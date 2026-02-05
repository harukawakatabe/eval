"""元素检测器 - 检测文档中的图片、表格、公式、图表。"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.base import BaseProcessor, ProcessResult
from models.ocr import OCRModel
from .doc_parser import DocContent


@dataclass
class ElementInfo:
    """
    单个元素信息。

    Attributes:
        bbox: 边界框 [x1, y1, x2, y2]
        page: 页码（从0开始）
        confidence: 置信度
        extra: 额外信息（如表格单元格、公式LaTeX等）
    """
    bbox: List[int]
    page: int
    confidence: float
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ElementList:
    """
    检测到的元素列表。

    Attributes:
        images: 图片元素列表
        tables: 表格元素列表
        formulas: 公式元素列表
        charts: 图表元素列表
    """
    images: List[ElementInfo] = field(default_factory=list)
    tables: List[ElementInfo] = field(default_factory=list)
    formulas: List[ElementInfo] = field(default_factory=list)
    charts: List[ElementInfo] = field(default_factory=list)

    def has_any(self) -> bool:
        """是否有任何元素。"""
        return bool(self.images or self.tables or self.formulas or self.charts)


class ElementDetector(BaseProcessor):
    """
    元素检测器 - 使用OCR模型检测文档元素。

    检测内容：
    - 图片：文档中的图片区域
    - 表格：文档中的表格结构
    - 公式：数学公式（LaTeX格式）
    - 图表：统计图表（柱状图、饼图等）
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化元素检测器。

        Args:
            config: 配置字典，可包含：
                - ocr_model: OCR模型实例
                - enabled_detectors: 启用的检测器列表
                - confidence_threshold: 置信度阈值
        """
        super().__init__(config)
        self.ocr_model: Optional[OCRModel] = config.get("ocr_model") if config else None
        self.enabled_detectors = self.config.get("enabled_detectors", ["image", "table", "formula", "chart"])
        self.confidence_threshold = self.config.get("confidence_threshold", 0.5)

    def process(self, input_data: DocContent) -> ProcessResult:
        """
        检测文档元素。

        Args:
            input_data: 解析后的文档内容

        Returns:
            ProcessResult，包含更新后的DocContent和ElementList
        """
        from core.schema import FileType

        elements = ElementList()

        # 检查 metadata 是否已有元素信息（DocParser 提取的）
        metadata = input_data.metadata or {}
        has_metadata_info = any(
            metadata.get(key) is not None
            for key in ["has_image", "has_table", "has_chart"]
        )

        # 优先使用 metadata（所有文件类型都适用）
        if has_metadata_info:
            return self._process_from_metadata(input_data, elements)

        # === PDF 备用方案：使用 OCR 检测页面图像 ===
        if input_data.file_type == FileType.PDF and input_data.pages:
            return self._process_with_ocr(input_data, elements)

        # 其他情况返回空结果
        return ProcessResult(
            success=True,
            data=(input_data, elements),
            metadata={"warning": "No metadata and no pages for OCR detection"}
        )

    def _process_from_metadata(self, input_data: DocContent, elements: ElementList) -> ProcessResult:
        """
        从 metadata 读取结构化元素信息（用于非 PDF 文档）。

        docx/pptx/xlsx 的元素信息由 DocParser 在解析时提取到 metadata 中。
        """
        metadata = input_data.metadata or {}

        # 根据 metadata 中的标志创建虚拟元素（用于后续判断 has_* 字段）
        if metadata.get("has_image", False):
            # 添加一个虚拟元素表示存在图片
            count = metadata.get("image_count", 1)
            for i in range(min(count, 1)):  # 至少添加一个表示存在
                elements.images.append(ElementInfo(
                    bbox=[0, 0, 0, 0],
                    page=0,
                    confidence=1.0,
                    extra={"source": "metadata"}
                ))

        if metadata.get("has_table", False):
            count = metadata.get("table_count", 1)
            for i in range(min(count, 1)):
                elements.tables.append(ElementInfo(
                    bbox=[0, 0, 0, 0],
                    page=0,
                    confidence=1.0,
                    extra={"source": "metadata"}
                ))

        if metadata.get("has_formula", False):
            elements.formulas.append(ElementInfo(
                bbox=[0, 0, 0, 0],
                page=0,
                confidence=1.0,
                extra={"source": "metadata"}
            ))

        if metadata.get("has_chart", False):
            count = metadata.get("chart_count", 1)
            for i in range(min(count, 1)):
                elements.charts.append(ElementInfo(
                    bbox=[0, 0, 0, 0],
                    page=0,
                    confidence=1.0,
                    extra={"source": "metadata"}
                ))

        return ProcessResult(
            success=True,
            data=(input_data, elements),
            metadata={
                "source": "metadata",
                "images_count": len(elements.images),
                "tables_count": len(elements.tables),
                "formulas_count": len(elements.formulas),
                "charts_count": len(elements.charts),
            }
        )

    def _process_with_ocr(self, input_data: DocContent, elements: ElementList) -> ProcessResult:
        """
        使用 OCR 检测页面图像中的元素（用于 PDF）。
        """
        # 如果没有OCR模型，返回空结果
        if self.ocr_model is None:
            return ProcessResult(
                success=True,
                data=(input_data, ElementList()),
                metadata={"warning": "No OCR model provided, skipping element detection"}
            )

        # 遍历每一页进行检测
        for page_idx, page_image in enumerate(input_data.pages):
            try:
                detected = self.ocr_model.detect_elements(page_image)

                # 处理检测结果
                if "image" in self.enabled_detectors:
                    for img in detected.get("images", []):
                        if img.get("confidence", 0) >= self.confidence_threshold:
                            elements.images.append(ElementInfo(
                                bbox=img.get("bbox", []),
                                page=page_idx,
                                confidence=img.get("confidence", 0.0),
                            ))

                if "table" in self.enabled_detectors:
                    for tbl in detected.get("tables", []):
                        if tbl.get("confidence", 0) >= self.confidence_threshold:
                            elements.tables.append(ElementInfo(
                                bbox=tbl.get("bbox", []),
                                page=page_idx,
                                confidence=tbl.get("confidence", 0.0),
                                extra={"cells": tbl.get("cells", [])}
                            ))

                if "formula" in self.enabled_detectors:
                    for frm in detected.get("formulas", []):
                        if frm.get("confidence", 0) >= self.confidence_threshold:
                            elements.formulas.append(ElementInfo(
                                bbox=frm.get("bbox", []),
                                page=page_idx,
                                confidence=frm.get("confidence", 0.0),
                                extra={"latex": frm.get("latex", "")}
                            ))

                if "chart" in self.enabled_detectors:
                    for cht in detected.get("charts", []):
                        if cht.get("confidence", 0) >= self.confidence_threshold:
                            elements.charts.append(ElementInfo(
                                bbox=cht.get("bbox", []),
                                page=page_idx,
                                confidence=cht.get("confidence", 0.0),
                                extra={"type": cht.get("type", "unknown")}
                            ))

            except Exception as e:
                # 单页检测失败不中断整体流程
                return ProcessResult(
                    success=False,
                    errors=[f"Error detecting elements on page {page_idx}: {str(e)}"]
                )

        return ProcessResult(
            success=True,
            data=(input_data, elements),
            metadata={
                "source": "ocr",
                "images_count": len(elements.images),
                "tables_count": len(elements.tables),
                "formulas_count": len(elements.formulas),
                "charts_count": len(elements.charts),
            }
        )
