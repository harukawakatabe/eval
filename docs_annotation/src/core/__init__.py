"""文档标注系统核心框架。"""

from .base import BaseProcessor, ProcessResult
from .pipeline import Pipeline
from .schema import (
    FileType,
    LayoutType,
    TableProfile,
    ChartProfile,
    PDFProfile,
    DocumentAnnotation,
)

__all__ = [
    "BaseProcessor",
    "ProcessResult",
    "Pipeline",
    "FileType",
    "LayoutType",
    "TableProfile",
    "ChartProfile",
    "PDFProfile",
    "DocumentAnnotation",
]
