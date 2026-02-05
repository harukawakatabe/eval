"""OCR模型接口 - 用于元素检测。"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class OCRModel(ABC):
    """
    OCR模型接口 - 用于检测文档元素。

    实现可以封装不同的OCR引擎，如：
    - PaddleOCR
    - Tesseract
    - EasyOCR
    - 等等
    """

    @abstractmethod
    def detect_elements(self, image_data: bytes) -> Dict[str, List[Dict[str, Any]]]:
        """
        检测页面中的元素。

        Args:
            image_data: 原始图像字节

        Returns:
            包含检测元素的字典：
            {
                "images": [{"bbox": [x1, y1, x2, y2], "confidence": 0.9}],
                "tables": [{"bbox": [x1, y1, x2, y2], "cells": [...]}],
                "formulas": [{"bbox": [x1, y1, x2, y2], "latex": "..."}],
                "charts": [{"bbox": [x1, y1, x2, y2], "type": "bar"}]
            }

        Note:
            - bbox格式: [x1, y1, x2, y2] 像素坐标
            - 空列表表示未检测到元素
        """
        pass

    @abstractmethod
    def extract_text(self, image_data: bytes) -> str:
        """
        从页面图像中提取文本。

        Args:
            image_data: 原始图像字节

        Returns:
            提取的文本字符串
        """
        pass


class MockOCR(OCRModel):
    """
    Mock OCR实现 - 用于测试。

    所有操作返回空结果。
    """

    def detect_elements(self, image_data: bytes) -> Dict[str, List[Dict[str, Any]]]:
        """返回空检测结果。"""
        return {
            "images": [],
            "tables": [],
            "formulas": [],
            "charts": [],
        }

    def extract_text(self, image_data: bytes) -> str:
        """返回空文本。"""
        return ""


class PaddleOCRModel(OCRModel):
    """
    PaddleOCR实现。

    需要: pip install paddleocr
    """

    def __init__(self, lang: str = "ch", use_angle_cls: bool = True):
        """
        初始化PaddleOCR。

        Args:
            lang: 语言代码（'ch'中文，'en'英文）
            use_angle_cls: 是否使用角度分类器
        """
        try:
            from paddleocr import PaddleOCR as PPOCR
            self.model = PPOCR(use_angle_cls=use_angle_cls, lang=lang)
        except ImportError:
            raise ImportError(
                "PaddleOCR未安装。"
                "请使用: pip install paddleocr"
            )

    def detect_elements(self, image_data: bytes) -> Dict[str, List[Dict[str, Any]]]:
        """
        使用PaddleOCR检测元素。

        Note: 这是基础实现。
        生产环境建议使用专用检测模型。
        """
        import io
        from PIL import Image

        # 将字节转换为PIL图像
        image = Image.open(io.BytesIO(image_data))

        # 运行OCR
        result = self.model.ocr(image, cls=True)

        # 解析结果（基础实现）
        detected: Dict[str, List[Dict[str, Any]]] = {
            "images": [],
            "tables": [],
            "formulas": [],
            "charts": [],
        }

        if result and result[0]:
            for line in result[0]:
                bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                # 将多边形转换为bbox [x1, y1, x2, y2]
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                detected["images"].append({
                    "bbox": [min(x_coords), min(y_coords), max(x_coords), max(y_coords)],
                    "confidence": line[1][1],
                })

        return detected

    def extract_text(self, image_data: bytes) -> str:
        """使用PaddleOCR提取文本。"""
        import io
        from PIL import Image

        image = Image.open(io.BytesIO(image_data))
        result = self.model.ocr(image, cls=True)

        if not result or not result[0]:
            return ""

        texts = [line[1][0] for line in result[0]]
        return "\n".join(texts)


class TesseractOCRModel(OCRModel):
    """
    Tesseract OCR实现。

    需要: pip install pytesseract
    还需要在系统上安装Tesseract。
    """

    def __init__(self, lang: str = "chi_sim+eng"):
        """
        初始化Tesseract OCR。

        Args:
            lang: 语言代码（如 'chi_sim+eng' 表示中英文）
        """
        try:
            import pytesseract
            self.pytesseract = pytesseract
        except ImportError:
            raise ImportError(
                "pytesseract未安装。"
                "请使用: pip install pytesseract"
            )

        self.lang = lang

    def detect_elements(self, image_data: bytes) -> Dict[str, List[Dict[str, Any]]]:
        """
        使用Tesseract检测元素。

        Note: Tesseract本身不原生支持检测表格/图表等元素。
        此实现主要关注文本区域。
        """
        import io
        from PIL import Image

        image = Image.open(io.BytesIO(image_data))

        # 获取字典格式的数据
        data = self.pytesseract.image_to_data(
            image, lang=self.lang, output_type=self.pytesseract.Output.DICT
        )

        detected: Dict[str, List[Dict[str, Any]]] = {
            "images": [],
            "tables": [],
            "formulas": [],
            "charts": [],
        }

        # 将文本分组为块
        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
            if text:
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                detected["images"].append({
                    "bbox": [x, y, x + w, y + h],
                    "confidence": data["conf"][i] / 100.0,
                })

        return detected

    def extract_text(self, image_data: bytes) -> str:
        """使用Tesseract提取文本。"""
        import io
        from PIL import Image

        image = Image.open(io.BytesIO(image_data))
        return self.pytesseract.image_to_string(image, lang=self.lang)
