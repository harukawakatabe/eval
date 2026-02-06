"""处理管道 - 顺序连接多个处理器。"""

from typing import Any, List, Optional
from .base import BaseProcessor, ProcessResult


class Pipeline:
    """
    处理管道 - 按顺序执行处理器。

    处理器按添加顺序执行，每个处理器的输出
    成为下一个处理器的输入。
    """

    def __init__(self, steps: Optional[List[BaseProcessor]] = None):
        """
        初始化管道。

        Args:
            steps: 可选的初始处理器列表
        """
        self.steps: List[BaseProcessor] = steps or []

    def add(self, processor: BaseProcessor) -> "Pipeline":
        """
        添加处理器到管道。

        Args:
            processor: 要添加的处理器

        Returns:
            返回自身以支持链式调用
        """
        self.steps.append(processor)
        return self

    def insert(self, index: int, processor: BaseProcessor) -> "Pipeline":
        """
        在指定位置插入处理器。

        Args:
            index: 插入位置的索引
            processor: 要插入的处理器

        Returns:
            返回自身以支持链式调用
        """
        self.steps.insert(index, processor)
        return self

    def remove(self, name: str) -> "Pipeline":
        """
        按类名移除处理器。

        Args:
            name: 要移除的处理器类名

        Returns:
            返回自身以支持链式调用
        """
        self.steps = [p for p in self.steps if p.__class__.__name__ != name]
        return self

    def clear(self) -> "Pipeline":
        """
        清空管道中的所有处理器。

        Returns:
            返回自身以支持链式调用
        """
        self.steps.clear()
        return self

    def execute(self, input_data: Any) -> ProcessResult:
        """
        执行管道。

        Args:
            input_data: 要处理的输入数据

        Returns:
            包含最终处理后数据的ProcessResult
        """
        current_data = input_data
        all_errors: List[str] = []

        for i, processor in enumerate(self.steps):
            try:
                result = processor.process(current_data)

                if not result.success:
                    return ProcessResult(
                        success=False,
                        data=current_data,
                        errors=result.errors,
                        metadata={"failed_at_step": i, "processor": processor.__class__.__name__},
                    )

                current_data = result.data

            except Exception as e:
                all_errors.append(f"Exception in {processor.__class__.__name__}: {str(e)}")
                return ProcessResult(
                    success=False,
                    data=current_data,
                    errors=all_errors,
                    metadata={"failed_at_step": i, "processor": processor.__class__.__name__},
                )

        return ProcessResult(
            success=True,
            data=current_data,
            metadata={"steps_executed": len(self.steps)},
        )

    def execute_batch(self, inputs: List[Any]) -> List[ProcessResult]:
        """
        批量执行管道。

        Args:
            inputs: 输入数据列表

        Returns:
            ProcessResult对象列表
        """
        return [self.execute(input_data) for input_data in inputs]

    def __len__(self) -> int:
        """返回管道中的步骤数量。"""
        return len(self.steps)

    def __repr__(self) -> str:
        """返回管道的字符串表示。"""
        steps_str = ", ".join(p.__class__.__name__ for p in self.steps)
        return f"Pipeline(steps=[{steps_str}])"
