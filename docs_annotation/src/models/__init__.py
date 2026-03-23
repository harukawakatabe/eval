"""OCR和LLM模型接口。"""

from docs_annotation.src.models.ocr import OCRModel, MockOCR
from docs_annotation.src.models.llm import LLMModel, MockLLM

__all__ = [
    "OCRModel",
    "MockOCR",
    "LLMModel",
    "MockLLM",
]
