#!/usr/bin/env python3
"""
导出文件级别的标注数据到 CSV

将 docs_annotation/output 下的每个 JSON 文件的标注信息导出为一行 CSV。

用法:
    uv run python analysis/export_files.py
    uv run python analysis/export_files.py --input docs_annotation/output --output analysis/reports/files.csv
"""

import argparse
import csv
import json
import sys
from pathlib import Path


def get_nested_value(data: dict, key: str):
    """获取嵌套字典中的值，支持点号分隔的路径"""
    keys = key.split(".")
    value = data
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return None
    return value


def main():
    parser = argparse.ArgumentParser(description="导出文件级别的标注数据到 CSV")
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="docs_annotation/output",
        help="标注输出目录 (默认: docs_annotation/output)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="analysis/reports/files.csv",
        help="输出 CSV 文件路径 (默认: analysis/reports/files.csv)",
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"错误: 输入目录不存在: {input_path}")
        sys.exit(1)
    
    # 收集所有 JSON 文件
    json_files = list(input_path.rglob("*.json"))
    if not json_files:
        print(f"错误: 目录中没有 JSON 文件: {input_path}")
        sys.exit(1)
    
    print(f"找到 {len(json_files)} 个 JSON 文件")
    
    # CSV 列定义
    columns = [
        "folder",
        "doc_id",
        "file_type",
        "file_path",
        "layout",
        "has_image",
        "has_table",
        "has_formula",
        "has_chart",
        "image_text_mixed",
        "reading_order_sensitive",
        "table_profile.long_table",
        "table_profile.cross_page_table",
        "table_profile.table_dominant",
        "chart_profile.cross_page_chart",
    ]
    
    # 收集数据
    rows = []
    for json_file in sorted(json_files):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            profile = data.get("doc_profile") or data.get("pdf_profile") or {}
            
            row = {
                "folder": json_file.parent.name if json_file.parent != input_path else "_root",
                "doc_id": data.get("doc_id", ""),
                "file_type": data.get("file_type", ""),
                "file_path": data.get("file_path", ""),
            }
            
            # 提取 profile 中的字段
            for col in columns[4:]:  # 跳过前4个基础字段
                value = get_nested_value(profile, col)
                row[col] = value if value is not None else ""
            
            rows.append(row)
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"警告: 无法加载 {json_file}: {e}")
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 写入 CSV
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"已导出 {len(rows)} 条记录到: {output_path}")


if __name__ == "__main__":
    main()
