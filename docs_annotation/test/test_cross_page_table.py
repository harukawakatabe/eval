#!/usr/bin/env python
"""测试跨页表格检测功能。

测试目标：
1. DOC/DOCX 文件的表格跨页检测
2. PPT/PPTX 文件的表格跨页检测
3. PDF 文件的表格跨页检测

使用方法：
    python -m test.test_cross_page_table [file_path]
    
示例：
    python -m test.test_cross_page_table "reference/data/Files/业务交付管理/12月百应分结果及大区排名.docx"
"""

import sys
import logging
import argparse
from pathlib import Path

# 添加正确的路径
script_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(script_dir))

from service import AnnotationService
from processors.doc_parser import ParserBackend
from models.ocr import MockOCR
from models.llm import MockLLM


def test_file(file_path: str, parser_backend: ParserBackend = ParserBackend.LEGACY):
    """测试单个文件的跨页表格检测。"""
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
        
        # 检查表格特征
        if ann.doc_profile and ann.doc_profile.table_profile:
            tp = ann.doc_profile.table_profile
            print("\n--- 表格特征分析 ---")
            print(f"  has_table: {ann.doc_profile.has_table}")
            print(f"  cross_page_table: {tp.cross_page_table}")
            print(f"  long_table: {tp.long_table}")
            print(f"  table_dominant: {tp.table_dominant}")
        else:
            print("\n⚠️ 未检测到表格特征")
            
        return ann
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="测试跨页表格检测")
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
    
    # 如果提供了文件路径，测试单个文件
    if args.file_path:
        test_file(args.file_path, parser_map[args.parser])
    else:
        # 默认测试用例
        test_files = [
            # 跨页表格测试（需要替换为实际路径）
            # "reference/data/Files/业务交付管理/12月百应分结果及大区排名.docx",
        ]
        
        if not test_files:
            print("请提供文件路径，或在脚本中配置 test_files 列表")
            print("用法: python -m test.test_cross_page_table <file_path>")
            return
        
        for fp in test_files:
            test_file(fp, parser_map[args.parser])


if __name__ == "__main__":
    main()
