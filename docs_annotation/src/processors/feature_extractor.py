"""特征提取器 - 提取文档的高级特征。"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..core.base import BaseProcessor, ProcessResult
from ..core.logger import get_logger
from ..models.llm import LLMModel
from .doc_parser import DocContent
from .element_detector import ElementList


@dataclass
class FeatureSet:
    """
    文档特征集合。

    Attributes:
        table_dominant: 表格是否占主导地位（可选）
        long_table: 是否有长表格（跨3页以上）
        cross_page_table: 表格是否跨页
        cross_page_chart: 图表是否跨页
        reading_order_sensitive: 阅读顺序是否敏感（可选）
    """
    table_dominant: Optional[bool] = None
    long_table: bool = False
    cross_page_table: bool = False
    cross_page_chart: bool = False
    reading_order_sensitive: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {k: v for k, v in [
            ("table_dominant", self.table_dominant),
            ("long_table", self.long_table),
            ("cross_page_table", self.cross_page_table),
            ("cross_page_chart", self.cross_page_chart),
            ("reading_order_sensitive", self.reading_order_sensitive),
        ] if v is not None}


class FeatureExtractor(BaseProcessor):
    """
    特征提取器 - 分析文档的结构特征。

    提取特征：
    - 表格特征：是否占主导、是否跨页、是否长表格
    - 图表特征：是否跨页
    - 阅读顺序：是否对顺序敏感
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化特征提取器。

        Args:
            config: 配置字典，可包含：
                - llm_model: LLM模型实例
                - long_table_threshold: 长表格页数阈值（默认3）
                - check_cross_page: 是否检查跨页
                - table_dominant_ratio: 表格页占比阈值（默认0.6）
        """
        super().__init__(config)
        self.llm_model: Optional[LLMModel] = config.get("llm_model") if config else None
        self.long_table_threshold = self.config.get("long_table_threshold", 3)
        self.check_cross_page = self.config.get("check_cross_page", True)
        self.table_dominant_ratio = self.config.get("table_dominant_ratio", 0.6)
        self.logger = get_logger()

    def process(self, input_data: tuple) -> ProcessResult:
        """
        提取文档特征。

        Args:
            input_data: (DocContent, ElementList) 元组

        Returns:
            ProcessResult，包含 (DocContent, ElementList, FeatureSet)
        """
        doc_content, elements = input_data

        features = FeatureSet()

        # 1. 分析表格特征
        if elements.tables:
            features = self._extract_table_features(doc_content, elements, features)

        # 2. 分析图表特征
        if elements.charts:
            features = self._extract_chart_features(elements, features)

        # 3. 使用LLM进行高级分析（如果有）
        if self.llm_model:
            features = self._analyze_with_llm(doc_content, elements, features)

        return ProcessResult(
            success=True,
            data=(doc_content, elements, features),
            metadata=features.to_dict()
        )

    def _extract_table_features(
        self,
        doc_content: DocContent,
        elements: ElementList,
        features: FeatureSet
    ) -> FeatureSet:
        """
        提取表格特征。

        分析逻辑：
        - 跨页表格：检测表格是否跨越页面边界
          - 方法1：连续页面有表格
          - 方法2：单个表格行数很多（>50行，约一页内容）
        - 长表格：统计表格跨越的页数
        - 表格主导：基于表格覆盖的页数比例判断
        """
        if not elements.tables:
            return features

        # 收集表格所在的页码和行数
        table_pages = set()
        max_table_rows = 0
        total_table_rows = 0
        
        for tbl in elements.tables:
            if tbl.page is not None:
                table_pages.add(tbl.page)
            # 从 extra 字典获取行数（ElementInfo 存储方式）
            rows = 0
            if hasattr(tbl, 'extra') and isinstance(tbl.extra, dict):
                rows = tbl.extra.get('rows', 0) or 0
            elif hasattr(tbl, 'metadata') and isinstance(tbl.metadata, dict):
                rows = tbl.metadata.get('rows', 0) or 0
            elif hasattr(tbl, 'rows'):
                rows = getattr(tbl, 'rows', 0) or 0
            max_table_rows = max(max_table_rows, rows)
            total_table_rows += rows
        
        total_pages = doc_content.page_count
        table_page_count = len(table_pages)
        table_page_ratio = table_page_count / total_pages if total_pages > 0 else 0
        
        # 基于行数估算表格跨越的页数（每页约50行）
        rows_per_page = 50
        estimated_table_pages = max(1, total_table_rows // rows_per_page) if total_table_rows > 0 else 0
        max_single_table_pages = max(1, max_table_rows // rows_per_page) if max_table_rows > 0 else 0

        # 1. 检测跨页表格
        has_cross_page = False
        cross_page_reason = ""
        
        if self.check_cross_page:
            # 方法1：连续的页面都有表格
            if len(table_pages) > 1:
                sorted_pages = sorted(table_pages)
                for i in range(len(sorted_pages) - 1):
                    if sorted_pages[i + 1] - sorted_pages[i] == 1:
                        has_cross_page = True
                        cross_page_reason = f"连续页面有表格 (页 {sorted_pages})"
                        break
            
            # 方法2：单个表格行数很多（超过一页的内容量）
            if not has_cross_page and max_table_rows > rows_per_page:
                has_cross_page = True
                cross_page_reason = f"单表格行数 {max_table_rows} > {rows_per_page} (约跨 {max_single_table_pages} 页)"
        
        features.cross_page_table = has_cross_page
        if has_cross_page:
            self.logger.debug(f"跨页表格: {cross_page_reason}")

        # 2. 判断是否为长表格
        long_table = False
        long_table_reason = ""
        
        if self.check_cross_page:
            # 方法1：表格跨越 >= threshold 页（基于页码）
            if len(table_pages) > 1:
                sorted_pages = sorted(table_pages)
                max_consecutive = 1
                current_consecutive = 1
                for i in range(len(sorted_pages) - 1):
                    if sorted_pages[i + 1] - sorted_pages[i] == 1:
                        current_consecutive += 1
                        max_consecutive = max(max_consecutive, current_consecutive)
                    else:
                        current_consecutive = 1
                if max_consecutive >= self.long_table_threshold:
                    long_table = True
                    long_table_reason = f"连续 {max_consecutive} 页有表格"
            
            # 方法2：基于行数估算（单个表格跨越 >= threshold 页）
            if not long_table and max_single_table_pages >= self.long_table_threshold:
                long_table = True
                long_table_reason = f"单表格行数 {max_table_rows} 约跨 {max_single_table_pages} 页"
        
        features.long_table = long_table
        if long_table:
            self.logger.debug(f"长表格: {long_table_reason}")

        # 3. 改进的表格主导性判断
        # 条件1: 表格页数/总页数 >= 阈值（默认60%）
        # 条件2: 全部页面都有表格
        # 条件3: 表格数量 >= 页数（平均每页至少一个表格）
        # 条件4: 基于行数估算的表格覆盖页数/总页数 >= 阈值（适用于大表格）
        total_tables = len(elements.tables)
        
        # 计算基于行数的表格页覆盖率
        estimated_coverage_ratio = estimated_table_pages / total_pages if total_pages > 0 else 0
        
        is_dominant = False
        reason = ""
        
        if table_page_ratio >= self.table_dominant_ratio:
            is_dominant = True
            reason = f"表格页占比 {table_page_ratio:.1%} >= {self.table_dominant_ratio:.0%}"
        elif estimated_coverage_ratio >= self.table_dominant_ratio:
            # 基于行数估算的覆盖率（适用于 DOCX 等无法精确跟踪页码的格式）
            is_dominant = True
            reason = f"表格行数覆盖估算 {estimated_coverage_ratio:.1%} >= {self.table_dominant_ratio:.0%} (表格约跨{estimated_table_pages}页/总{total_pages}页)"
        elif table_page_count == total_pages and total_pages > 0:
            is_dominant = True
            reason = "所有页面都有表格"
        elif total_pages > 0 and total_tables >= total_pages:
            is_dominant = True
            reason = f"表格数量({total_tables}) >= 页数({total_pages})"
        
        features.table_dominant = is_dominant
        
        # 记录日志
        self.logger.feature_extracted(
            table_dominant=is_dominant,
            cross_page_table=features.cross_page_table,
            long_table=features.long_table,
            cross_page_chart=features.cross_page_chart,
            table_page_ratio=table_page_ratio
        )
        
        if is_dominant:
            self.logger.debug(f"表格主导判断依据: {reason}")

        return features

    def _extract_chart_features(
        self,
        elements: ElementList,
        features: FeatureSet
    ) -> FeatureSet:
        """
        提取图表特征。

        分析逻辑：
        - 跨页图表：检测图表是否跨越页面边界
        """
        if not elements.charts or not self.check_cross_page:
            return features

        # 检测图表是否跨页（单个图表跨多页）
        chart_pages = [cht.page for cht in elements.charts]
        if len(chart_pages) > 1:
            # 检查是否有相邻页面的图表
            sorted_pages = sorted(set(chart_pages))
            for i in range(len(sorted_pages) - 1):
                if sorted_pages[i + 1] - sorted_pages[i] == 1:
                    features.cross_page_chart = True
                    break

        return features

    def _analyze_with_llm(
        self,
        doc_content: DocContent,
        elements: ElementList,
        features: FeatureSet
    ) -> FeatureSet:
        """
        使用LLM进行高级特征分析。

        分析内容：
        - 表格主导性确认
        - 阅读顺序敏感性
        """
        # 构建分析提示
        text_preview = doc_content.text[:500] if doc_content.text else ""

        prompt = f"""分析以下文档的特征，回答以下问题：

文档信息：
- 页数: {doc_content.page_count}
- 图片数量: {len(elements.images)}
- 表格数量: {len(elements.tables)}
- 公式数量: {len(elements.formulas)}
- 图表数量: {len(elements.charts)}
- 文本预览: {text_preview}

请判断：
1. 表格是否是文档的主要内容（占比超过50%）？
2. 文档的阅读顺序是否敏感（如：需要按特定顺序阅读才能理解）？
"""

        # 构建schema
        schema = {
            "table_dominant": "boolean",
            "reading_order_sensitive": "boolean",
        }

        try:
            result = self.llm_model.extract(prompt, schema)

            # 更新特征（仅在规则计算没有得出结论时使用 LLM 结果）
            # 如果规则已经确定了 table_dominant，不要覆盖
            if features.table_dominant is None and result.get("table_dominant") is not None:
                features.table_dominant = result["table_dominant"]
            # reading_order_sensitive 通常需要 LLM 判断
            if result.get("reading_order_sensitive") is not None:
                features.reading_order_sensitive = result["reading_order_sensitive"]

        except Exception as e:
            # LLM调用失败，保持原有特征
            self.logger.debug(f"LLM 分析失败: {e}")

        return features
