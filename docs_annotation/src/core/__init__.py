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
from .logger import AnnotationLogger, get_logger, set_log_level

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
    "AnnotationLogger",
    "get_logger",
    "set_log_level",
]
