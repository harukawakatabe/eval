"""特征提取器 - 提取文档的高级特征。"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.base import BaseProcessor, ProcessResult
from models.llm import LLMModel
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
        """
        super().__init__(config)
        self.llm_model: Optional[LLMModel] = config.get("llm_model") if config else None
        self.long_table_threshold = self.config.get("long_table_threshold", 3)
        self.check_cross_page = self.config.get("check_cross_page", True)

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
        - 长表格：统计表格跨越的页数
        - 表格主导：估算表格内容占比
        """
        if not elements.tables:
            return features

        # 1. 检测跨页表格
        if self.check_cross_page:
            table_pages = {tbl.page for tbl in elements.tables}
            features.cross_page_table = len(table_pages) > 1

            # 2. 判断是否为长表格
            features.long_table = len(table_pages) >= self.long_table_threshold

        # 3. 估算表格主导性（简单启发式）
        # 如果表格数量 > 5 或占页面比例高，认为是表格主导
        total_tables = len(elements.tables)
        total_pages = doc_content.page_count

        if total_tables > 5 or (total_pages > 0 and total_tables / total_pages > 0.5):
            features.table_dominant = True

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

            # 更新特征
            if result.get("table_dominant") is not None:
                features.table_dominant = result["table_dominant"]
            if result.get("reading_order_sensitive") is not None:
                features.reading_order_sensitive = result["reading_order_sensitive"]

        except Exception as e:
            # LLM调用失败，保持原有特征
            pass

        return features
