#!/usr/bin/env python
"""运行所有测试的入口脚本。

使用方法：
    python -m test.run_all_tests [test_data_dir]
    
示例：
    python -m test.run_all_tests "reference/data/Files/业务交付管理"
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any

# 添加正确的路径
script_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(script_dir))

from service import AnnotationService
from processors.doc_parser import ParserBackend
from models.ocr import MockOCR
from models.llm import MockLLM


# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'}


def run_tests(test_dir: str, verbose: bool = False):
    """运行测试目录下的所有文件。"""
    dir_path = Path(test_dir)
    
    if not dir_path.exists():
        print(f"[ERROR] 目录不存在: {test_dir}")
        return
    
    files = list(dir_path.rglob("*"))
    supported_files = [f for f in files if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    
    print(f"{'='*70}")
    print(f"测试目录: {test_dir}")
    print(f"找到 {len(supported_files)} 个支持的文件")
    print(f"{'='*70}")
    
    log_level = logging.DEBUG if verbose else logging.WARNING
    
    service = AnnotationService(
        ocr_model=MockOCR(),
        llm_model=MockLLM(),
        parser_backend=ParserBackend.LEGACY,
        log_level=log_level
    )
    
    results: List[Dict[str, Any]] = []
    success_count = 0
    fail_count = 0
    
    for i, file_path in enumerate(supported_files, 1):
        rel_path = file_path.relative_to(dir_path)
        print(f"\n[{i}/{len(supported_files)}] {rel_path}")
        
        try:
            ann = service.annotate(str(file_path))
            success_count += 1
            
            result = {
                "file": str(rel_path),
                "success": True,
                "file_type": ann.file_type.value,
                "has_table": ann.doc_profile.has_table if ann.doc_profile else None,
                "has_image": ann.doc_profile.has_image if ann.doc_profile else None,
                "has_chart": ann.doc_profile.has_chart if ann.doc_profile else None,
                "table_dominant": None,
                "cross_page_table": None,
                "long_table": None,
            }
            
            if ann.doc_profile and ann.doc_profile.table_profile:
                tp = ann.doc_profile.table_profile
                result["table_dominant"] = tp.table_dominant
                result["cross_page_table"] = tp.cross_page_table
                result["long_table"] = tp.long_table
            
            results.append(result)
            
            # 打印简要结果
            flags = []
            if result["has_table"]:
                flags.append("表格")
            if result["has_image"]:
                flags.append("图片")
            if result["has_chart"]:
                flags.append("图表")
            if result["table_dominant"]:
                flags.append("表格主导")
            if result["cross_page_table"]:
                flags.append("跨页表格")
            if result["long_table"]:
                flags.append("长表格")
            
            print(f"  [OK] {', '.join(flags) if flags else '无特殊元素'}")
            
        except Exception as e:
            fail_count += 1
            results.append({
                "file": str(rel_path),
                "success": False,
                "error": str(e)
            })
            print(f"  [FAIL] 错误: {e}")
    
    # 打印统计
    print(f"\n{'='*70}")
    print("测试统计")
    print(f"{'='*70}")
    print(f"总文件数: {len(supported_files)}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    
    # 统计特征分布
    if results:
        table_count = sum(1 for r in results if r.get("has_table"))
        image_count = sum(1 for r in results if r.get("has_image"))
        chart_count = sum(1 for r in results if r.get("has_chart"))
        table_dominant_count = sum(1 for r in results if r.get("table_dominant"))
        cross_page_count = sum(1 for r in results if r.get("cross_page_table"))
        long_table_count = sum(1 for r in results if r.get("long_table"))
        
        print(f"\n特征分布:")
        print(f"  含表格: {table_count}")
        print(f"  含图片: {image_count}")
        print(f"  含图表: {chart_count}")
        print(f"  表格主导: {table_dominant_count}")
        print(f"  跨页表格: {cross_page_count}")
        print(f"  长表格: {long_table_count}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="运行所有测试")
    parser.add_argument(
        "test_dir",
        nargs="?",
        default="reference/data/Files",
        help="测试数据目录 (默认: reference/data/Files)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细日志"
    )
    
    args = parser.parse_args()
    run_tests(args.test_dir, args.verbose)


if __name__ == "__main__":
    main()
