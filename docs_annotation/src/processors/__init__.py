"""文档标注处理器模块。"""

from .doc_parser import DocParser, DocContent, ParserBackend, create_parser
from .element_detector import ElementDetector, ElementList
from .feature_extractor import FeatureExtractor, FeatureSet
from .layout_classifier import LayoutClassifier

# 延迟导入 DoclingParser（避免 Docling 未安装时报错）
def get_docling_parser():
    """获取 Docling 解析器（延迟导入）。"""
    from .docling_parser import DoclingParser
    return DoclingParser

__all__ = [
    "DocParser",
    "DocContent",
    "ParserBackend",
    "create_parser",
    "get_docling_parser",
    "ElementDetector",
    "ElementList",
    "FeatureExtractor",
    "FeatureSet",
    "LayoutClassifier",
]
