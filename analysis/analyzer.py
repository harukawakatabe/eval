"""
文档标注分析器

分析 docs_annotation 输出的标注结果，为 query 抽取提供数据支撑。
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
from collections import defaultdict, Counter
from datetime import datetime


class AnnotationAnalyzer:
    """标注结果分析器"""
    
    # 所有文档类型通用的标签
    COMMON_TAGS = [
        "layout",
        "has_image",
        "has_table", 
        "has_formula",
        "has_chart",
        "image_text_mixed",
    ]
    
    # PDF 专属标签
    PDF_ONLY_TAGS = [
        "reading_order_sensitive",
        "table_profile.long_table",
        "table_profile.cross_page_table",
        "table_profile.table_dominant",
        "chart_profile.cross_page_chart",
    ]
    
    # 压力点标签（用于 query 抽取）
    STRESSOR_TAGS = [
        "has_image",
        "has_table",
        "has_formula", 
        "has_chart",
        "image_text_mixed",
        "reading_order_sensitive",
        "table_profile.long_table",
        "table_profile.cross_page_table",
        "table_profile.table_dominant",
        "chart_profile.cross_page_chart",
    ]
    
    def __init__(
        self,
        input_dir: str,
        sparse_threshold: int = 3,
        complexity_threshold: int = 3,
    ):
        """
        初始化分析器
        
        Args:
            input_dir: 标注输出目录路径
            sparse_threshold: 稀疏桶阈值（文件数 < N 视为稀疏）
            complexity_threshold: 高复杂度阈值（压力点 >= N 视为高复杂度）
        """
        self.input_dir = Path(input_dir)
        self.sparse_threshold = sparse_threshold
        self.complexity_threshold = complexity_threshold
        
        # 加载所有标注数据
        self.annotations: List[Dict[str, Any]] = []
        self.by_folder: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._load_annotations()
    
    def _load_annotations(self):
        """加载所有 JSON 标注文件"""
        if not self.input_dir.exists():
            raise FileNotFoundError(f"输入目录不存在: {self.input_dir}")
        
        for json_file in self.input_dir.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 添加来源信息
                    data["_source_file"] = str(json_file)
                    data["_folder"] = json_file.parent.name if json_file.parent != self.input_dir else "_root"
                    self.annotations.append(data)
                    self.by_folder[data["_folder"]].append(data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"警告: 无法加载 {json_file}: {e}")
    
    def _get_nested_value(self, data: Dict, key: str) -> Any:
        """获取嵌套字典中的值，支持点号分隔的路径"""
        keys = key.split(".")
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value
    
    def _get_doc_profile(self, annotation: Dict) -> Dict:
        """获取 doc_profile（兼容旧版 pdf_profile）"""
        return annotation.get("doc_profile") or annotation.get("pdf_profile") or {}
    
    def _get_stressors(self, annotation: Dict) -> List[str]:
        """提取文档的压力点列表"""
        profile = self._get_doc_profile(annotation)
        stressors = []
        
        for tag in self.STRESSOR_TAGS:
            value = self._get_nested_value(profile, tag)
            if value is True:
                stressors.append(tag)
        
        # 特殊处理 layout
        layout = profile.get("layout")
        if layout in ("double", "mixed"):
            stressors.append(f"layout={layout}")
        
        return stressors
    
    # ==================== 分析方法 ====================
    
    def analyze_basic_stats(self, annotations: List[Dict] = None) -> Dict:
        """基础统计分析"""
        data = annotations or self.annotations
        
        if not data:
            return {"total_files": 0, "file_types": {}, "folders": {}}
        
        # 文件类型分布
        file_types = Counter(a.get("file_type", "unknown") for a in data)
        
        # 文件夹分布
        folders = Counter(a.get("_folder", "_unknown") for a in data)
        
        return {
            "total_files": len(data),
            "file_types": dict(file_types.most_common()),
            "file_type_rates": {
                k: f"{v / len(data) * 100:.1f}%"
                for k, v in file_types.items()
            },
            "folders": dict(folders.most_common()),
        }
    
    def analyze_tag_distribution(self, annotations: List[Dict] = None) -> Dict:
        """标签分布分析"""
        data = annotations or self.annotations
        
        if not data:
            return {}
        
        result = {}
        all_tags = self.COMMON_TAGS + self.PDF_ONLY_TAGS
        
        for tag in all_tags:
            true_count = 0
            false_count = 0
            na_count = 0
            
            for ann in data:
                profile = self._get_doc_profile(ann)
                value = self._get_nested_value(profile, tag)
                
                if value is True:
                    true_count += 1
                elif value is False:
                    false_count += 1
                else:
                    na_count += 1
            
            total_valid = true_count + false_count
            result[tag] = {
                "true": true_count,
                "false": false_count,
                "na": na_count,
                "true_rate": f"{true_count / total_valid * 100:.1f}%" if total_valid > 0 else "N/A",
            }
        
        # 特殊处理 layout 枚举
        layout_dist = Counter()
        for ann in data:
            profile = self._get_doc_profile(ann)
            layout = profile.get("layout", "unknown")
            layout_dist[layout] += 1
        
        result["layout_distribution"] = dict(layout_dist.most_common())
        
        return result
    
    def analyze_stressor_combinations(self, annotations: List[Dict] = None) -> Dict:
        """压力点组合分析"""
        data = annotations or self.annotations
        
        if not data:
            return {}
        
        # 每个文档的压力点
        doc_stressors: List[Tuple[str, List[str]]] = []
        for ann in data:
            stressors = self._get_stressors(ann)
            doc_stressors.append((ann.get("doc_id", "unknown"), stressors))
        
        # 压力点计数分布
        count_dist = Counter(len(s) for _, s in doc_stressors)
        
        # 组合统计
        combo_counter = Counter()
        for _, stressors in doc_stressors:
            if stressors:
                combo_key = tuple(sorted(stressors))
                combo_counter[combo_key] += 1
        
        # 常见组合 TOP 20
        top_combos = [
            {"stressors": list(combo), "count": count}
            for combo, count in combo_counter.most_common(20)
        ]
        
        # 稀有组合（仅出现 1-2 次）
        rare_combos = [
            {"stressors": list(combo), "count": count}
            for combo, count in combo_counter.items()
            if count <= 2
        ]
        
        # 高复杂度文档（压力点 >= threshold）
        high_complexity_docs = [
            {
                "doc_id": doc_id,
                "file_type": next((a.get("file_type") for a in data if a.get("doc_id") == doc_id), "unknown"),
                "stressors": stressors,
                "stressor_count": len(stressors),
            }
            for doc_id, stressors in doc_stressors
            if len(stressors) >= self.complexity_threshold
        ]
        high_complexity_docs.sort(key=lambda x: x["stressor_count"], reverse=True)
        
        return {
            "stressor_count_distribution": {
                str(k): v for k, v in sorted(count_dist.items())
            },
            "total_unique_combinations": len(combo_counter),
            "top_combinations": top_combos,
            "rare_combinations": rare_combos[:20],  # 最多显示 20 个
            "high_complexity_docs": high_complexity_docs,
            "high_complexity_count": len(high_complexity_docs),
        }
    
    def analyze_buckets(self, annotations: List[Dict] = None) -> Dict:
        """分桶分析（对齐 balance_keys）"""
        data = annotations or self.annotations
        
        if not data:
            return {}
        
        # 一级桶：file_type
        level1_buckets: Dict[str, List[Dict]] = defaultdict(list)
        for ann in data:
            file_type = ann.get("file_type", "unknown")
            level1_buckets[file_type].append(ann)
        
        result = {
            "level1_buckets": {},
            "level2_buckets": {},  # 仅 PDF
        }
        
        for file_type, docs in level1_buckets.items():
            result["level1_buckets"][file_type] = {
                "count": len(docs),
                "doc_ids": [d.get("doc_id") for d in docs],
            }
            
            # PDF 二级分桶
            if file_type == "pdf":
                # 按关键特征组合分桶
                sub_buckets: Dict[str, List[str]] = defaultdict(list)
                
                for doc in docs:
                    profile = self._get_doc_profile(doc)
                    
                    # 构建桶键
                    bucket_parts = []
                    
                    # layout
                    layout = profile.get("layout", "single")
                    bucket_parts.append(f"layout={layout}")
                    
                    # 关键 stressor
                    for tag in ["has_table", "has_chart", "has_image"]:
                        if profile.get(tag):
                            bucket_parts.append(tag)
                    
                    # table_profile
                    table_profile = profile.get("table_profile", {})
                    if table_profile.get("cross_page_table"):
                        bucket_parts.append("cross_page_table")
                    if table_profile.get("long_table"):
                        bucket_parts.append("long_table")
                    
                    bucket_key = " | ".join(sorted(bucket_parts)) if bucket_parts else "basic"
                    sub_buckets[bucket_key].append(doc.get("doc_id"))
                
                result["level2_buckets"]["pdf"] = {
                    bucket_key: {
                        "count": len(doc_ids),
                        "doc_ids": doc_ids,
                    }
                    for bucket_key, doc_ids in sorted(sub_buckets.items(), key=lambda x: -len(x[1]))
                }
        
        return result
    
    def analyze_gaps(self, annotations: List[Dict] = None) -> Dict:
        """覆盖缺口分析"""
        data = annotations or self.annotations
        
        if not data:
            return {}
        
        tag_dist = self.analyze_tag_distribution(data)
        bucket_analysis = self.analyze_buckets(data)
        
        gaps = {
            "empty_buckets": [],
            "sparse_buckets": [],
            "missing_features": [],
            "file_type_gaps": [],
        }
        
        # 检查完全缺失的特征
        for tag, dist in tag_dist.items():
            if isinstance(dist, dict) and "true" in dist:
                if dist["true"] == 0:
                    gaps["missing_features"].append({
                        "tag": tag,
                        "message": f"标签 '{tag}' 在所有文档中都为 false",
                    })
        
        # 检查文件类型缺口
        expected_types = {"pdf", "doc", "ppt", "xlsx"}
        actual_types = set(bucket_analysis.get("level1_buckets", {}).keys())
        missing_types = expected_types - actual_types
        
        for t in missing_types:
            gaps["file_type_gaps"].append({
                "file_type": t,
                "message": f"缺少 {t} 类型的文档",
            })
        
        # 检查稀疏桶
        for file_type, info in bucket_analysis.get("level1_buckets", {}).items():
            if info["count"] < self.sparse_threshold:
                gaps["sparse_buckets"].append({
                    "bucket": f"file_type={file_type}",
                    "count": info["count"],
                    "threshold": self.sparse_threshold,
                })
        
        # 检查 PDF 二级桶
        pdf_buckets = bucket_analysis.get("level2_buckets", {}).get("pdf", {})
        for bucket_key, info in pdf_buckets.items():
            if info["count"] < self.sparse_threshold:
                gaps["sparse_buckets"].append({
                    "bucket": f"pdf/{bucket_key}",
                    "count": info["count"],
                    "threshold": self.sparse_threshold,
                })
        
        return gaps
    
    def generate_sampling_advice(self, annotations: List[Dict] = None) -> Dict:
        """生成采样建议"""
        data = annotations or self.annotations
        
        if not data:
            return {}
        
        basic_stats = self.analyze_basic_stats(data)
        bucket_analysis = self.analyze_buckets(data)
        gaps = self.analyze_gaps(data)
        stressor_analysis = self.analyze_stressor_combinations(data)
        
        # 计算各文件类型的最小数量
        file_type_counts = basic_stats.get("file_types", {})
        min_count = min(file_type_counts.values()) if file_type_counts else 0
        
        # 需要带放回采样的类型
        needs_replacement = [
            ft for ft, count in file_type_counts.items()
            if count < 5  # 假设每个文档生成 2 个 query，至少需要 5 个文档
        ]
        
        advice = {
            "recommended_per_file_type": min(min_count * 2, 50) if min_count > 0 else 10,
            "recommended_queries_per_doc": 2,
            "needs_replacement_sampling": needs_replacement,
            "sparse_buckets_warning": [b["bucket"] for b in gaps.get("sparse_buckets", [])],
            "priority_docs": [
                d["doc_id"] for d in stressor_analysis.get("high_complexity_docs", [])[:20]
            ],
            "priority_docs_count": stressor_analysis.get("high_complexity_count", 0),
            "suggested_config": {
                "per_file_type": min(min_count * 2, 50) if min_count > 0 else 10,
                "queries_per_doc": 2,
                "allow_sample_with_replacement": len(needs_replacement) > 0,
                "balance_keys": {
                    "level1": "file_type",
                    "pdf_stressors": self.STRESSOR_TAGS,
                },
            },
        }
        
        return advice
    
    # ==================== 输出方法 ====================
    
    def run_full_analysis(self) -> Dict:
        """运行完整分析"""
        return {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "input_dir": str(self.input_dir),
                "sparse_threshold": self.sparse_threshold,
                "complexity_threshold": self.complexity_threshold,
            },
            "basic_stats": self.analyze_basic_stats(),
            "tag_distribution": self.analyze_tag_distribution(),
            "stressor_combinations": self.analyze_stressor_combinations(),
            "buckets": self.analyze_buckets(),
            "gaps": self.analyze_gaps(),
            "sampling_advice": self.generate_sampling_advice(),
        }
    
    def run_folder_analysis(self) -> Dict:
        """按文件夹运行分析"""
        result = {}
        for folder, annotations in self.by_folder.items():
            result[folder] = {
                "basic_stats": self.analyze_basic_stats(annotations),
                "tag_distribution": self.analyze_tag_distribution(annotations),
                "stressor_combinations": self.analyze_stressor_combinations(annotations),
            }
        return result
    
    def export_to_json(self, output_dir: str):
        """导出所有 JSON 报告"""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        full_analysis = self.run_full_analysis()
        
        # summary.json
        with open(out_path / "summary.json", "w", encoding="utf-8") as f:
            json.dump(full_analysis, f, ensure_ascii=False, indent=2)
        
        # by_folder.json
        folder_analysis = self.run_folder_analysis()
        with open(out_path / "by_folder.json", "w", encoding="utf-8") as f:
            json.dump(folder_analysis, f, ensure_ascii=False, indent=2)
        
        # buckets.json
        with open(out_path / "buckets.json", "w", encoding="utf-8") as f:
            json.dump(full_analysis["buckets"], f, ensure_ascii=False, indent=2)
        
        # stressor_combos.json
        with open(out_path / "stressor_combos.json", "w", encoding="utf-8") as f:
            json.dump(full_analysis["stressor_combinations"], f, ensure_ascii=False, indent=2)
        
        # gaps.json
        with open(out_path / "gaps.json", "w", encoding="utf-8") as f:
            json.dump(full_analysis["gaps"], f, ensure_ascii=False, indent=2)
        
        # sampling_advice.json
        with open(out_path / "sampling_advice.json", "w", encoding="utf-8") as f:
            json.dump(full_analysis["sampling_advice"], f, ensure_ascii=False, indent=2)
        
        return full_analysis
    
    def export_to_csv(self, output_dir: str):
        """导出 CSV 报告"""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        full_analysis = self.run_full_analysis()
        
        # tag_distribution.csv
        tag_dist = full_analysis["tag_distribution"]
        with open(out_path / "tag_distribution.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["标签", "true", "false", "N/A", "true占比"])
            for tag, dist in tag_dist.items():
                if isinstance(dist, dict) and "true" in dist:
                    writer.writerow([
                        tag,
                        dist.get("true", 0),
                        dist.get("false", 0),
                        dist.get("na", 0),
                        dist.get("true_rate", "N/A"),
                    ])
        
        # bucket_distribution.csv
        buckets = full_analysis["buckets"]
        with open(out_path / "bucket_distribution.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["桶类型", "桶名称", "文件数"])
            
            # 一级桶
            for ft, info in buckets.get("level1_buckets", {}).items():
                writer.writerow(["file_type", ft, info["count"]])
            
            # 二级桶（PDF）
            for bucket_key, info in buckets.get("level2_buckets", {}).get("pdf", {}).items():
                writer.writerow(["pdf_sub", bucket_key, info["count"]])
        
        # high_complexity_docs.csv
        stressor_combos = full_analysis["stressor_combinations"]
        high_docs = stressor_combos.get("high_complexity_docs", [])
        with open(out_path / "high_complexity_docs.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["doc_id", "file_type", "压力点数", "压力点列表"])
            for doc in high_docs:
                writer.writerow([
                    doc["doc_id"],
                    doc["file_type"],
                    doc["stressor_count"],
                    ", ".join(doc["stressors"]),
                ])
    
    def export_to_markdown(self, output_dir: str) -> str:
        """导出 Markdown 报告"""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        full_analysis = self.run_full_analysis()
        basic = full_analysis["basic_stats"]
        tag_dist = full_analysis["tag_distribution"]
        stressor_combos = full_analysis["stressor_combinations"]
        gaps = full_analysis["gaps"]
        advice = full_analysis["sampling_advice"]
        
        lines = [
            "# 文档标注分析报告",
            "",
            f"**生成时间**: {full_analysis['metadata']['generated_at']}",
            f"**输入目录**: `{full_analysis['metadata']['input_dir']}`",
            f"**文件总数**: {basic['total_files']}",
            "",
            "---",
            "",
            "## 1. 基础统计",
            "",
            "### 1.1 文件类型分布",
            "",
            "| 文件类型 | 数量 | 占比 |",
            "|---------|------|------|",
        ]
        
        for ft, count in basic.get("file_types", {}).items():
            rate = basic.get("file_type_rates", {}).get(ft, "N/A")
            lines.append(f"| {ft} | {count} | {rate} |")
        
        lines.extend([
            "",
            "### 1.2 文件夹分布",
            "",
            "| 文件夹 | 数量 |",
            "|--------|------|",
        ])
        
        for folder, count in basic.get("folders", {}).items():
            lines.append(f"| {folder} | {count} |")
        
        lines.extend([
            "",
            "---",
            "",
            "## 2. 标签分布",
            "",
            "| 标签 | true | false | N/A | true占比 |",
            "|------|------|-------|-----|----------|",
        ])
        
        for tag, dist in tag_dist.items():
            if isinstance(dist, dict) and "true" in dist:
                lines.append(f"| {tag} | {dist.get('true', 0)} | {dist.get('false', 0)} | {dist.get('na', 0)} | {dist.get('true_rate', 'N/A')} |")
        
        # Layout 分布
        layout_dist = tag_dist.get("layout_distribution", {})
        if layout_dist:
            lines.extend([
                "",
                "### Layout 分布",
                "",
                "| Layout | 数量 |",
                "|--------|------|",
            ])
            for layout, count in layout_dist.items():
                lines.append(f"| {layout} | {count} |")
        
        lines.extend([
            "",
            "---",
            "",
            "## 3. 压力点组合分析",
            "",
            "### 3.1 压力点计数分布",
            "",
            "| 压力点数 | 文档数 |",
            "|---------|--------|",
        ])
        
        for count, num in stressor_combos.get("stressor_count_distribution", {}).items():
            lines.append(f"| {count} | {num} |")
        
        lines.extend([
            "",
            f"**唯一组合数**: {stressor_combos.get('total_unique_combinations', 0)}",
            "",
            "### 3.2 常见组合 TOP 10",
            "",
        ])
        
        top_combos = stressor_combos.get("top_combinations", [])[:10]
        for i, combo in enumerate(top_combos, 1):
            stressors_str = ", ".join(combo["stressors"]) if combo["stressors"] else "(无压力点)"
            lines.append(f"{i}. `[{stressors_str}]` - {combo['count']} 个文档")
        
        # 高复杂度文档
        high_docs = stressor_combos.get("high_complexity_docs", [])
        if high_docs:
            lines.extend([
                "",
                f"### 3.3 高复杂度文档（压力点 ≥ {self.complexity_threshold}）",
                "",
                f"共 {len(high_docs)} 个文档",
                "",
                "| doc_id | file_type | 压力点 |",
                "|--------|-----------|--------|",
            ])
            for doc in high_docs[:15]:  # 最多显示 15 个
                stressors_str = ", ".join(doc["stressors"])
                lines.append(f"| {doc['doc_id'][:30]}... | {doc['file_type']} | {stressors_str} |")
            
            if len(high_docs) > 15:
                lines.append(f"| ... | ... | （还有 {len(high_docs) - 15} 个） |")
        
        lines.extend([
            "",
            "---",
            "",
            "## 4. 覆盖缺口分析",
            "",
        ])
        
        # 缺失特征
        missing = gaps.get("missing_features", [])
        if missing:
            lines.append("### 4.1 缺失特征")
            lines.append("")
            for m in missing:
                lines.append(f"- **{m['tag']}**: {m['message']}")
            lines.append("")
        
        # 文件类型缺口
        ft_gaps = gaps.get("file_type_gaps", [])
        if ft_gaps:
            lines.append("### 4.2 文件类型缺口")
            lines.append("")
            for g in ft_gaps:
                lines.append(f"- {g['message']}")
            lines.append("")
        
        # 稀疏桶
        sparse = gaps.get("sparse_buckets", [])
        if sparse:
            lines.append("### 4.3 稀疏桶（样本不足）")
            lines.append("")
            lines.append("| 桶 | 文件数 | 阈值 |")
            lines.append("|----|--------|------|")
            for s in sparse:
                lines.append(f"| {s['bucket']} | {s['count']} | < {s['threshold']} |")
            lines.append("")
        
        if not missing and not ft_gaps and not sparse:
            lines.append("**无明显覆盖缺口**")
            lines.append("")
        
        lines.extend([
            "---",
            "",
            "## 5. 采样建议",
            "",
            f"- **建议 per_file_type**: {advice.get('recommended_per_file_type', 'N/A')}",
            f"- **建议 queries_per_doc**: {advice.get('recommended_queries_per_doc', 2)}",
            f"- **需要带放回采样的类型**: {', '.join(advice.get('needs_replacement_sampling', [])) or '无'}",
            f"- **优先采样文档数**: {advice.get('priority_docs_count', 0)}",
            "",
            "### 建议配置",
            "",
            "```json",
            json.dumps(advice.get("suggested_config", {}), ensure_ascii=False, indent=2),
            "```",
            "",
            "---",
            "",
            "*报告由 analysis 模块自动生成*",
        ])
        
        report_content = "\n".join(lines)
        
        with open(out_path / "REPORT.md", "w", encoding="utf-8") as f:
            f.write(report_content)
        
        return report_content
    
    def export_all(self, output_dir: str):
        """导出所有格式的报告"""
        print(f"正在分析 {len(self.annotations)} 个标注文件...")
        
        self.export_to_json(output_dir)
        print("  [OK] JSON 报告已生成")
        
        self.export_to_csv(output_dir)
        print("  [OK] CSV 报告已生成")
        
        self.export_to_markdown(output_dir)
        print("  [OK] Markdown 报告已生成")
        
        print(f"\n所有报告已输出到: {output_dir}")
