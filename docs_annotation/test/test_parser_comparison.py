#!/usr/bin/env python
"""解析器对比测试脚本。

对比 Legacy (pdfplumber/python-docx) 和 Docling 解析器的结果。

使用方法：
    python -m test.test_parser_comparison <file_path>
    python -m test.test_parser_comparison <directory> --batch
    
示例：
    python -m test.test_parser_comparison document.pdf
    python -m test.test_parser_comparison "reference/data/Files/业务交付管理" --batch
"""

import sys
import os
import logging
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List

# 添加正确的路径
script_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(script_dir))

from service import AnnotationService
from processors.doc_parser import ParserBackend
from models.ocr import MockOCR
from models.llm import MockLLM


# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'}


def annotate_with_parser(file_path: str, parser_backend: ParserBackend) -> Dict[str, Any]:
    """使用指定解析器标注文件。"""
    service = AnnotationService(
        ocr_model=MockOCR(),
        llm_model=MockLLM(),
        parser_backend=parser_backend,
        log_level=logging.WARNING
    )
    
    try:
        ann = service.annotate(file_path)
        result = ann.to_dict()
        result["_success"] = True
        return result
    except Exception as e:
        return {
            "_success": False,
            "_error": str(e)
        }


def compare_file(file_path: str) -> Dict[str, Any]:
    """对比单个文件的解析结果。"""
    results = {
        "file": file_path,
        "parsers": {}
    }
    
    # Legacy 解析器（始终可用）
    print(f"  [Legacy] 解析中...")
    results["parsers"]["legacy"] = annotate_with_parser(file_path, ParserBackend.LEGACY)
    
    # Docling 解析器（可能未安装）
    try:
        from src.processors.docling_parser import DoclingParser
        parser = DoclingParser()
        if parser.is_available():
            print(f"  [Docling] 解析中...")
            results["parsers"]["docling"] = annotate_with_parser(file_path, ParserBackend.DOCLING)
        else:
            results["parsers"]["docling"] = {"_success": False, "_error": "Docling 未安装"}
    except ImportError:
        results["parsers"]["docling"] = {"_success": False, "_error": "Docling 模块未找到"}
    
    return results


def print_comparison(result: Dict[str, Any]):
    """打印对比结果。"""
    print(f"\n{'='*70}")
    print(f"文件: {result['file']}")
    print(f"{'='*70}")
    
    parsers = result.get("parsers", {})
    
    # 提取关键字段进行对比
    fields = [
        ("has_table", lambda r: r.get("doc_profile", {}).get("has_table")),
        ("has_image", lambda r: r.get("doc_profile", {}).get("has_image")),
        ("has_chart", lambda r: r.get("doc_profile", {}).get("has_chart")),
        ("has_formula", lambda r: r.get("doc_profile", {}).get("has_formula")),
        ("table_dominant", lambda r: r.get("doc_profile", {}).get("table_profile", {}).get("table_dominant") if r.get("doc_profile", {}).get("table_profile") else None),
        ("cross_page_table", lambda r: r.get("doc_profile", {}).get("table_profile", {}).get("cross_page_table") if r.get("doc_profile", {}).get("table_profile") else None),
        ("long_table", lambda r: r.get("doc_profile", {}).get("table_profile", {}).get("long_table") if r.get("doc_profile", {}).get("table_profile") else None),
        ("layout", lambda r: r.get("doc_profile", {}).get("layout")),
    ]
    
    # 打印表格头
    parser_names = list(parsers.keys())
    header = f"{'字段':<20}" + "".join(f"{p:<15}" for p in parser_names)
    print(header)
    print("-" * len(header))
    
    # 打印每个字段的对比
    for field_name, extractor in fields:
        row = f"{field_name:<20}"
        values = []
        for p in parser_names:
            r = parsers[p]
            if not r.get("_success"):
                values.append("ERROR")
            else:
                v = extractor(r)
                values.append(str(v) if v is not None else "-")
        row += "".join(f"{v:<15}" for v in values)
        
        # 如果值不一致，标记差异
        unique_values = set(v for v in values if v not in ["ERROR", "-"])
        if len(unique_values) > 1:
            row += " ⚠️ 差异"
        
        print(row)
    
    # 打印错误信息
    for p, r in parsers.items():
        if not r.get("_success"):
            print(f"\n❌ {p} 错误: {r.get('_error')}")


def batch_compare(directory: str) -> List[Dict[str, Any]]:
    """批量对比目录下的文件。"""
    results = []
    dir_path = Path(directory)
    
    if not dir_path.is_dir():
        print(f"❌ 目录不存在: {directory}")
        return results
    
    files = [f for f in dir_path.rglob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    print(f"找到 {len(files)} 个支持的文件")
    
    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {file_path.name}")
        result = compare_file(str(file_path))
        results.append(result)
        print_comparison(result)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="解析器对比测试")
    parser.add_argument(
        "path",
        help="文件路径或目录路径"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理目录下的所有文件"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="输出 JSON 结果到文件"
    )
    
    args = parser.parse_args()
    
    if args.batch or os.path.isdir(args.path):
        results = batch_compare(args.path)
    else:
        result = compare_file(args.path)
        print_comparison(result)
        results = [result]
    
    # 保存结果
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 结果已保存到: {args.output}")
    
    # 统计差异
    if len(results) > 1:
        print(f"\n{'='*70}")
        print("统计摘要")
        print(f"{'='*70}")
        print(f"总文件数: {len(results)}")
        
        # 统计成功/失败
        legacy_success = sum(1 for r in results if r.get("parsers", {}).get("legacy", {}).get("_success"))
        docling_success = sum(1 for r in results if r.get("parsers", {}).get("docling", {}).get("_success"))
        print(f"Legacy 成功: {legacy_success}/{len(results)}")
        print(f"Docling 成功: {docling_success}/{len(results)}")


if __name__ == "__main__":
    main()
