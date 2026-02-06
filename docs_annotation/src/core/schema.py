"""文档标注Schema定义。"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from enum import Enum


class FileType(str, Enum):
    """支持的文档文件类型。"""

    PDF = "pdf"
    DOC = "doc"
    EXCEL = "excel"
    PPT = "ppt"
    HTML = "html"
    TXT = "txt"
    MD = "md"


# 文件扩展名到 FileType 的映射（公共常量）
EXT_TO_FILE_TYPE: Dict[str, "FileType"] = {
    ".pdf": FileType.PDF,
    ".doc": FileType.DOC,
    ".docx": FileType.DOC,
    ".xls": FileType.EXCEL,
    ".xlsx": FileType.EXCEL,
    ".ppt": FileType.PPT,
    ".pptx": FileType.PPT,
    ".html": FileType.HTML,
    ".htm": FileType.HTML,
    ".txt": FileType.TXT,
    ".md": FileType.MD,
}


class LayoutType(str, Enum):
    """文档布局类型。"""

    SINGLE = "single"
    DOUBLE = "double"
    MIXED = "mixed"


@dataclass
class TableProfile:
    """
    表格特征Profile。

    Attributes:
        long_table: 是否为长表格（跨3页以上）
        cross_page_table: 表格是否跨页
        table_dominant: 表格是否占主导内容（可选）
    """

    long_table: bool = False
    cross_page_table: bool = False
    table_dominant: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，排除None值。"""
        return {k: v for k, v in [
            ("long_table", self.long_table),
            ("cross_page_table", self.cross_page_table),
            ("table_dominant", self.table_dominant),
        ] if v is not None}


@dataclass
class ChartProfile:
    """
    图表特征Profile。

    Attributes:
        cross_page_chart: 图表是否跨页
    """

    cross_page_chart: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "cross_page_chart": self.cross_page_chart,
        }


@dataclass
class DocProfile:
    """
    文档通用标注Profile（适用于所有文档类型）。

    Attributes:
        layout: 文档布局类型（single/double/mixed），非PDF默认single
        has_image: 文档是否包含图片
        has_table: 文档是否包含可被结构化解析的表格
        has_image_table: 文档是否包含图片形式的表格（扫描版/截图，无法结构化解析）
        has_complex_table: 文档是否包含复杂表格（多级表头/大量合并单元格）
        has_formula: 文档是否包含数学公式
        has_chart: 文档是否包含图表
        image_text_mixed: 是否为图文混排（同时包含图片和大量文字）
        reading_order_sensitive: 阅读顺序是否重要（可选，仅PDF）
        table_profile: 表格特征Profile（仅PDF，当has_table=True时）
        chart_profile: 图表特征Profile（仅PDF，当has_chart=True时）
    """

    layout: LayoutType = LayoutType.SINGLE
    has_image: bool = False
    has_table: bool = False
    has_image_table: bool = False
    has_complex_table: bool = False
    has_formula: bool = False
    has_chart: bool = False
    image_text_mixed: bool = False
    reading_order_sensitive: Optional[bool] = None
    table_profile: Optional[TableProfile] = None
    chart_profile: Optional[ChartProfile] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，排除None值。"""
        result: Dict[str, Any] = {
            "layout": self.layout.value,
            "has_image": self.has_image,
            "has_table": self.has_table,
            "has_image_table": self.has_image_table,
            "has_complex_table": self.has_complex_table,
            "has_formula": self.has_formula,
            "has_chart": self.has_chart,
            "image_text_mixed": self.image_text_mixed,
        }

        # 添加可选字段（仅当有值时）
        if self.reading_order_sensitive is not None:
            result["reading_order_sensitive"] = self.reading_order_sensitive
        if self.table_profile is not None:
            result["table_profile"] = self.table_profile.to_dict()
        if self.chart_profile is not None:
            result["chart_profile"] = self.chart_profile.to_dict()

        return result


# 保持向后兼容的别名
PDFProfile = DocProfile


@dataclass
class DocumentAnnotation:
    """
    完整的文档标注结果。

    Attributes:
        doc_id: 文档唯一标识符
        file_type: 文档文件类型
        file_path: 文档文件路径
        doc_profile: 文档通用Profile（所有文件类型都有）
    """

    doc_id: str
    file_type: FileType
    file_path: str = ""
    doc_profile: Optional[DocProfile] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于JSON序列化。"""
        result: Dict[str, Any] = {
            "doc_id": self.doc_id,
            "file_type": self.file_type.value,
        }

        if self.file_path:
            result["file_path"] = self.file_path

        if self.doc_profile is not None:
            result["doc_profile"] = self.doc_profile.to_dict()

        return result

    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串。"""
        import json
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
