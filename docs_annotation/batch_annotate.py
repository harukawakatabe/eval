"""批量文档标注脚本。

用于批量处理 reference/data/Files 目录下的文档，
自动过滤不支持的格式和失败文件，保存标注结果。

使用示例：
    python batch_annotate.py
    python batch_annotate.py --input ../reference/data/Files --output ./output
    python batch_annotate.py --use-mock  # 使用Mock模型测试
"""

import sys
import os
import io

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

import json
import argparse
from pathlib import Path
from typing import List, Set, Dict, Any
from datetime import datetime

from src.service import AnnotationService
from src.models.ocr import PaddleOCRModel, MockOCR
from src.models.llm import OpenAILLM, MockLLM


# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}


class BatchAnnotator:
    """批量标注处理器。"""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        use_mock: bool = False,
        skip_existing: bool = True,
    ):
        """
        初始化批量标注器。

        Args:
            input_dir: 输入文档目录
            output_dir: 输出结果目录
            use_mock: 是否使用Mock模型（用于测试）
            skip_existing: 是否跳过已标注的文件
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.skip_existing = skip_existing

        # 初始化服务
        if use_mock:
            print("使用 Mock 模型进行测试...")
            self.service = AnnotationService(
                ocr_model=MockOCR(),
                llm_model=MockLLM(),
            )
        else:
            # 使用真实模型
            openai_api_key = os.getenv("OPENAI_API_KEY")
            openai_base_url = os.getenv("OPENAI_BASE_URL")
            openai_model = os.getenv("OPENAI_MODEL_STANDARD", "gpt-4")
            
            if not openai_api_key:
                print("警告: 未设置 OPENAI_API_KEY，将使用 Mock LLM")
                print("请在 .env 文件中配置或设置环境变量")
                llm_model = MockLLM()
            else:
                llm_kwargs = {
                    "api_key": openai_api_key,
                    "model": openai_model,
                }
                if openai_base_url:
                    llm_kwargs["base_url"] = openai_base_url
                    print(f"使用自定义 OpenAI Base URL: {openai_base_url}")
                
                llm_model = OpenAILLM(**llm_kwargs)
                print(f"使用 OpenAI 模型: {openai_model}")

            try:
                ocr_model = PaddleOCRModel(lang="ch")
                print("使用 PaddleOCR + OpenAI 进行标注...")
            except ImportError:
                print("警告: PaddleOCR 未安装，将使用 Mock OCR")
                ocr_model = MockOCR()

            self.service = AnnotationService(
                ocr_model=ocr_model,
                llm_model=llm_model,
            )

        # 统计信息
        self.stats = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "success": 0,
        }
        self.failed_files: List[Dict[str, str]] = []

    def load_failed_files(self) -> Set[str]:
        """
        加载所有 parsing_failed_files.json 中的文件名。

        Returns:
            失败文件名集合
        """
        failed_files = set()

        for json_file in self.input_dir.rglob("parsing_failed_files.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    failed_files.update(data.get("parsing_failed_files", []))
            except Exception as e:
                print(f"警告: 读取失败文件列表时出错 {json_file}: {e}")

        return failed_files

    def should_process(self, file_path: Path, failed_files: Set[str]) -> bool:
        """
        判断文件是否应该被处理。

        Args:
            file_path: 文件路径
            failed_files: 失败文件名集合

        Returns:
            是否应该处理
        """
        # 检查文件名是否在失败列表中
        if file_path.name in failed_files:
            return False

        # 检查扩展名
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return False

        # 检查是否已经标注（如果启用跳过）
        if self.skip_existing:
            output_file = self.get_output_path(file_path)
            if output_file.exists():
                return False

        return True

    def get_output_path(self, input_file: Path) -> Path:
        """
        获取输出文件路径（保持原有目录结构）。

        Args:
            input_file: 输入文件路径

        Returns:
            输出文件路径
        """
        # 计算相对路径
        relative_path = input_file.relative_to(self.input_dir)

        # 修改扩展名为 .json
        output_path = self.output_dir / relative_path.with_suffix(".json")

        return output_path

    def collect_files(self) -> List[Path]:
        """
        收集需要处理的文件。

        Returns:
            文件路径列表
        """
        print(f"\n扫描目录: {self.input_dir}")

        failed_files = self.load_failed_files()
        if failed_files:
            print(f"已加载 {len(failed_files)} 个失败文件（将被跳过）")

        files_to_process = []

        for file_path in self.input_dir.rglob("*"):
            if not file_path.is_file():
                continue

            self.stats["total_files"] += 1

            if self.should_process(file_path, failed_files):
                files_to_process.append(file_path)

        print(f"\n找到 {self.stats['total_files']} 个文件")
        print(f"需要处理 {len(files_to_process)} 个文件")

        return files_to_process

    def process_file(self, file_path: Path) -> bool:
        """
        处理单个文件。

        Args:
            file_path: 文件路径

        Returns:
            是否成功
        """
        try:
            # 标注文档
            annotation = self.service.annotate(str(file_path))

            # 保存结果
            output_path = self.get_output_path(file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.service.save_annotation(annotation, str(output_path))

            self.stats["success"] += 1
            return True

        except Exception as e:
            self.stats["failed"] += 1
            self.failed_files.append({
                "file": str(file_path),
                "error": str(e),
            })
            print(f"  ✗ 失败: {e}")
            return False

    def run(self, verbose: bool = False):
        """
        执行批量标注。

        Args:
            verbose: 是否显示每个文件的处理详情（默认 False，只显示进度）
        """
        start_time = datetime.now()

        print("=" * 60)
        print("文档批量标注系统")
        print("=" * 60)

        # 收集文件
        files = self.collect_files()

        if not files:
            print("\n没有需要处理的文件。")
            return

        # 处理文件
        total = len(files)
        print(f"\n开始处理 {total} 个文件...")

        for i, file_path in enumerate(files, 1):
            self.process_file(file_path)
            self.stats["processed"] += 1

            # 进度显示
            if verbose:
                # 详细模式：每个文件一行
                relative_path = file_path.relative_to(self.input_dir)
                status = "✓" if self.stats["success"] == i - self.stats["failed"] else "✗"
                print(f"[{i}/{total}] {status} {relative_path}")
            else:
                # 简洁模式：同一行更新进度
                progress = i / total * 100
                bar_len = 30
                filled = int(bar_len * i / total)
                bar = "█" * filled + "░" * (bar_len - filled)
                print(f"\r进度: {bar} {progress:5.1f}% ({i}/{total})", end="", flush=True)

        # 换行（简洁模式下进度条结束）
        if not verbose:
            print()

        # 保存失败文件报告
        if self.failed_files:
            report_path = self.output_dir / "failed_files.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(self.failed_files, f, indent=2, ensure_ascii=False)

        # 打印统计
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("处理完成！")
        print("=" * 60)
        print(f"总文件数:       {self.stats['total_files']}")
        print(f"已处理:         {self.stats['processed']}")
        print(f"成功:           {self.stats['success']}")
        print(f"失败:           {self.stats['failed']}")
        print(f"耗时:           {duration:.2f} 秒")
        print(f"输出目录:       {self.output_dir}")

        if self.failed_files:
            print(f"\n失败文件报告:   {self.output_dir / 'failed_files.json'}")


def main():
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="批量标注文档",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--input",
        type=str,
        default="../reference/data/Files",
        help="输入文档目录（默认: ../reference/data/Files）",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="./output",
        help="输出结果目录（默认: ./output）",
    )

    parser.add_argument(
        "--use-mock",
        action="store_true",
        help="使用Mock模型（用于测试流程）",
    )

    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="不跳过已标注的文件（重新处理所有文件）",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示每个文件的处理详情（默认只显示进度条）",
    )

    args = parser.parse_args()

    # 转换为绝对路径
    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    # 检查输入目录
    if not input_dir.exists():
        print(f"错误: 输入目录不存在: {input_dir}")
        sys.exit(1)

    # 创建批量标注器并运行
    annotator = BatchAnnotator(
        input_dir=input_dir,
        output_dir=output_dir,
        use_mock=args.use_mock,
        skip_existing=not args.no_skip_existing,
    )

    annotator.run(verbose=args.verbose)


if __name__ == "__main__":
    main()
