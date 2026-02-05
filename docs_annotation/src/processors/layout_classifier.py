"""布局分类器 - 判断文档布局类型，生成最终标注。"""

from typing import Any, Dict, Optional

from core.base import BaseProcessor, ProcessResult
from core.schema import LayoutType, FileType
from models.llm import LLMModel
from .doc_parser import DocContent
from .element_detector import ElementList
from .feature_extractor import FeatureSet


class LayoutClassifier(BaseProcessor):
    """
    布局分类器 - 判断文档的布局类型。

    布局类型：
    - single: 单页布局，每页内容独立
    - double: 双页布局，内容跨页连续（如展开表格）
    - mixed: 混合布局，既有单页也有双页内容
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化布局分类器。

        Args:
            config: 配置字典，可包含：
                - llm_model: LLM模型实例
                - use_llm: 是否使用LLM（默认True）
                - fallback_rule: LLM失败时的默认值（默认"single"）
        """
        super().__init__(config)
        self.llm_model: Optional[LLMModel] = config.get("llm_model") if config else None
        self.use_llm = self.config.get("use_llm", True)
        self.fallback_rule = LayoutType(self.config.get("fallback_rule", "single"))

    def process(self, input_data: tuple) -> ProcessResult:
        """
        分类文档布局，生成最终标注。

        Args:
            input_data: (DocContent, ElementList, FeatureSet) 元组

        Returns:
            ProcessResult，包含最终的DocumentAnnotation
        """
        doc_content, elements, features = input_data

        is_pdf = doc_content.file_type == FileType.PDF

        # 1. 布局分类
        if is_pdf:
            # PDF：尝试使用 LLM 分类
            if self.use_llm and self.llm_model is not None:
                layout = self._classify_with_llm(doc_content, elements, features)
            else:
                layout = self._classify_by_rules(doc_content, elements, features)
        else:
            # 非 PDF：默认 single
            layout = LayoutType.SINGLE

        # 2. 构建最终结果
        from core.schema import DocumentAnnotation, DocProfile, TableProfile, ChartProfile

        # 判断是否图文混排
        has_image = len(elements.images) > 0
        has_substantial_text = len(doc_content.text.strip()) > 100  # 文字超过100字符
        image_text_mixed = has_image and has_substantial_text

        # 构建 DocProfile（适用于所有文档类型）
        doc_profile = DocProfile(
            layout=layout,
            has_image=has_image,
            has_table=len(elements.tables) > 0,
            has_formula=len(elements.formulas) > 0,
            has_chart=len(elements.charts) > 0,
            image_text_mixed=image_text_mixed,
        )

        # 仅 PDF：添加可选字段
        if is_pdf:
            doc_profile.reading_order_sensitive = features.reading_order_sensitive

            # 添加表格特征（仅 PDF）
            if elements.tables:
                doc_profile.table_profile = TableProfile(
                    long_table=features.long_table,
                    cross_page_table=features.cross_page_table,
                    table_dominant=features.table_dominant,
                )

            # 添加图表特征（仅 PDF）
            if elements.charts:
                doc_profile.chart_profile = ChartProfile(
                    cross_page_chart=features.cross_page_chart,
                )

        # 构建完整标注
        annotation = DocumentAnnotation(
            doc_id=doc_content.doc_id,
            file_type=doc_content.file_type,
            file_path=doc_content.file_path,
            doc_profile=doc_profile,
        )

        return ProcessResult(
            success=True,
            data=annotation,
            metadata={"layout_type": layout.value, "is_pdf": is_pdf}
        )

    def _classify_with_llm(
        self,
        doc_content: DocContent,
        elements: ElementList,
        features: FeatureSet
    ) -> LayoutType:
        """
        使用LLM进行布局分类。

        Args:
            doc_content: 文档内容
            elements: 检测到的元素
            features: 提取的特征

        Returns:
            布局类型
        """
        text_preview = doc_content.text[:500] if doc_content.text else ""

        prompt = f"""分析以下文档的布局类型。

文档信息：
- 页数: {doc_content.page_count}
- 图片数量: {len(elements.images)}
- 表格数量: {len(elements.tables)}
- 跨页表格: {features.cross_page_table}
- 长表格: {features.long_table}
- 文本预览: {text_preview}

布局类型说明：
- single: 单页布局，每页内容独立，如论文、报告
- double: 双页布局，内容跨页连续展开，如折页图、长表格
- mixed: 混合布局，既有单页内容也有跨页内容

请判断文档属于哪种布局类型。
"""

        try:
            result = self.llm_model.classify(
                prompt,
                options=["single", "double", "mixed"]
            )
            return LayoutType(result.get("label", "single"))

        except Exception as e:
            # LLM调用失败，使用规则分类
            return self._classify_by_rules(doc_content, elements, features)

    def _classify_by_rules(
        self,
        doc_content: DocContent,
        elements: ElementList,
        features: FeatureSet
    ) -> LayoutType:
        """
        使用规则进行布局分类。

        规则：
        1. 如果有长表格或跨页表格 → double
        2. 如果有跨页图表 → double
        3. 否则 → single
        4. 如果既有单页特征又有双页特征 → mixed
        """
        has_double_page_features = (
            features.long_table or
            features.cross_page_table or
            features.cross_page_chart
        )

        has_single_page_features = (
            len(elements.images) > 0 or
            len(doc_content.text) > 0
        )

        if has_double_page_features and has_single_page_features:
            return LayoutType.MIXED
        elif has_double_page_features:
            return LayoutType.DOUBLE
        else:
            return LayoutType.SINGLE
