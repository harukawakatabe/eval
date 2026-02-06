#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试特定的问题文件。"""

import sys
import logging
from pathlib import Path

# 添加正确的路径
script_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(script_dir))

from service import AnnotationService
from processors.doc_parser import ParserBackend
from models.ocr import MockOCR
from models.llm import MockLLM


# 测试文件列表（使用 Path 处理中文路径）
BASE_DIR = Path(r"D:\Project\Test\eval\reference\data\Files")

TEST_FILES = [
    # 1. 跨页表格（DOCX）
    BASE_DIR / "业务交付管理" / "12月百应分结果及大区排名.docx",
    # 2. 表格误识别为图片（PDF）
    BASE_DIR / "业务交付管理" / "2-联想百应服务商收费标准.pdf",
    BASE_DIR / "业务交付管理" / "3-联想百应社区服务站优惠券返还政策.pdf",
    # 3. table_dominant 判断（PDF）
    BASE_DIR / "业务交付管理" / "5-联想百应《优选服务商红黄线管理规则》2025年第四版1001.pdf",
    # 4. 其他测试文件
    BASE_DIR / "城市运营" / "【高德建店】规范文档建店SOP手册.pdf",
]


def test_file(file_path: Path, verbose: bool = False, parser_backend: str = "legacy"):
    """测试单个文件。"""
    print(f"\n{'='*70}")
    print(f"测试文件: {file_path.name}")
    print(f"完整路径: {file_path}")
    print(f"解析器: {parser_backend}")
    print(f"{'='*70}")
    
    if not file_path.exists():
        print(f"[SKIP] 文件不存在")
        return None
    
    log_level = logging.DEBUG if verbose else logging.WARNING
    
    # 选择解析器后端
    backend_map = {
        "legacy": ParserBackend.LEGACY,
        "docling": ParserBackend.DOCLING,
        "auto": ParserBackend.AUTO,
    }
    backend = backend_map.get(parser_backend.lower(), ParserBackend.LEGACY)
    
    service = AnnotationService(
        ocr_model=MockOCR(),
        llm_model=MockLLM(),
        parser_backend=backend,
        log_level=log_level
    )
    
    try:
        ann = service.annotate(str(file_path))
        
        print("\n--- 标注结果 ---")
        print(f"文件类型: {ann.file_type.value}")
        
        if ann.doc_profile:
            dp = ann.doc_profile
            print(f"布局: {dp.layout.value}")
            print(f"has_table: {dp.has_table}")
            print(f"has_image: {dp.has_image}")
            print(f"has_chart: {dp.has_chart}")
            print(f"has_formula: {dp.has_formula}")
            print(f"image_text_mixed: {dp.image_text_mixed}")
            
            if dp.table_profile:
                tp = dp.table_profile
                print("\n--- 表格特征 ---")
                print(f"table_dominant: {tp.table_dominant}")
                print(f"cross_page_table: {tp.cross_page_table}")
                print(f"long_table: {tp.long_table}")
        
        print("\n--- 完整 JSON ---")
        print(ann.to_json())
        
        return ann
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="测试特定问题文件")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志")
    parser.add_argument("-i", "--index", type=int, help="只测试指定索引的文件 (0-based)")
    parser.add_argument("-p", "--parser", default="legacy", 
                        choices=["legacy", "docling", "auto"],
                        help="解析器后端 (默认: legacy)")
    args = parser.parse_args()
    
    print("=" * 70)
    print("测试问题文件")
    print("=" * 70)
    print(f"解析器: {args.parser}")
    
    # 列出所有测试文件
    print("\n测试文件列表:")
    for i, f in enumerate(TEST_FILES):
        exists = "[OK]" if f.exists() else "[NOT FOUND]"
        print(f"  {i}. {exists} {f.name}")
    
    # 运行测试
    if args.index is not None:
        if 0 <= args.index < len(TEST_FILES):
            test_file(TEST_FILES[args.index], args.verbose, args.parser)
        else:
            print(f"索引 {args.index} 超出范围")
    else:
        for f in TEST_FILES:
            test_file(f, args.verbose, args.parser)
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
