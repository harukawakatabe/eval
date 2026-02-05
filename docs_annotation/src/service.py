"""文档标注服务 - 统一入口。"""

from pathlib import Path
from typing import Any, Dict, Optional

from core.pipeline import Pipeline
from core.schema import DocumentAnnotation
from processors.doc_parser import DocParser
from processors.element_detector import ElementDetector
from processors.feature_extractor import FeatureExtractor
from processors.layout_classifier import LayoutClassifier
from models.ocr import OCRModel
from models.llm import LLMModel


class AnnotationService:
    """
    文档标注服务 - 统一服务入口。

    负责构建处理流程并执行文档标注。

    使用示例：
        service = AnnotationService(
            ocr_model=PaddleOCRModel(),
            llm_model=OpenAILLM(api_key="...")
        )
        annotation = service.annotate("document.pdf")
    """

    def __init__(
        self,
        ocr_model: Optional[OCRModel] = None,
        llm_model: Optional[LLMModel] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化标注服务。

        Args:
            ocr_model: OCR模型实例（用于元素检测）
            llm_model: LLM模型实例（用于特征提取和布局分类）
            config: 全局配置字典
        """
        self.ocr_model = ocr_model
        self.llm_model = llm_model
        self.config = config or {}

    def annotate(self, file_path: str) -> DocumentAnnotation:
        """
        标注文档。

        Args:
            file_path: 文档文件路径

        Returns:
            DocumentAnnotation: 标注结果
        """
        # 1. 构建Pipeline
        pipeline = self._build_pipeline()

        # 2. 执行
        result = pipeline.execute(file_path)

        # 3. 返回结果
        if not result.success:
            raise ValueError(f"Annotation failed: {result.errors}")

        return result.data

    def annotate_batch(self, file_paths: list[str]) -> list[DocumentAnnotation]:
        """
        批量标注文档。

        Args:
            file_paths: 文档文件路径列表

        Returns:
            标注结果列表
        """
        pipeline = self._build_pipeline()
        results = pipeline.execute_batch(file_paths)

        annotations = []
        for result in results:
            if result.success:
                annotations.append(result.data)
            else:
                # 失败的文档记录错误
                print(f"Error: {result.errors}")

        return annotations

    def _build_pipeline(self) -> Pipeline:
        """
        构建处理Pipeline。

        流程：DocParser → ElementDetector → FeatureExtractor → LayoutClassifier
        """
        return Pipeline() \
            .add(DocParser(self.config.get("doc_parser", {}))) \
            .add(ElementDetector({
                **self.config.get("element_detector", {}),
                "ocr_model": self.ocr_model,
            })) \
            .add(FeatureExtractor({
                **self.config.get("feature_extractor", {}),
                "llm_model": self.llm_model,
            })) \
            .add(LayoutClassifier({
                **self.config.get("layout_classifier", {}),
                "llm_model": self.llm_model,
            }))

    @staticmethod
    def save_annotation(
        annotation: DocumentAnnotation,
        output_path: str,
        format: str = "json"
    ) -> None:
        """
        保存标注结果到文件。

        Args:
            annotation: 标注结果
            output_path: 输出文件路径
            format: 输出格式（json/yaml）
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(output, "w", encoding="utf-8") as f:
                f.write(annotation.to_json())
        elif format == "yaml":
            import yaml
            with open(output, "w", encoding="utf-8") as f:
                yaml.dump(annotation.to_dict(), f, allow_unicode=True)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """
        加载配置文件。

        Args:
            config_path: 配置文件路径（YAML格式）

        Returns:
            配置字典
        """
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
