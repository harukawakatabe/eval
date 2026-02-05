import sys
import warnings
import logging

# 抑制 pdfplumber/pdfminer 的字体警告
warnings.filterwarnings("ignore", message=".*FontBBox.*")
logging.getLogger("pdfminer").setLevel(logging.ERROR)

sys.path.insert(0, "docs_annotation/src")

from src.service import AnnotationService
from src.models.ocr import MockOCR
from src.models.llm import MockLLM

# 要测试的文件
file_path = "reference/data/Files/城市运营/【高德建店】规范文档建店SOP手册.pdf"

service = AnnotationService(ocr_model=MockOCR(), llm_model=MockLLM())
ann = service.annotate(file_path)
print(ann.to_json())