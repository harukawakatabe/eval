#!/usr/bin/env python3
"""
文档标注分析工具 - 命令行入口

分析 docs_annotation 输出的标注结果，为 query 抽取提供数据支撑。

用法:
    uv run python analysis/analyze.py
    uv run python analysis/analyze.py --input docs_annotation/output --output analysis/reports
    uv run python analysis/analyze.py --folder 城市运营
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from analysis.analyzer import AnnotationAnalyzer


def main():
    parser = argparse.ArgumentParser(
        description="分析文档标注结果，为 query 抽取提供数据支撑",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析默认目录
  uv run python analysis/analyze.py

  # 指定输入和输出目录
  uv run python analysis/analyze.py --input docs_annotation/output --output analysis/reports

  # 仅分析某个文件夹
  uv run python analysis/analyze.py --folder 城市运营

  # 调整阈值
  uv run python analysis/analyze.py --sparse-threshold 5 --complexity-threshold 4
        """,
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="docs_annotation/output",
        help="标注输出目录路径 (默认: docs_annotation/output)",
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="analysis/reports",
        help="分析报告输出目录 (默认: analysis/reports)",
    )
    
    parser.add_argument(
        "--folder", "-f",
        type=str,
        default=None,
        help="仅分析指定的子文件夹",
    )
    
    parser.add_argument(
        "--sparse-threshold",
        type=int,
        default=3,
        help="稀疏桶阈值，文件数 < N 视为稀疏 (默认: 3)",
    )
    
    parser.add_argument(
        "--complexity-threshold",
        type=int,
        default=3,
        help="高复杂度阈值，压力点 >= N 视为高复杂度 (默认: 3)",
    )
    
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="仅输出 JSON 格式",
    )
    
    parser.add_argument(
        "--csv-only",
        action="store_true",
        help="仅输出 CSV 格式",
    )
    
    parser.add_argument(
        "--md-only",
        action="store_true",
        help="仅输出 Markdown 格式",
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="安静模式，减少输出",
    )
    
    args = parser.parse_args()
    
    # 处理路径
    input_path = Path(args.input)
    if args.folder:
        input_path = input_path / args.folder
    
    output_path = Path(args.output)
    if args.folder:
        output_path = output_path / args.folder
    
    # 检查输入目录
    if not input_path.exists():
        print(f"错误: 输入目录不存在: {input_path}")
        print("\n请先运行 batch_annotate.py 生成标注结果:")
        print("  uv run python docs_annotation/batch_annotate.py --input <文档目录>")
        sys.exit(1)
    
    # 检查是否有 JSON 文件
    json_files = list(input_path.rglob("*.json"))
    if not json_files:
        print(f"错误: 目录中没有 JSON 文件: {input_path}")
        sys.exit(1)
    
    if not args.quiet:
        print("=" * 60)
        print("文档标注分析工具")
        print("=" * 60)
        print(f"输入目录: {input_path}")
        print(f"输出目录: {output_path}")
        print(f"发现 {len(json_files)} 个 JSON 文件")
        print(f"稀疏桶阈值: {args.sparse_threshold}")
        print(f"高复杂度阈值: {args.complexity_threshold}")
        print("-" * 60)
    
    try:
        # 创建分析器
        analyzer = AnnotationAnalyzer(
            input_dir=str(input_path),
            sparse_threshold=args.sparse_threshold,
            complexity_threshold=args.complexity_threshold,
        )
        
        # 输出报告
        if args.json_only:
            analyzer.export_to_json(str(output_path))
            if not args.quiet:
                print("[OK] JSON 报告已生成")
        elif args.csv_only:
            analyzer.export_to_csv(str(output_path))
            if not args.quiet:
                print("[OK] CSV 报告已生成")
        elif args.md_only:
            analyzer.export_to_markdown(str(output_path))
            if not args.quiet:
                print("[OK] Markdown 报告已生成")
        else:
            analyzer.export_all(str(output_path))
        
        if not args.quiet:
            print("-" * 60)
            print("生成的报告文件:")
            for f in sorted(output_path.iterdir()):
                print(f"  - {f.name}")
            print("=" * 60)
        
        # 打印简要摘要
        if not args.quiet:
            full_analysis = analyzer.run_full_analysis()
            basic = full_analysis["basic_stats"]
            advice = full_analysis["sampling_advice"]
            
            print("\n[快速摘要]")
            print(f"  文件总数: {basic['total_files']}")
            print(f"  文件类型: {', '.join(f'{k}({v})' for k, v in basic.get('file_types', {}).items())}")
            print(f"  高复杂度文档: {advice.get('priority_docs_count', 0)} 个")
            print(f"  建议 per_file_type: {advice.get('recommended_per_file_type', 'N/A')}")
            
            gaps = full_analysis["gaps"]
            if gaps.get("sparse_buckets") or gaps.get("missing_features"):
                print("\n[警告] 发现覆盖缺口，详见 REPORT.md")
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
