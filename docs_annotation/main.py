"""文档标注系统 - 使用示例。"""

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

import os

from docs_annotation.src.service import AnnotationService
from docs_annotation.src.models.ocr import PaddleOCRModel
from docs_annotation.src.models.llm import OpenAILLM


def main():
    """主函数 - 演示文档标注系统的使用。"""

    openai_api_key = os.environ.get("OPENAI_API_KEY")

    print("=" * 60)
    print("使用 PaddleOCR + OpenAI 进行完整标注")
    print("=" * 60)

    if openai_api_key:
        service = AnnotationService(
            ocr_model=PaddleOCRModel(lang="ch"),
            llm_model=OpenAILLM(api_key=openai_api_key, model="gpt-4"),
        )
        print("服务初始化成功")
        # annotation = service.annotate("path/to/document.pdf")
        # service.save_annotation(annotation, "output/document_annotation.json")
    else:
        print("未设置 OPENAI_API_KEY 环境变量，跳过。")


if __name__ == "__main__":
    main()
