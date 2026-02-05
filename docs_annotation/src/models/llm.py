"""LLM模型接口 - 用于分类和信息提取。"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMModel(ABC):
    """
    LLM模型接口 - 用于分类和提取任务。

    实现可以封装不同的LLM提供商，如：
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - 本地模型 (GLM, Qwen等)
    """

    @abstractmethod
    def classify(
        self, prompt: str, options: List[str]
    ) -> Dict[str, Any]:
        """
        执行分类任务。

        Args:
            prompt: 带上下文的分类提示词
            options: 可选类别列表

        Returns:
            包含分类结果的字典：
            {
                "label": "selected_label",
                "confidence": 0.85,
                "reasoning": "explanation (optional)"
            }
        """
        pass

    @abstractmethod
    def extract(self, prompt: str, schema: Dict[str, str]) -> Dict[str, Any]:
        """
        执行信息提取。

        Args:
            prompt: 带上下文的提取提示词
            schema: 定义预期字段和类型的字典：
                    {"field_name": "type_description"}

        Returns:
            符合schema的提取值字典
        """
        pass


class MockLLM(LLMModel):
    """
    Mock LLM实现 - 用于测试。

    所有操作返回默认值。
    """

    def classify(self, prompt: str, options: List[str]) -> Dict[str, Any]:
        """返回第一个选项，高置信度。"""
        return {
            "label": options[0] if options else "unknown",
            "confidence": 1.0,
            "reasoning": "Mock分类",
        }

    def extract(self, prompt: str, schema: Dict[str, str]) -> Dict[str, Any]:
        """根据schema类型返回默认值。"""
        result = {}
        for field_name, field_type in schema.items():
            if "bool" in field_type.lower():
                result[field_name] = False
            elif "int" in field_type.lower() or "float" in field_type.lower():
                result[field_name] = 0
            elif "str" in field_type.lower() or "string" in field_type.lower():
                result[field_name] = ""
            else:
                result[field_name] = None
        return result


class OpenAILLM(LLMModel):
    """
    OpenAI GPT实现。

    需要: pip install openai
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        base_url: Optional[str] = None,
    ):
        """
        初始化OpenAI LLM。

        Args:
            api_key: OpenAI API密钥
            model: 模型名称（默认: gpt-4）
            base_url: 可选的自定义base URL
        """
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        except ImportError:
            raise ImportError(
                "OpenAI包未安装。"
                "请使用: pip install openai"
            )

        self.model = model

    def _call(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """调用OpenAI API。"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content or ""

    def classify(self, prompt: str, options: List[str]) -> Dict[str, Any]:
        """
        使用OpenAI进行分类。

        使用function calling实现可靠分类。
        """
        options_str = ", ".join(options)

        messages = [
            {
                "role": "system",
                "content": f"You are a classifier. Choose from these options: {options_str}",
            },
            {"role": "user", "content": prompt},
        ]

        # 尝试使用function calling
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=[
                    {
                        "name": "classify",
                        "description": "Classify the input",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "label": {
                                    "type": "string",
                                    "enum": options,
                                },
                                "confidence": {"type": "number"},
                                "reasoning": {"type": "string"},
                            },
                            "required": ["label"],
                        },
                    }
                ],
                function_call={"name": "classify"},
            )

            import json
            return json.loads(response.choices[0].message.function_call.arguments)

        except Exception:
            # 回退到基于文本的分类
            response_text = self._call(messages)
            for option in options:
                if option.lower() in response_text.lower():
                    return {"label": option, "confidence": 0.8, "reasoning": response_text[:100]}

            return {
                "label": options[0] if options else "unknown",
                "confidence": 0.5,
                "reasoning": response_text[:100],
            }

    def extract(self, prompt: str, schema: Dict[str, str]) -> Dict[str, Any]:
        """
        使用OpenAI提取结构化信息。

        使用function calling实现可靠提取。
        """
        # 构建function calling的JSON schema
        properties = {}
        for field_name, field_type in schema.items():
            if "bool" in field_type.lower():
                properties[field_name] = {"type": "boolean"}
            elif "int" in field_type.lower():
                properties[field_name] = {"type": "integer"}
            elif "float" in field_type.lower() or "num" in field_type.lower():
                properties[field_name] = {"type": "number"}
            else:
                properties[field_name] = {"type": "string"}

        messages = [
            {
                "role": "system",
                "content": "Extract structured information from the given text.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=[
                    {
                        "name": "extract",
                        "description": "Extract information",
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": list(schema.keys()),
                        },
                    }
                ],
                function_call={"name": "extract"},
            )

            import json
            return json.loads(response.choices[0].message.function_call.arguments)

        except Exception:
            # 回退: 返回空schema
            return {k: None for k in schema.keys()}


class ClaudeLLM(LLMModel):
    """
    Anthropic Claude实现。

    需要: pip install anthropic
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
    ):
        """
        初始化Claude LLM。

        Args:
            api_key: Anthropic API密钥
            model: 模型名称（默认: claude-3-5-sonnet-20241022）
        """
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError(
                "Anthropic包未安装。"
                "请使用: pip install anthropic"
            )

        self.model = model

    def _call(self, prompt: str, max_tokens: int = 1024) -> str:
        """调用Claude API。"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def classify(self, prompt: str, options: List[str]) -> Dict[str, Any]:
        """
        使用Claude进行分类。

        使用提示工程进行分类。
        """
        options_str = ", ".join(options)

        full_prompt = f"""Classify the following document description.

Options: {options_str}

Respond in JSON format:
{{"label": "your_choice", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}

Document:
{prompt}
"""

        response = self._call(full_prompt)

        # 从响应中解析JSON
        import json
        try:
            result = json.loads(response)
            return {
                "label": result.get("label", options[0] if options else "unknown"),
                "confidence": result.get("confidence", 0.8),
                "reasoning": result.get("reasoning", ""),
            }
        except json.JSONDecodeError:
            # 回退: 在响应中搜索选项
            for option in options:
                if option.lower() in response.lower():
                    return {"label": option, "confidence": 0.7, "reasoning": response[:100]}

            return {"label": options[0] if options else "unknown", "confidence": 0.5, "reasoning": response[:100]}

    def extract(self, prompt: str, schema: Dict[str, str]) -> Dict[str, Any]:
        """
        使用Claude提取结构化信息。

        使用提示工程进行提取。
        """
        schema_str = "\n".join(f"- {k}: {v}" for k, v in schema.items())

        full_prompt = f"""Extract structured information from the following document.

Output schema:
{schema_str}

Respond in JSON format with exactly these fields.

Document:
{prompt}
"""

        response = self._call(full_prompt)

        # 从响应中解析JSON
        import json
        try:
            result = json.loads(response)
            # 确保所有schema键都存在
            for key in schema.keys():
                if key not in result:
                    result[key] = None
            return result
        except json.JSONDecodeError:
            return {k: None for k in schema.keys()}
