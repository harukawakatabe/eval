"""文档标注系统 - Document Annotation System。

一个灵活、可扩展的文档标注框架，支持多种文档格式的结构化标注。

主要功能:
- 支持PDF、Word、Excel、PPT、HTML、TXT等多种格式
- 检测文档中的图片、表格、公式、图表等元素
- 提取跨页、长表格等结构特征
- 分类文档布局类型（单页/双页/混合）
- 可插拔的OCR和LLM模型接口

使用示例:
    from service import AnnotationService
    from models.ocr import PaddleOCRModel
    from models.llm import OpenAILLM

    service = AnnotationService(
        ocr_model=PaddleOCRModel(),
        llm_model=OpenAILLM(api_key="...")
    )

    annotation = service.annotate("document.pdf")
    print(annotation.to_json())
"""

__version__ = "0.1.0"
__author__ = "Your Name"

from .service import AnnotationService
from .core.schema import DocumentAnnotation, FileType, LayoutType
from .core.pipeline import Pipeline
from .core.base import BaseProcessor, ProcessResult

__all__ = [
    "AnnotationService",
    "DocumentAnnotation",
    "FileType",
    "LayoutType",
    "Pipeline",
    "BaseProcessor",
    "ProcessResult",
]
