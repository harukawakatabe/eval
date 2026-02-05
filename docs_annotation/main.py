"""文档标注系统 - 使用示例。"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from service import AnnotationService
from models.ocr import PaddleOCRModel, MockOCR, TesseractOCRModel
from models.llm import OpenAILLM, ClaudeLLM, MockLLM


def main():
    """主函数 - 演示文档标注系统的使用。"""

    # ==================== 示例1: 使用Mock模型（无需API） ====================
    print("=" * 60)
    print("示例1: 使用Mock模型进行文档解析")
    print("=" * 60)

    service1 = AnnotationService(
        ocr_model=MockOCR(),
        llm_model=MockLLM(),
    )

    # 示例：解析PDF文件（需要提供实际文件路径）
    # annotation1 = service1.annotate("path/to/document.pdf")
    # print(f"\n标注结果:\n{annotation1.to_json()}")

    print("\n使用Mock模型可以快速测试文档解析功能，无需配置API。")
    print("Mock模型返回空检测结果，适合测试流程。")

    # ==================== 示例2: 使用PaddleOCR + OpenAI ====================
    print("\n" + "=" * 60)
    print("示例2: 使用PaddleOCR + OpenAI进行完整标注")
    print("=" * 60)

    # 检查API密钥
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if openai_api_key:
        service2 = AnnotationService(
            ocr_model=PaddleOCRModel(lang="ch"),
            llm_model=OpenAILLM(api_key=openai_api_key, model="gpt-4"),
        )

        print("服务初始化成功，使用PaddleOCR + OpenAI GPT-4")
        # annotation2 = service2.annotate("path/to/document.pdf")
        # service2.save_annotation(annotation2, "output/document_annotation.json")
    else:
        print("未设置OPENAI_API_KEY环境变量，跳过此示例。")

    # ==================== 示例3: 使用Tesseract + Claude ====================
    print("\n" + "=" * 60)
    print("示例3: 使用Tesseract + Claude进行完整标注")
    print("=" * 60)

    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_api_key:
        service3 = AnnotationService(
            ocr_model=TesseractOCRModel(lang="chi_sim+eng"),
            llm_model=ClaudeLLM(api_key=anthropic_api_key),
        )

        print("服务初始化成功，使用Tesseract + Claude")
    else:
        print("未设置ANTHROPIC_API_KEY环境变量，跳过此示例。")

    # ==================== 示例4: 使用配置文件 ====================
    print("\n" + "=" * 60)
    print("示例4: 使用配置文件初始化服务")
    print("=" * 60)

    config_path = Path(__file__).parent / "config" / "processors.yaml"
    if config_path.exists():
        config = AnnotationService.load_config(str(config_path))
        print(f"配置文件加载成功: {config_path}")

        # 从配置获取模型设置
        ocr_config = config.get("models", {}).get("ocr", {})
        llm_config = config.get("models", {}).get("llm", {})

        print(f"OCR模型类型: {ocr_config.get('type', 'not specified')}")
        print(f"LLM模型类型: {llm_config.get('type', 'not specified')}")
    else:
        print(f"配置文件不存在: {config_path}")

    # ==================== 示例5: 批量处理 ====================
    print("\n" + "=" * 60)
    print("示例5: 批量处理多个文档")
    print("=" * 60)

    service5 = AnnotationService(
        ocr_model=MockOCR(),
        llm_model=MockLLM(),
    )

    # 批量处理（需要提供实际文件路径）
    # files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    # annotations = service5.annotate_batch(files)
    # for i, ann in enumerate(annotations):
    #     service5.save_annotation(ann, f"output/doc{i+1}_annotation.json")

    print("批量处理功能示例（需要提供实际文件路径）。")

    # ==================== 使用说明 ====================
    print("\n" + "=" * 60)
    print("使用说明")
    print("=" * 60)
    print("""
1. 安装依赖:
   pip install -r requirements.txt

2. 配置API密钥（可选）:
   export OPENAI_API_KEY="your-key-here"
   export ANTHROPIC_API_KEY="your-key-here"

3. 运行标注:
   from service import AnnotationService
   from models.ocr import PaddleOCRModel
   from models.llm import OpenAILLM

   service = AnnotationService(
       ocr_model=PaddleOCRModel(),
       llm_model=OpenAILLM(api_key="your-api-key")
   )
   annotation = service.annotate("path/to/document.pdf")
   print(annotation.to_json())

4. 保存结果:
   service.save_annotation(annotation, "output/result.json")

5. 支持的文档格式:
   - PDF: .pdf
   - Word: .doc, .docx
   - Excel: .xls, .xlsx
   - PowerPoint: .ppt, .pptx
   - HTML: .html, .htm
   - Text/Markdown: .txt, .md
    """)


if __name__ == "__main__":
    main()
