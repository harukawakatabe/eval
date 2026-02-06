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
│   │   ├── logger.py      # 日志模块
│   │   ├── pipeline.py    # 处理管道
│   │   └── schema.py      # Schema定义
│   │
│   ├── processors/        # 处理器模块
│   │   ├── doc_parser.py      # 文档解析器（Legacy）
│   │   ├── docling_parser.py  # Docling高精度解析器
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
│
├── test/                  # 测试目录
│   ├── run_all_tests.py       # 运行所有测试
│   ├── test_table_detection.py
│   ├── test_chart_detection.py
│   ├── test_cross_page_table.py
│   └── test_parser_comparison.py
│
├── output/                # 输出目录（运行时生成）
├── main.py                # 使用示例
├── test_one.py            # 单文件测试脚本
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

# 使用轻量级解析器（不需要 Docling/GPU，速度快）
python batch_annotate.py --parser legacy

# 组合使用：轻量解析器 + Mock 模型 + 详细输出
python batch_annotate.py --parser legacy --use-mock -v
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
import sys
sys.path.insert(0, "src")  # 添加src目录到路径

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
import sys
import os
sys.path.insert(0, "src")

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
import sys
sys.path.insert(0, "src")

from service import AnnotationService
from models.ocr import PaddleOCRModel
from models.llm import OpenAILLM

# 加载配置
config = AnnotationService.load_config("config/processors.yaml")

# 根据配置初始化服务
service = AnnotationService(
    ocr_model=PaddleOCRModel(),
    llm_model=OpenAILLM(api_key="..."),
    config=config.get("processors", {})
)
```

### 4. 使用单文件测试脚本

```bash
# 基本使用
python test_one.py document.pdf

# 详细日志模式
python test_one.py document.pdf -v

# 指定解析器（auto/docling/legacy）
python test_one.py document.pdf --parser docling

# 静默模式
python test_one.py document.pdf -q
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
    "has_image_table": false,
    "has_complex_table": true,
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
    "has_image_table": false,
    "has_complex_table": false,
    "has_formula": false,
    "has_chart": false,
    "image_text_mixed": true
  }
}
```

> **说明**：`table_profile` 和 `chart_profile` 仅对 PDF 输出，因为跨页概念只对 PDF 有意义。

### 表格字段说明（RAG 场景）

| 字段 | 含义 | RAG 影响 |
|------|------|---------|
| `has_table` | 是否有**可被结构化解析**的表格 | 能正常 chunk 和问答 |
| `has_image_table` | 是否有**图片形式**的表格（扫描版/截图） | 需要 OCR，结构可能丢失，chunking 时可能变成图片或纯文字 |
| `has_complex_table` | 是否有**复杂表格**（>10列 / >100行 / 宽表格） | 即使解析也难在 chunk 中保持格式，问答可能不准确 |

**判断标准：**
- `has_image_table = True`：检测到大图片但没有对应的结构化表格
- `has_complex_table = True`：列数 > 10，或行数 > 100，或列数 ≥ 7 且行数 > 20

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
  --parser TYPE          解析器类型: auto, docling, legacy（默认: auto）
  -v, --verbose          显示每个文件的处理详情（默认只显示进度条）
  -h, --help             显示帮助信息
```

### 解析器选项说明

| 选项 | 说明 | 适用场景 |
|------|------|---------|
| `auto` | 自动选择（优先 Docling） | 默认选项，自动适配 |
| `docling` | 强制使用 Docling | 需要高精度解析，有 GPU 加速 |
| `legacy` | 使用 pdfplumber/python-docx | 轻量快速，不需要 GPU |

```bash
# 使用 legacy 解析器（快速，不需要 Docling/GPU）
python batch_annotate.py --parser legacy

# 使用 legacy + Mock 模型测试
python batch_annotate.py --parser legacy --use-mock

# 使用 legacy + 详细输出
python batch_annotate.py --parser legacy -v
```

