"""文档标注系统基础类。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ProcessResult:
    """
    统一格式的处理结果。

    Attributes:
        success: 处理是否成功
        data: 处理后的数据
        errors: 错误消息列表
        metadata: 处理过程的额外元数据
    """

    success: bool
    data: Any = None
    errors: list[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def add_error(self, error: str) -> None:
        """添加错误消息。"""
        self.errors.append(error)
        self.success = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class BaseProcessor(ABC):
    """
    处理器基类。

    所有处理器都应继承此类，实现独立的处理任务，
    并返回ProcessResult格式的结果。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化处理器。

        Args:
            config: 可选的配置字典
        """
        self.config = config or {}

    @abstractmethod
    def process(self, input_data: Any) -> ProcessResult:
        """
        处理输入数据。

        Args:
            input_data: 要处理的输入数据

        Returns:
            包含处理后数据的ProcessResult
        """
        pass

    def get_config(self) -> Dict[str, Any]:
        """获取处理器配置。"""
        return self.config.copy()

    def update_config(self, **kwargs) -> None:
        """更新处理器配置。"""
        self.config.update(kwargs)
