# 文档标注系统

一个灵活、可扩展的文档标注框架，支持多种文档格式的结构化标注。

## 功能特性

- **多格式支持**: PDF、Word、Excel、PPT、HTML、TXT、Markdown
- **元素检测**: 图片、表格、公式、图表
- **特征提取**: 跨页检测、长表格识别、内容主导性分析
- **布局分类**: 单页/双页/混合布局自动识别
- **可插拔模型**: 支持多种OCR和LLM模型

## 项目结构

```
docs_annotation/
├── src/
│   ├── core/              # 核心框架
│   │   ├── base.py        # 基类定义
│   │   ├── pipeline.py    # 处理管道
│   │   └── schema.py      # Schema定义
│   │
│   ├── processors/        # 处理器模块
│   │   ├── doc_parser.py      # 文档解析器
│   │   ├── element_detector.py # 元素检测
│   │   ├── feature_extractor.py # 特征提取
│   │   └── layout_classifier.py # 布局分类
│   │
│   ├── models/            # 模型接口
│   │   ├── ocr.py         # OCR模型
│   │   └── llm.py         # LLM模型
│   │
│   └── service.py         # 统一服务入口
│
├── config/                # 配置文件
│   └── processors.yaml    # 处理器配置
│
├── docs/                  # 文档目录
│   ├── 需求文档.md
│   ├── 技术文档.md
│   └── 技术文档v2.md
│
├── output/                # 输出目录
├── main.py                # 使用示例
├── batch_annotate.py      # 批量处理脚本
└── requirements.txt       # 依赖列表
```

## 安装

### 使用 pip

```bash
pip install -r requirements.txt
```

### 使用 uv（推荐，更快）

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
# Windows PowerShell
.venv\Scripts\activate

# 安装依赖
uv pip install -r requirements.txt
```

### 可选依赖

```bash
# Tesseract OCR (需要先安装tesseract程序)
pip install pytesseract

# Claude API
pip install anthropic
```

### 环境配置

**方式一：使用 .env 文件（推荐）**

1. 复制 `.env.example` 为 `.env`：

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

2. 编辑 `.env` 文件，填入您的 API 密钥：

```bash
# OpenAI 配置
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，支持自定义 API 地址

# Anthropic (Claude) 配置（可选）
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# 其他配置（可选）
# OPENAI_MODEL=gpt-4
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

**方式二：环境变量**

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="your-api-key-here"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选

# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
```

> **注意**：使用 `.env` 文件的方式更安全，且不需要每次重新设置环境变量。

## 快速开始

### 批量处理（推荐）

**第一步：配置 API 密钥**

确保已配置 `.env` 文件或设置了环境变量（见上方"环境配置"）。

**第二步：运行批量处理**

```bash
# 测试运行（使用 Mock 模型，无需 API）
python batch_annotate.py --use-mock

# 正式运行（使用 PaddleOCR + OpenAI）
python batch_annotate.py

# 自定义输入输出目录
python batch_annotate.py --input ../reference/data/Files --output ./output

# 重新处理所有文件（不跳过已标注的）
python batch_annotate.py --no-skip-existing
```

**功能特性：**
- ✅ 自动扫描目录及子目录
- ✅ 过滤支持的文件格式（PDF、Word、Excel、PPT）
- ✅ 自动排除 `parsing_failed_files.json` 中的失败文件
- ✅ 保持原有目录结构输出结果
- ✅ 显示处理进度和统计信息
- ✅ 生成失败文件报告
- ✅ 支持增量处理（跳过已标注文件）

### 单文件处理

### 1. 使用Mock模型（无需API）

```python
from service import AnnotationService
from models.ocr import MockOCR
from models.llm import MockLLM

service = AnnotationService(
    ocr_model=MockOCR(),
    llm_model=MockLLM(),
)

annotation = service.annotate("document.pdf")
print(annotation.to_json())
```

### 2. 使用PaddleOCR + OpenAI

```python
import os
from service import AnnotationService
from models.ocr import PaddleOCRModel
from models.llm import OpenAILLM

