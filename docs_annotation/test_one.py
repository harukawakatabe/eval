#!/usr/bin/env python
"""单文件标注测试脚本。

支持命令行参数：
    python test_one.py <file_path> [options]
    
选项：
    -v, --verbose      启用详细日志 (DEBUG级别)
    -q, --quiet        静默模式 (WARNING级别)
    --parser <type>    解析器类型: auto, docling, legacy (默认: auto)
    --no-ocr           不使用OCR
    --help             显示帮助信息

示例：
    python test_one.py document.pdf -v
    python test_one.py document.docx --parser docling
    python test_one.py document.xlsx -v --parser legacy
"""

import sys
import os
import warnings
import logging
import argparse

# 抑制 pdfplumber/pdfminer 的字体警告
warnings.filterwarnings("ignore", message=".*FontBBox.*")
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# 将脚本所在目录添加到 Python 路径，确保能找到 src 包
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from src.service import AnnotationService
from src.processors.doc_parser import ParserBackend
from src.models.ocr import MockOCR
from src.models.llm import MockLLM


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="单文件标注测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    python test_one.py document.pdf -v
    python test_one.py document.docx --parser docling
    python test_one.py document.xlsx -v --parser legacy
        """
    )
    
    parser.add_argument(
        "file_path",
        nargs="?",
        default="reference/data/Files/城市运营/【高德建店】规范文档建店SOP手册.pdf",
        help="要标注的文件路径 (默认: 示例PDF)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细日志 (DEBUG级别)"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="静默模式 (WARNING级别)"
    )
    
    parser.add_argument(
        "--parser",
        choices=["auto", "docling", "legacy"],
        default="auto",
        help="解析器类型 (默认: auto)"
    )
    
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="不使用OCR"
    )
    
    return parser.parse_args()


def main():
    """主函数。"""
    args = parse_args()
    
    # 确定日志级别
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    
    # 确定解析器类型
    parser_map = {
        "auto": ParserBackend.AUTO,
        "docling": ParserBackend.DOCLING,
        "legacy": ParserBackend.LEGACY,
    }
    parser_backend = parser_map[args.parser]
    
    # 确定OCR模型
    ocr_model = None if args.no_ocr else MockOCR()
    
    # 打印配置信息
    if not args.quiet:
        print(f"{'='*60}")
        print(f"文件: {args.file_path}")
        print(f"解析器: {args.parser}")
        print(f"日志级别: {logging.getLevelName(log_level)}")
        print(f"OCR: {'禁用' if args.no_ocr else '启用(Mock)'}")
        print(f"{'='*60}")
    
    # 创建服务并标注
    service = AnnotationService(
        ocr_model=ocr_model,
        llm_model=MockLLM(),
        parser_backend=parser_backend,
        log_level=log_level
    )
    
    try:
        ann = service.annotate(args.file_path)
        
        # 输出结果
        if not args.quiet:
            print("\n" + "="*60)
            print("标注结果:")
            print("="*60)
        print(ann.to_json())
        
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()