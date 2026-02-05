"""OCR和LLM模型接口。"""

from .ocr import OCRModel, MockOCR
from .llm import LLMModel, MockLLM

__all__ = [
    "OCRModel",
    "MockOCR",
    "LLMModel",
    "MockLLM",
]