## 不使用脚本的方法

如果你不想使用 `batch_annotate.py`，可以直接调用 `AnnotationService`：

### 方法一：Python 代码调用（在 docs_annotation 目录下）

```python
import sys
sys.path.insert(0, "src")

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

### 方法二：从外部目录调用

```python
import sys
sys.path.insert(0, "docs_annotation/src")

from service import AnnotationService
from models.ocr import MockOCR
from models.llm import MockLLM

service = AnnotationService(ocr_model=MockOCR(), llm_model=MockLLM())
print(service.annotate("path/to/document.docx").to_json())
```

### 方法三：使用 uv run 一行命令

```bash
# 单文件标注（在 docs_annotation 目录下执行）
uv run python -c "
import sys; sys.path.insert(0, 'src')
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
# 使用 test_one.py（推荐）
python test_one.py document.pdf -v

# 或使用 main.py 查看使用示例
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

# 使用示例

命令
```bash
python batch_annotate.py -v
```

输出
```json
{
  "doc_id": "【高德建店】规范文档建店SOP手册",
  "file_type": "pdf",
  "file_path": "D:\\Project\\Test\\eval\\reference\\data\\Files\\城市运营\\【高德建店】规范文档建店SOP手册.pdf",
  "doc_profile": {
    "layout": "single",
    "has_image": true,
    "has_table": true,
    "has_image_table": true,
    "has_complex_table": false,
    "has_formula": false,
    "has_chart": true,
    "image_text_mixed": true,
    "reading_order_sensitive": true,
    "table_profile": {
      "long_table": false,
      "cross_page_table": false,
      "table_dominant": false
    },
    "chart_profile": {
      "cross_page_chart": false
    }
  }
}
```

## 字段解读

### 文档通用标注 Profile

| 字段 | 类型 | 说明 |
|------|------|------|
| `layout` | string | 文档布局类型：`single`（单页）/ `double`（双页）/ `mixed`（混合） |
| `has_image` | bool | 文档是否包含图片 |
| `has_table` | bool | 是否有**可被结构化解析**的表格（能正常 chunk） |
| `has_image_table` | bool | 是否有**图片形式**的表格（扫描版/截图，chunking 时可能丢失或变成图片） |
| `has_complex_table` | bool | 是否有**复杂表格**（列数多/行数多，chunk 中难以保持格式） |
| `has_formula` | bool | 文档是否包含数学公式 |
| `has_chart` | bool | 文档是否包含图表 |
| `image_text_mixed` | bool | 是否为图文混排（同时包含图片和大量文字） |
| `reading_order_sensitive` | bool | 阅读顺序是否重要（可选，仅 PDF） |
| `table_profile` | object | 表格特征 Profile（仅 PDF，当 `has_table=True` 时） |
| `chart_profile` | object | 图表特征 Profile（仅 PDF，当 `has_chart=True` 时） |

### 表格特征 Profile

| 字段 | 类型 | 说明 |
|------|------|------|
| `long_table` | bool | 是否为长表格（跨 3 页以上） |
| `cross_page_table` | bool | 表格是否跨页 |
| `table_dominant` | bool | 表格是否占主导内容（可选） |

### 图表特征 Profile

| 字段 | 类型 | 说明 |
|------|------|------|
| `cross_page_chart` | bool | 图表是否跨页 |

### RAG 场景使用建议

根据表格字段组合，可以判断文档的解析难度：

| 组合 | 解析难度 | 建议处理方式 |
|------|---------|-------------|
| `has_table=true`, 其他 false | 低 | 直接使用结构化解析 |
| `has_image_table=true` | 中 | 需要 OCR + 表格识别，或使用 Docling |
| `has_complex_table=true` | 高 | 考虑特殊 chunk 策略，或提示用户表格可能不完整 |
| 两者都为 true | 高 | 建议人工审核或使用专业表格提取工具 |