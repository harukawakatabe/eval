"""文档标注系统核心框架。"""

from docs_annotation.src.core.base import BaseProcessor, ProcessResult
from docs_annotation.src.core.pipeline import Pipeline
from docs_annotation.src.core.schema import (
    FileType,
    LayoutType,
    TableProfile,
    ChartProfile,
    PDFProfile,
    DocumentAnnotation,
)
from docs_annotation.src.core.logger import AnnotationLogger, get_logger, set_log_level

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
