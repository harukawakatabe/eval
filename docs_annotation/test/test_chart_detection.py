#!/usr/bin/env python
"""测试图表检测功能。

测试目标：
1. PDF 中的图表检测（折线图、柱状图、饼图等）
2. DOC/DOCX 中嵌入的图表检测
3. PPT/PPTX 中的图表检测

使用方法：
    python -m test.test_chart_detection [file_path]
"""

import sys
import logging
import argparse
from pathlib import Path

# 添加正确的路径
script_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(script_dir))

from src.service import AnnotationService
from processors.doc_parser import ParserBackend
from models.ocr import MockOCR
from models.llm import MockLLM


def test_file(file_path: str, parser_backend: ParserBackend = ParserBackend.LEGACY):
    """测试单个文件的图表检测。"""
    print(f"\n{'='*70}")
    print(f"测试文件: {file_path}")
    print(f"解析器: {parser_backend.value}")
    print(f"{'='*70}")
    
    service = AnnotationService(
        ocr_model=MockOCR(),
        llm_model=MockLLM(),
        parser_backend=parser_backend,
        log_level=logging.DEBUG
    )
    
    try:
        ann = service.annotate(file_path)
        
        print("\n--- 标注结果 ---")
        print(ann.to_json())
        
        # 分析结果
        if ann.doc_profile:
            dp = ann.doc_profile
            print("\n--- 图表检测分析 ---")
            print(f"  has_chart: {dp.has_chart}")
            print(f"  has_image: {dp.has_image}")
            print(f"  has_table: {dp.has_table}")
            
            if dp.chart_profile:
                cp = dp.chart_profile
                print(f"  cross_page_chart: {cp.cross_page_chart}")
        
        return ann
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="测试图表检测功能")
    parser.add_argument(
        "file_path",
        nargs="?",
        default=None,
        help="要测试的文件路径"
    )
    parser.add_argument(
        "--parser",
        choices=["auto", "docling", "legacy"],
        default="legacy",
        help="解析器类型"
    )
    
    args = parser.parse_args()
    
    parser_map = {
        "auto": ParserBackend.AUTO,
        "docling": ParserBackend.DOCLING,
        "legacy": ParserBackend.LEGACY,
    }
    
    if args.file_path:
        test_file(args.file_path, parser_map[args.parser])
    else:
        print("请提供文件路径")
        print("用法: python -m test.test_chart_detection <file_path>")


if __name__ == "__main__":
    main()
