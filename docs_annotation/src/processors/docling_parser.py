"""Docling 解析器 - 基于 Docling 库的高精度文档解析。"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..core.base import BaseProcessor, ProcessResult
from ..core.schema import DocumentAnnotation, FileType, EXT_TO_FILE_TYPE
from ..core.logger import get_logger
from .doc_parser import DocContent

# 抑制 Docling 内部日志
logging.getLogger("docling").setLevel(logging.WARNING)


class DoclingParser(BaseProcessor):
    """
    Docling 文档解析器 - 高精度多格式支持。
    
    支持的格式：
    - PDF: 高精度表格和布局检测
    - DOC/DOCX: Word 文档
    - XLS/XLSX: Excel 表格
    - PPT/PPTX: PowerPoint 演示文稿
    - HTML: 网页
    
    特点：
    - 97.9% 表格提取准确率
    - 自动检测页码
    - 结构化输出（表格行列、多级表头）
    - 公式检测（LaTeX）
    - 阅读顺序检测
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 Docling 解析器。
        
        Args:
            config: 配置字典，可包含：
                - ocr_enabled: 是否启用 OCR（默认 True）
                - table_structure: 是否提取表格结构（默认 True）
                - extract_images: 是否提取图片（默认 True）
        """
        super().__init__(config)
        self.ocr_enabled = self.config.get("ocr_enabled", True)
        self.table_structure = self.config.get("table_structure", True)
        self.extract_images = self.config.get("extract_images", True)
        self.logger = get_logger()
        
        # 延迟加载 Docling
        self._converter = None
        self._docling_available = None
    
    def _get_converter(self):
        """延迟加载 Docling DocumentConverter。"""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                self._converter = DocumentConverter()
                self._docling_available = True
                self.logger.debug("Docling 加载成功")
            except ImportError:
                self._docling_available = False
                self.logger.warning("Docling 未安装，将使用备用解析器")
        return self._converter
    
    def is_available(self) -> bool:
        """检查 Docling 是否可用。"""
        if self._docling_available is None:
            self._get_converter()
        return self._docling_available
    
    def process(self, input_data: str) -> ProcessResult:
        """
        解析文档文件。
        
        Args:
            input_data: 文档文件路径
            
        Returns:
            包含 DocContent 的 ProcessResult
        """
        file_path = Path(input_data)
        
        if not file_path.exists():
            return ProcessResult(
                success=False,
                errors=[f"文件不存在: {input_data}"]
            )
        
        file_type = self._detect_file_type(file_path)
        self.logger.parser_start("Docling")
        
        # 检查 Docling 是否可用
        converter = self._get_converter()
        if converter is None:
            return ProcessResult(
                success=False,
                errors=["Docling 未安装。请使用: pip install docling"]
            )
        
        try:
            # 使用 Docling 转换文档
            conv_result = converter.convert(str(file_path))
            doc = conv_result.document
            
            # 提取内容
            content = self._extract_content(file_path, file_type, doc)
            
            # 记录解析结果
            self.logger.elements_detected(
                page_count=content.page_count,
                images=content.metadata.get("image_count", 0),
                tables=content.metadata.get("table_count", 0),
                formulas=content.metadata.get("formula_count", 0),
                charts=content.metadata.get("chart_count", 0),
                table_pages=content.metadata.get("table_pages", []),
                image_pages=content.metadata.get("image_pages", [])
            )
            
            return ProcessResult(success=True, data=content)
            
        except Exception as e:
            self.logger.error(f"Docling 解析失败: {str(e)}")
            return ProcessResult(
                success=False,
                errors=[f"Docling 解析文件时出错 {file_path}: {str(e)}"]
            )
    
    def _detect_file_type(self, file_path: Path) -> FileType:
        """从扩展名检测文件类型。"""
        ext = file_path.suffix.lower()
        return EXT_TO_FILE_TYPE.get(ext, FileType.TXT)
    
    def _extract_content(self, file_path: Path, file_type: FileType, doc) -> DocContent:
        """
        从 Docling 文档对象提取内容。
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            doc: Docling 文档对象
            
        Returns:
            DocContent 实例
        """
        doc_id = file_path.stem
        
        # 提取文本
        try:
            text = doc.export_to_markdown()
        except Exception:
            text = ""
        
        # 获取页数
        page_count = self._get_page_count(doc)
        
        # === 元素检测 ===
        tables_info = self._extract_tables(doc)
        images_info = self._extract_images(doc)
        formulas_info = self._extract_formulas(doc)
        charts_info = self._extract_charts(doc)
        
        # 收集页码信息
        table_pages: Set[int] = set()
        image_pages: Set[int] = set()
        
        for tbl in tables_info:
            if tbl.get("page") is not None:
                table_pages.add(tbl["page"])
        
        for img in images_info:
            if img.get("page") is not None:
                image_pages.add(img["page"])
        
        # 判断 has_chart（Docling 可能没有直接的图表检测）
        # 可以基于图片特征或文档内容启发式判断
        has_chart = len(charts_info) > 0
        
        # 检测图片表格（有图片但没有结构化表格）
        has_image_table = len(images_info) > 0 and len(tables_info) == 0
        
        # 检测复杂表格
        has_complex_table = self._detect_complex_table(tables_info)
        
        return DocContent(
            doc_id=doc_id,
            file_type=file_type,
            file_path=str(file_path),
            page_count=page_count,
            text=text,
            pages=[],  # Docling 不需要页面图像
            metadata={
                "has_image": len(images_info) > 0,
                "has_table": len(tables_info) > 0,
                "has_image_table": has_image_table,
                "has_complex_table": has_complex_table,
                "has_formula": len(formulas_info) > 0,
                "has_chart": has_chart,
                "image_count": len(images_info),
                "table_count": len(tables_info),
                "formula_count": len(formulas_info),
                "chart_count": len(charts_info),
                "table_pages": sorted(table_pages),
                "image_pages": sorted(image_pages),
                # 详细表格信息（用于跨页检测）
                "tables_detail": tables_info,
                "images_detail": images_info,
            }
        )
    
    def _get_page_count(self, doc) -> int:
        """获取文档页数。"""
        try:
            # Docling 文档可能有 pages 属性
            if hasattr(doc, 'pages') and doc.pages:
                return len(doc.pages)
            # 或者从 metadata 获取
            if hasattr(doc, 'metadata') and doc.metadata:
                return doc.metadata.get('page_count', 1)
        except Exception:
            pass
        return 1
    
    def _extract_tables(self, doc) -> List[Dict[str, Any]]:
        """
        提取表格信息。
        
        Returns:
            表格信息列表，每个包含：
            - page: 页码
            - rows: 行数
            - cols: 列数
            - bbox: 边界框（如果有）
        """
        tables_info = []
        
        try:
            # Docling 的表格访问方式
            if hasattr(doc, 'tables'):
                for idx, table in enumerate(doc.tables):
                    info = {
                        "index": idx,
                        "page": None,
                        "rows": 0,
                        "cols": 0,
                        "bbox": None
                    }
                    
                    # 获取页码
                    if hasattr(table, 'prov') and table.prov:
                        # prov 可能包含位置信息
                        for prov in table.prov:
                            if hasattr(prov, 'page_no'):
                                info["page"] = prov.page_no
                            elif hasattr(prov, 'page'):
                                info["page"] = prov.page
                            if hasattr(prov, 'bbox'):
                                info["bbox"] = list(prov.bbox) if prov.bbox else None
                    
                    # 获取表格尺寸
                    if hasattr(table, 'num_rows'):
                        info["rows"] = table.num_rows
                        info["cols"] = getattr(table, 'num_cols', 0)
                    elif hasattr(table, 'data') and table.data:
                        # TableData 可能有 grid 或其他属性
                        try:
                            if hasattr(table.data, 'grid'):
                                info["rows"] = len(table.data.grid) if table.data.grid else 0
                                if table.data.grid:
                                    info["cols"] = len(table.data.grid[0]) if table.data.grid[0] else 0
                            elif hasattr(table.data, '__iter__'):
                                data_list = list(table.data)
                                info["rows"] = len(data_list)
                                if data_list:
                                    info["cols"] = len(data_list[0]) if hasattr(data_list[0], '__len__') else 0
                        except (TypeError, AttributeError):
                            pass
                    
                    # 记录详细日志
                    self.logger.table_info(
                        idx, 
                        info["page"] or 0, 
                        info["rows"], 
                        info["cols"],
                        info["bbox"]
                    )
                    
                    tables_info.append(info)
                    
        except Exception as e:
            self.logger.debug(f"提取表格信息时出错: {e}")
        
        return tables_info
    
    def _extract_images(self, doc) -> List[Dict[str, Any]]:
        """提取图片信息。"""
        images_info = []
        
        try:
            if hasattr(doc, 'pictures'):
                for idx, pic in enumerate(doc.pictures):
                    info = {
                        "index": idx,
                        "page": None,
                        "bbox": None
                    }
                    
                    if hasattr(pic, 'prov') and pic.prov:
                        for prov in pic.prov:
                            if hasattr(prov, 'page_no'):
                                info["page"] = prov.page_no
                            elif hasattr(prov, 'page'):
                                info["page"] = prov.page
                            if hasattr(prov, 'bbox'):
                                info["bbox"] = list(prov.bbox) if prov.bbox else None
                    
                    images_info.append(info)
                    
        except Exception as e:
            self.logger.debug(f"提取图片信息时出错: {e}")
        
        return images_info
    
    def _extract_formulas(self, doc) -> List[Dict[str, Any]]:
        """提取公式信息。"""
        formulas_info = []
        
        try:
            # Docling 可能通过 equations 或其他属性提供公式
            if hasattr(doc, 'equations'):
                for idx, eq in enumerate(doc.equations):
                    info = {
                        "index": idx,
                        "page": None,
                        "latex": None
                    }
                    
                    if hasattr(eq, 'prov') and eq.prov:
                        for prov in eq.prov:
                            if hasattr(prov, 'page_no'):
                                info["page"] = prov.page_no
                    
                    if hasattr(eq, 'text'):
                        info["latex"] = eq.text
                    
                    formulas_info.append(info)
                    
        except Exception as e:
            self.logger.debug(f"提取公式信息时出错: {e}")
        
        return formulas_info
    
    def _extract_charts(self, doc) -> List[Dict[str, Any]]:
        """
        提取图表信息。
        
        注意：Docling 可能没有专门的图表检测，
        这里尝试从 figures 或其他属性推断。
        """
        charts_info = []
        
        try:
            # 尝试从 figures 中识别图表
            if hasattr(doc, 'figures'):
                for idx, fig in enumerate(doc.figures):
                    # 简单启发式：如果有 caption 包含"图表"、"chart"等关键词
                    is_chart = False
                    caption = ""
                    
                    if hasattr(fig, 'caption') and fig.caption:
                        caption = str(fig.caption).lower()
                        chart_keywords = ['chart', 'graph', 'plot', '图表', '柱状图', '饼图', '折线图']
                        is_chart = any(kw in caption for kw in chart_keywords)
                    
                    if is_chart:
                        info = {
                            "index": idx,
                            "page": None,
                            "type": "unknown"
                        }
                        
                        if hasattr(fig, 'prov') and fig.prov:
                            for prov in fig.prov:
                                if hasattr(prov, 'page_no'):
                                    info["page"] = prov.page_no
                        
                        charts_info.append(info)
                        
        except Exception as e:
            self.logger.debug(f"提取图表信息时出错: {e}")
        
        return charts_info
    
    def _detect_complex_table(self, tables_info: List[Dict[str, Any]]) -> bool:
        """
        检测是否有复杂表格。
        
        复杂表格判断标准（RAG 场景下难以正确解析）：
        1. 列数过多（>10列）- 在 chunk 中难以保持格式
        2. 行数非常多（>100行）- 容易超出 chunk 大小
        3. 宽表格：列数 >= 7 且行数 > 20
        
        Args:
            tables_info: 表格详细信息列表
            
        Returns:
            是否有复杂表格
        """
        if not tables_info:
            return False
        
        for tbl in tables_info:
            cols = tbl.get("cols", 0)
            rows = tbl.get("rows", 0)
            
            # 列数过多：> 10 列
            if cols > 10:
                self.logger.debug(f"检测到复杂表格：列数 {cols} > 10")
                return True
            
            # 行数非常多：> 100 行
            if rows > 100:
                self.logger.debug(f"检测到复杂表格：行数 {rows} > 100")
                return True
            
            # 宽表格：列数 >= 7 且行数 > 20
            if cols >= 7 and rows > 20:
                self.logger.debug(f"检测到复杂表格：列数 {cols} >= 7 且行数 {rows} > 20")
                return True
        
        return False
