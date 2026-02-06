"""统一日志工具 - 提供详细的解析过程日志。"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class AnnotationLogger:
    """
    文档标注系统统一日志器。
    
    提供结构化的日志输出，包含：
    - 文件信息
    - 解析阶段
    - 检测到的元素
    - OCR 调用信息
    - 错误和警告
    """
    
    _instance: Optional['AnnotationLogger'] = None
    _initialized: bool = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self, 
        level: int = logging.INFO, 
        name: str = "docs_annotation",
        log_to_file: bool = False,
        log_dir: Optional[Path] = None
    ):
        """
        初始化日志器。
        
        Args:
            level: 日志级别 (logging.DEBUG, logging.INFO, etc.)
            name: 日志器名称
            log_to_file: 是否将日志保存到文件
            log_dir: 日志文件目录（默认为 docs_annotation/logs）
        """
        if AnnotationLogger._initialized:
            return
            
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.log_file_path = None  # 保存日志文件路径
        
        # 避免重复添加 handler
        if not self.logger.handlers:
            # 创建格式化器
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            )
            
            # 控制台输出
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # 文件输出（如果启用）
            if log_to_file:
                # 确定日志目录
                if log_dir is None:
                    # 默认使用 docs_annotation/logs
                    log_dir = Path(__file__).parent.parent.parent / "logs"
                
                log_dir = Path(log_dir)
                log_dir.mkdir(parents=True, exist_ok=True)
                
                # 生成日志文件名（使用时间戳）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = log_dir / f"annotation_{timestamp}.log"
                self.log_file_path = log_file
                
                # 创建文件处理器
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(level)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
        
        AnnotationLogger._initialized = True
    
    def set_level(self, level: int) -> None:
        """设置日志级别。"""
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)
    
    # === 文件级别日志 ===
    
    def file_start(self, file_path: str, file_type: str) -> None:
        """记录开始处理文件。"""
        self.logger.info(f"{'='*60}")
        self.logger.info(f"[FILE] 开始处理: {file_path}")
        self.logger.info(f"   文件类型: {file_type}")
    
    def file_end(self, file_path: str, success: bool, duration_ms: Optional[float] = None) -> None:
        """记录文件处理完成。"""
        status = "[OK]" if success else "[FAIL]"
        duration_str = f" ({duration_ms:.0f}ms)" if duration_ms else ""
        self.logger.info(f"{status} 处理完成: {file_path}{duration_str}")
        self.logger.info(f"{'='*60}")
    
    # === 解析器日志 ===
    
    def parser_start(self, parser_name: str) -> None:
        """记录解析器开始。"""
        self.logger.info(f"[PARSER] 使用解析器: {parser_name}")
    
    def parser_fallback(self, from_parser: str, to_parser: str, reason: str) -> None:
        """记录解析器回退。"""
        self.logger.warning(f"[WARN] 解析器回退: {from_parser} -> {to_parser}")
        self.logger.warning(f"   原因: {reason}")
    
    # === 元素检测日志 ===
    
    def elements_detected(
        self, 
        page_count: int,
        images: int = 0, 
        tables: int = 0, 
        formulas: int = 0, 
        charts: int = 0,
        table_pages: list = None,
        image_pages: list = None
    ) -> None:
        """记录检测到的元素。"""
        self.logger.info(f"[RESULT] 解析结果:")
        self.logger.info(f"   页数: {page_count}")
        self.logger.info(f"   图片: {images} 个" + (f" (页: {image_pages})" if image_pages else ""))
        self.logger.info(f"   表格: {tables} 个" + (f" (页: {table_pages})" if table_pages else ""))
        self.logger.info(f"   公式: {formulas} 个")
        self.logger.info(f"   图表: {charts} 个")
    
    def table_info(self, table_idx: int, page: int, rows: int = 0, cols: int = 0, bbox: list = None) -> None:
        """记录表格详细信息。"""
        bbox_str = f", bbox={bbox}" if bbox else ""
        self.logger.debug(f"   表格[{table_idx}]: 页{page}, {rows}行x{cols}列{bbox_str}")
    
    # === OCR 日志 ===
    
    def ocr_start(self, page_idx: int, image_size: tuple = None) -> None:
        """记录 OCR 开始。"""
        size_str = f" ({image_size[0]}x{image_size[1]})" if image_size else ""
        self.logger.debug(f"[OCR] 处理页 {page_idx}{size_str}")
    
    def ocr_result(self, page_idx: int, detected: dict) -> None:
        """记录 OCR 结果。"""
        summary = ", ".join([
            f"{k}={len(v)}" for k, v in detected.items() if v
        ])
        if summary:
            self.logger.debug(f"   OCR 页{page_idx} 结果: {summary}")
    
    def ocr_error(self, page_idx: int, error: str) -> None:
        """记录 OCR 错误。"""
        self.logger.error(f"[ERROR] OCR 页{page_idx} 失败: {error}")
    
    def ocr_skip(self, reason: str) -> None:
        """记录跳过 OCR 的原因。"""
        self.logger.debug(f"[SKIP] 跳过 OCR: {reason}")
    
    # === 特征提取日志 ===
    
    def feature_extracted(
        self,
        table_dominant: Optional[bool] = None,
        cross_page_table: bool = False,
        long_table: bool = False,
        cross_page_chart: bool = False,
        table_page_ratio: float = 0.0
    ) -> None:
        """记录提取的特征。"""
        self.logger.info(f"[FEATURE] 特征提取:")
        if table_dominant is not None:
            self.logger.info(f"   表格主导: {table_dominant} (表格页占比: {table_page_ratio:.1%})")
        self.logger.info(f"   跨页表格: {cross_page_table}")
        self.logger.info(f"   长表格: {long_table}")
        self.logger.info(f"   跨页图表: {cross_page_chart}")
    
    # === 布局分类日志 ===
    
    def layout_classified(self, layout: str, reason: str = "") -> None:
        """记录布局分类结果。"""
        reason_str = f" ({reason})" if reason else ""
        self.logger.info(f"[LAYOUT] 布局类型: {layout}{reason_str}")
    
    # === 通用日志 ===
    
    def debug(self, msg: str) -> None:
        """调试日志。"""
        self.logger.debug(msg)
    
    def info(self, msg: str) -> None:
        """信息日志。"""
        self.logger.info(msg)
    
    def warning(self, msg: str) -> None:
        """警告日志。"""
        self.logger.warning(f"[WARN] {msg}")
    
    def error(self, msg: str) -> None:
        """错误日志。"""
        self.logger.error(f"[ERROR] {msg}")


# 全局日志实例
_logger: Optional[AnnotationLogger] = None


def get_logger(
    level: int = logging.INFO,
    log_to_file: bool = False,
    log_dir: Optional[Path] = None
) -> AnnotationLogger:
    """
    获取全局日志实例。
    
    Args:
        level: 日志级别
        log_to_file: 是否将日志保存到文件
        log_dir: 日志文件目录（默认为 docs_annotation/logs）
    """
    global _logger
    if _logger is None:
        _logger = AnnotationLogger(level=level, log_to_file=log_to_file, log_dir=log_dir)
    return _logger


def set_log_level(level: int) -> None:
    """设置全局日志级别。"""
    get_logger().set_level(level)
