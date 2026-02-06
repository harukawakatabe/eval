#!/usr/bin/env python
"""测试表格检测功能，特别是表格与图片的区分。

测试目标：
1. PDF 中表格不应被误识别为图片
2. table_dominant 判断逻辑
3. 表格页数比例计算

使用方法：
    python -m test.test_table_detection [file_path]
    
示例：
    python -m test.test_table_detection "reference/data/Files/业务交付管理/2-联想百应服务商收费标准.pdf"
    python -m test.test_table_detection "reference/data/Files/业务交付管理/5-联想百应《优选服务商红黄线管理规则》2025年第四版1001.pdf"
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
    """测试单个文件的表格检测。"""
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
            print("\n--- 元素检测分析 ---")
            print(f"  has_table: {dp.has_table}")
            print(f"  has_image: {dp.has_image}")
            print(f"  has_chart: {dp.has_chart}")
            
            if dp.table_profile:
                tp = dp.table_profile
                print("\n--- 表格特征分析 ---")
                print(f"  table_dominant: {tp.table_dominant}")
                print(f"  cross_page_table: {tp.cross_page_table}")
                print(f"  long_table: {tp.long_table}")
                
                # 验证 table_dominant 逻辑
                if tp.table_dominant:
                    print("  ✅ table_dominant=True")
                else:
                    print("  ⚠️ table_dominant=False，请检查是否正确")
        
        return ann
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_parsers(file_path: str):
    """对比不同解析器的结果。"""
    print(f"\n{'='*70}")
    print(f"对比测试: {file_path}")
    print(f"{'='*70}")
    
    results = {}
    
    for backend in [ParserBackend.LEGACY]:  # 如果安装了 Docling，可以添加 ParserBackend.DOCLING
        print(f"\n>>> 使用 {backend.value} 解析器")
        service = AnnotationService(
            ocr_model=MockOCR(),
            llm_model=MockLLM(),
            parser_backend=backend,
            log_level=logging.WARNING  # 减少日志噪音
        )
        
        try:
            ann = service.annotate(file_path)
            results[backend.value] = {
                "has_table": ann.doc_profile.has_table if ann.doc_profile else None,
                "has_image": ann.doc_profile.has_image if ann.doc_profile else None,
                "table_dominant": ann.doc_profile.table_profile.table_dominant if ann.doc_profile and ann.doc_profile.table_profile else None,
            }
        except Exception as e:
            results[backend.value] = {"error": str(e)}
    
    # 打印对比结果
    print("\n--- 对比结果 ---")
    for parser, result in results.items():
        print(f"\n{parser}:")
        for k, v in result.items():
            print(f"  {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="测试表格检测功能")
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
    parser.add_argument(
        "--compare",
        action="store_true",
        help="对比不同解析器的结果"
    )
    
    args = parser.parse_args()
    
    parser_map = {
        "auto": ParserBackend.AUTO,
        "docling": ParserBackend.DOCLING,
        "legacy": ParserBackend.LEGACY,
    }
    
    if args.file_path:
        if args.compare:
            compare_parsers(args.file_path)
        else:
            test_file(args.file_path, parser_map[args.parser])
    else:
        print("请提供文件路径")
        print("用法: python -m test.test_table_detection <file_path>")
        print("      python -m test.test_table_detection <file_path> --compare")


if __name__ == "__main__":
    main()