service = AnnotationService(
    ocr_model=PaddleOCRModel(lang="ch"),
    llm_model=OpenAILLM(
        api_key=os.environ["OPENAI_API_KEY"],
        model="gpt-4"
    ),
)

annotation = service.annotate("document.pdf")
print(annotation.to_json())

# 保存结果
service.save_annotation(annotation, "output/result.json")
```

### 3. 使用配置文件

```python
from service import AnnotationService

# 加载配置
config = AnnotationService.load_config("config/processors.yaml")

# 根据配置初始化服务
service = AnnotationService(
    ocr_model=PaddleOCRModel(),
    llm_model=OpenAILLM(api_key="..."),
    config=config.get("processors", {})
)
```

## 标注结果格式

所有文档类型统一使用 `doc_profile` 输出：

**PDF 文档（完整字段）：**
```json
{
  "doc_id": "document",
  "file_type": "pdf",
  "file_path": "/path/to/document.pdf",
  "doc_profile": {
    "layout": "single",
    "has_image": true,
    "has_table": true,
    "has_formula": false,
    "has_chart": false,
    "image_text_mixed": true,
    "reading_order_sensitive": false,
    "table_profile": {
      "long_table": false,
      "cross_page_table": true,
      "table_dominant": false
    },
    "chart_profile": {
      "cross_page_chart": false
    }
  }
}
```

**Word/Excel/PPT 文档（简化字段，无跨页信息）：**
```json
{
  "doc_id": "document",
  "file_type": "doc",
  "file_path": "/path/to/document.docx",
  "doc_profile": {
    "layout": "single",
    "has_image": true,
    "has_table": true,
    "has_formula": false,
    "has_chart": false,
    "image_text_mixed": true
  }
}
```

> **说明**：`table_profile` 和 `chart_profile` 仅对 PDF 输出，因为跨页概念只对 PDF 有意义。

### 各文件类型元素检测方式

| 文件类型 | 检测方式 | 支持的元素 |
|---------|---------|-----------|
| **PDF** | `pdfplumber` 结构化解析 | 图片、表格、图表（基于线条/矩形数量推断）、公式（暂不支持） |
| **Word (.docx)** | `python-docx` 结构化解析 | 图片（内联+关系）、表格、公式（OMML）、图表（嵌入chart） |
| **PPT (.pptx)** | `python-pptx` 结构化解析 | 图片、表格、图表、公式（OLE对象） |
| **Excel (.xlsx)** | `openpyxl` 结构化解析 | 图片、表格（默认true）、图表、公式（单元格公式） |
| **HTML/TXT** | 文本解析 | 暂不支持元素检测 |

> **图文混排检测**：对所有文档类型，当检测到图片且文字超过100字符时，`image_text_mixed` 为 `true`。

## 支持的模型

### OCR模型

| 模型 | 安装命令 | 说明 |
|-----|---------|------|
| MockOCR | 无需安装 | 用于测试，返回空结果 |
| PaddleOCR | `pip install paddleocr` | 支持中英文 |
| Tesseract | `pip install pytesseract` | 需安装tesseract程序 |

### LLM模型

| 模型 | 安装命令 | 说明 |
|-----|---------|------|
| MockLLM | 无需安装 | 用于测试 |
| OpenAI | `pip install openai` | GPT-4, GPT-3.5 |
| Claude | `pip install anthropic` | Claude 3.5 Sonnet |

## 批量处理命令行参数

```bash
python batch_annotate.py [OPTIONS]

选项:
  --input PATH            输入文档目录（默认: ../reference/data/Files）
  --output PATH           输出结果目录（默认: ./output）
  --use-mock             使用 Mock 模型（用于测试流程）
  --no-skip-existing     不跳过已标注的文件（重新处理所有文件）
  -v, --verbose          显示每个文件的处理详情（默认只显示进度条）
  -h, --help             显示帮助信息
