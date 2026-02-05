"""文档解析器 - 支持多种文件类型。"""

import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.base import BaseProcessor, ProcessResult
from core.schema import DocumentAnnotation, FileType

# 抑制 pdfminer 的字体警告
logging.getLogger("pdfminer").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*FontBBox.*")


@dataclass
class DocContent:
    """
    解析后的文档内容。

    Attributes:
        doc_id: 文档标识符
        file_type: 文件类型枚举
        file_path: 文件路径
        page_count: 页数
        text: 提取的文本内容
        pages: 页面图像字节列表（用于PDF/图片）
        metadata: 额外元数据
    """

    doc_id: str
    file_type: FileType
    file_path: str
    page_count: int = 0
    text: str = ""
    pages: List[bytes] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocParser(BaseProcessor):
    """
    文档解析器 - 支持多种文件类型。

    支持的格式：
    - PDF: pdfplumber 或 PyPDF2
    - DOC/DOCX: python-docx
    - XLS/XLSX: openpyxl
    - PPT/PPTX: python-pptx
    - HTML/HTM: BeautifulSoup
    - TXT/MD: 直接文本读取
    """

    # 文件类型扩展名映射
    _EXT_MAP: Dict[str, FileType] = {
        ".pdf": FileType.PDF,
        ".doc": FileType.DOC,
        ".docx": FileType.DOC,
        ".xls": FileType.EXCEL,
        ".xlsx": FileType.EXCEL,
        ".ppt": FileType.PPT,
        ".pptx": FileType.PPT,
        ".html": FileType.HTML,
        ".htm": FileType.HTML,
        ".txt": FileType.TXT,
        ".md": FileType.MD,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化文档解析器。"""
        super().__init__(config)
        self.supported_formats = self.config.get(
            "supported_formats",
            ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "html", "htm", "txt", "md"]
        )
        self.extract_images = self.config.get("extract_images", True)

    def process(self, input_data: str) -> ProcessResult:
        """
        解析文档文件。

        Args:
            input_data: 文档文件路径

        Returns:
            包含DocContent的ProcessResult
        """
        file_path = Path(input_data)

        if not file_path.exists():
            return ProcessResult(
                success=False,
                errors=[f"文件不存在: {input_data}"]
            )

        file_type = self._detect_file_type(file_path)

        try:
            if file_type == FileType.PDF:
                content = self._parse_pdf(file_path)
            elif file_type == FileType.DOC:
                content = self._parse_docx(file_path)
            elif file_type == FileType.EXCEL:
                content = self._parse_excel(file_path)
            elif file_type == FileType.PPT:
                content = self._parse_pptx(file_path)
            elif file_type in (FileType.HTML,):
                content = self._parse_html(file_path)
            elif file_type in (FileType.TXT, FileType.MD):
                content = self._parse_text(file_path)
            else:
                return ProcessResult(
                    success=False,
                    errors=[f"不支持的文件类型: {file_type}"]
                )

            return ProcessResult(success=True, data=content)

        except Exception as e:
            return ProcessResult(
                success=False,
                errors=[f"解析文件时出错 {file_path}: {str(e)}"]
            )

    def _detect_file_type(self, file_path: Path) -> FileType:
        """从扩展名检测文件类型。"""
        ext = file_path.suffix.lower()
        return self._EXT_MAP.get(ext, FileType.TXT)

    def _parse_pdf(self, file_path: Path) -> DocContent:
        """解析PDF文档，提取结构化元素信息。"""
        import io
        import sys
        from contextlib import redirect_stderr

        doc_id = file_path.stem

        # 抑制 pdfminer 的字体警告（直接打印到 stderr）
        _stderr = sys.stderr
        
        # 优先使用pdfplumber（更适合表格和图片）
        try:
            import pdfplumber
            sys.stderr = io.StringIO()

            pages: List[bytes] = []
            text_parts: List[str] = []

            # === 结构化元素检测 ===
            total_images = 0
            total_tables = 0
            total_rects = 0
            total_lines = 0
            table_pages = set()  # 记录有表格的页码
            image_pages = set()  # 记录有图片的页码

            with pdfplumber.open(file_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    # 提取文本
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)

                    # 检测图片
                    page_images = page.images
                    if page_images:
                        total_images += len(page_images)
                        image_pages.add(page_idx)

                    # 检测表格
                    page_tables = page.find_tables()
                    if page_tables:
                        total_tables += len(page_tables)
                        table_pages.add(page_idx)

                    # 检测线条和矩形（可能是图表/流程图）
                    total_lines += len(page.lines) if page.lines else 0
                    total_rects += len(page.rects) if page.rects else 0

                    # 如果启用，提取页面图像（用于 OCR 备用）
                    if self.extract_images:
                        import io
                        img = page.to_image().original
                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format='PNG')
                        pages.append(img_bytes.getvalue())

            # 判断是否有图表（基于线条和矩形数量的启发式规则）
            # 如果有很多矩形/线条，可能是流程图或图表
            has_chart = (total_lines + total_rects) > 20
            
            # 恢复 stderr
            sys.stderr = _stderr

            return DocContent(
                doc_id=doc_id,
                file_type=FileType.PDF,
                file_path=str(file_path),
                page_count=len(pdf.pages) if not pages else len(pages),
                text="\n".join(text_parts),
                pages=pages,
                metadata={
                    "has_image": total_images > 0,
                    "has_table": total_tables > 0,
                    "has_formula": False,  # pdfplumber 不检测公式，后续可用 OCR 补充
                    "has_chart": has_chart,
                    "image_count": total_images,
                    "table_count": total_tables,
                    "rect_count": total_rects,
                    "line_count": total_lines,
                    "table_pages": list(table_pages),
                    "image_pages": list(image_pages),
                }
            )

        except ImportError:
            # pdfplumber 未安装，恢复 stderr 并回退到 PyPDF2
            sys.stderr = _stderr
            try:
                import PyPDF2

                text_parts: List[str] = []

                with open(file_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        text_parts.append(page.extract_text() or "")

                return DocContent(
                    doc_id=doc_id,
                    file_type=FileType.PDF,
                    file_path=str(file_path),
                    page_count=len(pdf_reader.pages),
                    text="\n".join(text_parts),
                    pages=[],
                    metadata={
                        "has_image": False,
                        "has_table": False,
                        "has_formula": False,
                        "has_chart": False,
                    }
                )

            except ImportError:
                raise ImportError(
                    "PDF解析需要pdfplumber或PyPDF2。"
                    "请使用: pip install pdfplumber"
                )

    def _parse_docx(self, file_path: Path) -> DocContent:
        """解析Word文档（.doc, .docx），提取结构化元素信息。"""
        try:
            from docx import Document as DocxDocument
            from docx.opc.constants import RELATIONSHIP_TYPE as RT
        except ImportError:
            raise ImportError(
                "Word文档解析需要python-docx。"
                "请使用: pip install python-docx"
            )

        doc = DocxDocument(file_path)

        # 从段落提取文本
        text_parts = [p.text for p in doc.paragraphs]

        # 估算页数（某些段落可能没有 style）
        page_count = len([p for p in doc.paragraphs if p.style and p.style.name and p.style.name.startswith("Heading")])

        # === 结构化元素检测 ===
        # 1. 检测表格
        has_table = len(doc.tables) > 0

        # 2. 检测图片（内联图片 + 关系中的图片）
        has_image = False
        # 检测 inline shapes（内联图片）
        for shape in doc.inline_shapes:
            if shape.type == 3:  # WD_INLINE_SHAPE_TYPE.PICTURE = 3
                has_image = True
                break
        # 检测关系中的图片
        if not has_image:
            for rel in doc.part.rels.values():
                if 'image' in rel.reltype:
                    has_image = True
                    break

        # 3. 检测公式（OMML - Office Math Markup Language）
        has_formula = False
        omml_ns = '{http://schemas.openxmlformats.org/officeDocument/2006/math}'
        for para in doc.paragraphs:
            if omml_ns in para._element.xml:
                has_formula = True
                break

        # 4. 检测图表（嵌入的 chart）
        has_chart = False
        for rel in doc.part.rels.values():
            if 'chart' in rel.reltype:
                has_chart = True
                break

        return DocContent(
            doc_id=file_path.stem,
            file_type=FileType.DOC,
            file_path=str(file_path),
            page_count=max(1, page_count),
            text="\n".join(text_parts),
            metadata={
                "has_image": has_image,
                "has_table": has_table,
                "has_formula": has_formula,
                "has_chart": has_chart,
                "table_count": len(doc.tables),
            }
        )

    def _parse_excel(self, file_path: Path) -> DocContent:
        """解析Excel文档（.xls, .xlsx），提取结构化元素信息。"""
        try:
            import openpyxl
        except ImportError:
            raise ImportError(
                "Excel解析需要openpyxl。"
                "请使用: pip install openpyxl"
            )

        # 不使用 read_only 模式以便访问图片和图表
        wb = openpyxl.load_workbook(file_path, read_only=False)

        text_parts: List[str] = []

        # === 结构化元素检测 ===
        has_image = False
        has_chart = False
        has_formula = False
        image_count = 0
        chart_count = 0
        formula_count = 0

        for sheet in wb.worksheets:
            # 提取文本
            for row in sheet.iter_rows(values_only=True):
                row_text = " ".join(str(cell) for cell in row if cell is not None)
                if row_text.strip():
                    text_parts.append(row_text)

            # 检测图片
            if hasattr(sheet, '_images') and sheet._images:
                has_image = True
                image_count += len(sheet._images)

            # 检测图表
            if hasattr(sheet, '_charts') and sheet._charts:
                has_chart = True
                chart_count += len(sheet._charts)

            # 检测公式（遍历单元格检查是否有公式）
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.data_type == 'f' or (cell.value and isinstance(cell.value, str) and cell.value.startswith('=')):
                        has_formula = True
                        formula_count += 1
                        if formula_count > 10:  # 检测到足够多就停止
                            break
                if formula_count > 10:
                    break

        wb.close()

        return DocContent(
            doc_id=file_path.stem,
            file_type=FileType.EXCEL,
            file_path=str(file_path),
            page_count=len(wb.worksheets),
            text="\n".join(text_parts),
            metadata={
                "has_image": has_image,
                "has_table": True,  # Excel 本身就是表格
                "has_formula": has_formula,
                "has_chart": has_chart,
                "image_count": image_count,
                "chart_count": chart_count,
            }
        )

    def _parse_pptx(self, file_path: Path) -> DocContent:
        """解析PowerPoint文档（.ppt, .pptx），提取结构化元素信息。"""
        try:
            from pptx import Presentation
            from pptx.enum.shapes import MSO_SHAPE_TYPE
        except ImportError:
            raise ImportError(
                "PowerPoint解析需要python-pptx。"
                "请使用: pip install python-pptx"
            )

        prs = Presentation(file_path)

        text_parts: List[str] = []

        # === 结构化元素检测 ===
        has_image = False
        has_table = False
        has_chart = False
        has_formula = False
        table_count = 0
        image_count = 0
        chart_count = 0

        for slide in prs.slides:
            for shape in slide.shapes:
                # 提取文本
                if hasattr(shape, "text") and shape.text:
                    text_parts.append(shape.text)

                # 检测图片
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    has_image = True
                    image_count += 1

                # 检测表格
                if shape.has_table:
                    has_table = True
                    table_count += 1

                # 检测图表
                if shape.has_chart:
                    has_chart = True
                    chart_count += 1

                # 检测公式（OLE 对象或特定类型）
                if shape.shape_type == MSO_SHAPE_TYPE.OLE_CONTROL_OBJECT:
                    # 可能是公式对象
                    has_formula = True

        return DocContent(
            doc_id=file_path.stem,
            file_type=FileType.PPT,
            file_path=str(file_path),
            page_count=len(prs.slides),
            text="\n".join(text_parts),
            metadata={
                "has_image": has_image,
                "has_table": has_table,
                "has_formula": has_formula,
                "has_chart": has_chart,
                "table_count": table_count,
                "image_count": image_count,
                "chart_count": chart_count,
            }
        )

    def _parse_html(self, file_path: Path) -> DocContent:
        """解析HTML文档。"""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "HTML解析需要beautifulsoup4。"
                "请使用: pip install beautifulsoup4"
            )

        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")

        # 移除script和style元素
        for script in soup(["script", "style"]):
            script.decompose()

        # 获取文本
        text = soup.get_text(separator="\n", strip=True)

        return DocContent(
            doc_id=file_path.stem,
            file_type=FileType.HTML,
            file_path=str(file_path),
            page_count=1,
            text=text,
        )

    def _parse_text(self, file_path: Path) -> DocContent:
        """解析纯文本或Markdown文档。"""
        encodings = ["utf-8", "gbk", "gb2312", "latin-1"]

        text = ""
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    text = f.read()
                break
            except UnicodeDecodeError:
                continue

        # 估算页数（按行数）
        lines = text.split("\n")
        page_count = max(1, len(lines) // 50)

        return DocContent(
            doc_id=file_path.stem,
            file_type=FileType.MD if file_path.suffix == ".md" else FileType.TXT,
            file_path=str(file_path),
            page_count=page_count,
            text=text,
        )