```

## 不使用脚本的方法

如果你不想使用 `batch_annotate.py`，可以直接调用 `AnnotationService`：

### 方法一：Python 代码调用

```python
import sys
sys.path.insert(0, "docs_annotation/src")

from service import AnnotationService
from models.ocr import MockOCR  # 或 PaddleOCRModel
from models.llm import MockLLM  # 或 OpenAILLM

# 初始化服务
service = AnnotationService(
    ocr_model=MockOCR(),
    llm_model=MockLLM(),
)

# 单文件标注
annotation = service.annotate("path/to/document.docx")
print(annotation.to_json())

# 保存结果
service.save_annotation(annotation, "output/result.json")

# 批量标注（自己遍历文件）
from pathlib import Path
for file_path in Path("documents").rglob("*.docx"):
    ann = service.annotate(str(file_path))
    service.save_annotation(ann, f"output/{file_path.stem}.json")
```

### 方法二：使用 uv run 一行命令

```bash
# 单文件标注（输出到控制台）
uv run python -c "
import sys; sys.path.insert(0, 'docs_annotation/src')
from service import AnnotationService
from models.ocr import MockOCR
from models.llm import MockLLM
service = AnnotationService(ocr_model=MockOCR(), llm_model=MockLLM())
print(service.annotate('path/to/document.docx').to_json())
"
```

## 配置说明

配置文件位于 `config/processors.yaml`，可配置：

- **文档解析器**: 支持的文件格式、是否提取图像
- **元素检测器**: 启用的检测器、置信度阈值
- **特征提取器**: 跨页检测、长表格阈值
- **布局分类器**: 是否使用LLM
- **模型配置**: OCR 模型类型（paddleocr/tesseract）、LLM 模型类型（openai/claude）

## 扩展开发

### 新增文档类型

1. 在 `FileType` 枚举中添加新类型
2. 在 `DocParser` 中添加解析逻辑
3. 定义对应的 Profile

### 新增OCR模型

```python
from models.ocr import OCRModel

class MyOCR(OCRModel):
    def detect_elements(self, image_data: bytes):
        # 实现检测逻辑
        pass

    def extract_text(self, image_data: bytes):
        # 实现文本提取
        pass
```

### 新增处理器

```python
from core.base import BaseProcessor, ProcessResult

class MyProcessor(BaseProcessor):
    def process(self, input_data):
        # 实现处理逻辑
        return ProcessResult(success=True, data=result)
```

## 运行示例

### 批量处理示例

```bash
# 1. 配置 .env 文件（首次使用）
copy .env.example .env
# 然后编辑 .env，填入您的 OPENAI_API_KEY

# 2. 测试流程（使用 Mock 模型）
python batch_annotate.py --use-mock

# 3. 处理特定目录
python batch_annotate.py --input ../reference/data/Files/供应商管理部

# 4. 正式批量处理
python batch_annotate.py
```

### 单文件处理示例

```bash
python main.py
```

## 输出结果

批量处理后，输出目录结构如下：

```
output/
├── 供应商管理部/
│   ├── document1.json
│   ├── document2.json
│   └── ...
├── 城市运营/
│   ├── document3.json
│   └── ...
└── failed_files.json  # 失败文件报告（如果有）
```

每个 JSON 文件包含对应文档的完整标注信息。

## 注意事项

1. **支持的文件格式**：PDF、Word (.doc/.docx)、Excel (.xls/.xlsx)、PowerPoint (.ppt/.pptx)
2. **不支持的格式**：图片文件 (.jpg/.png) 会被自动跳过
3. **API 配置**：
   - 推荐使用 `.env` 文件管理 API 密钥
   - 支持自定义 `OPENAI_BASE_URL`（如使用代理或国内 API）
   - `.env` 文件不应提交到 git（已在 .gitignore 中）
4. **API 配额**：使用真实模型时注意 API 调用次数和费用
5. **处理时间**：大量文档处理可能需要较长时间，建议先用 `--use-mock` 测试流程
6. **增量处理**：默认跳过已标注的文件，使用 `--no-skip-existing` 强制重新处理

## 许可证

MIT License
