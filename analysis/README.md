# 文档标注分析模块

分析 `docs_annotation` 输出的标注结果，为 `mock_query` 的 query 抽取提供数据支撑。

## 功能

- **基础统计**: 文件数量、类型分布、文件夹分布
- **标签分布**: 各标签的 true/false 比例
- **压力点组合分析**: 识别常见/稀有组合，定位高复杂度文档
- **分桶分析**: 按 file_type 和 PDF 特征分桶，支持均衡采样
- **覆盖缺口分析**: 发现空桶、稀疏桶、缺失特征
- **采样建议**: 输出可直接用于 `mock_query` 的配置建议

## 快速开始

```bash
# 1. 确保已有标注结果
uv run python docs_annotation/batch_annotate.py --input <文档目录>

# 2. 运行分析
uv run python analysis/analyze.py
```

## 命令行参数

| 参数 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | `-i` | `docs_annotation/output` | 标注输出目录 |
| `--output` | `-o` | `analysis/reports` | 报告输出目录 |
| `--folder` | `-f` | 无 | 仅分析指定子文件夹 |
| `--sparse-threshold` | | 3 | 稀疏桶阈值（文件数 < N 视为稀疏） |
| `--complexity-threshold` | | 3 | 高复杂度阈值（压力点 >= N） |
| `--json-only` | | | 仅输出 JSON |
| `--csv-only` | | | 仅输出 CSV |
| `--md-only` | | | 仅输出 Markdown |
| `--quiet` | `-q` | | 安静模式 |

## 使用示例

```bash
# 基本用法
uv run python analysis/analyze.py

# 指定输入输出目录
uv run python analysis/analyze.py \
  --input docs_annotation/output \
  --output analysis/reports

# 仅分析某个文件夹
uv run python analysis/analyze.py --folder 城市运营

# 调整阈值
uv run python analysis/analyze.py \
  --sparse-threshold 5 \
  --complexity-threshold 4

# 仅生成 Markdown 报告
uv run python analysis/analyze.py --md-only
```

## 输出文件

运行后将在输出目录生成以下文件：

### JSON 文件

| 文件 | 说明 |
|------|------|
| `summary.json` | 全量统计汇总 |
| `by_folder.json` | 按文件夹的分析 |
| `buckets.json` | 分桶详情（桶 → 文件列表） |
| `stressor_combos.json` | 压力点组合统计 |
| `gaps.json` | 覆盖缺口分析 |
| `sampling_advice.json` | 采样建议 |

### CSV 文件

| 文件 | 说明 |
|------|------|
| `tag_distribution.csv` | 标签分布表 |
| `bucket_distribution.csv` | 分桶分布表 |
| `high_complexity_docs.csv` | 高复杂度文档列表 |

### Markdown 文件

| 文件 | 说明 |
|------|------|
| `REPORT.md` | 可读分析报告 |

## 分析维度详解

### 1. 基础统计

统计文件总数、按文件类型分布、按文件夹分布。

### 2. 标签分布

分析以下标签的 true/false 比例：

**通用标签（所有文件类型）**:
- `layout` (single/double/mixed)
- `has_image`
- `has_table`
- `has_formula`
- `has_chart`
- `image_text_mixed`

**PDF 专属标签**:
- `reading_order_sensitive`
- `table_profile.long_table`
- `table_profile.cross_page_table`
- `table_profile.table_dominant`
- `chart_profile.cross_page_chart`

### 3. 压力点组合分析

- **压力点计数分布**: 0/1/2/3+ 个压力点的文档各多少
- **常见组合 TOP 20**: 最频繁出现的压力点组合
- **稀有组合**: 仅出现 1-2 次的边缘 case
- **高复杂度文档**: 压力点 >= 阈值的文档列表

### 4. 分桶分析

对齐 `mock_query` 的 `balance_keys` 配置：

```
一级桶: file_type
  ├── pdf (35)
  │     ├── 二级桶: layout=single | has_table (12)
  │     ├── 二级桶: layout=single | has_chart (8)
  │     └── ...
  ├── doc (10)
  └── ppt (5)
```

### 5. 覆盖缺口分析

- **空桶**: 某些特征组合完全没有文档
- **稀疏桶**: 文件数 < 阈值的桶
- **缺失特征**: 整个数据集中某标签全为 false
- **文件类型缺口**: 某 file_type 数量过少

### 6. 采样建议

输出可直接用于 `mock_query/config.json` 的配置：

```json
{
  "per_file_type": 10,
  "queries_per_doc": 2,
  "allow_sample_with_replacement": true,
  "balance_keys": {
    "level1": "file_type",
    "pdf_stressors": ["has_table", "has_chart", ...]
  }
}
```

## 与 mock_query 配合使用

```bash
# 1. 运行标注
uv run python docs_annotation/batch_annotate.py --input <文档目录>

# 2. 运行分析
uv run python analysis/analyze.py

# 3. 查看报告，根据建议调整 mock_query 配置
cat analysis/reports/REPORT.md
cat analysis/reports/sampling_advice.json

# 4. 生成 query
uv run python mock_query/generate_queries.py \
  --annotations_dir docs_annotation/output \
  --per_file_type 10  # 根据分析建议设置
```

## Python API

```python
from analysis.analyzer import AnnotationAnalyzer

# 创建分析器
analyzer = AnnotationAnalyzer(
    input_dir="docs_annotation/output",
    sparse_threshold=3,
    complexity_threshold=3,
)

# 运行完整分析
result = analyzer.run_full_analysis()

# 获取采样建议
advice = analyzer.generate_sampling_advice()
print(advice["recommended_per_file_type"])

# 导出所有报告
analyzer.export_all("analysis/reports")
```

## 目录结构

```
analysis/
├── __init__.py          # 包初始化
├── analyzer.py          # 核心分析类
├── analyze.py           # CLI 入口
├── README.md            # 本文档
└── reports/             # 输出目录（运行后生成）
    ├── summary.json
    ├── by_folder.json
    ├── buckets.json
    ├── stressor_combos.json
    ├── gaps.json
    ├── sampling_advice.json
    ├── tag_distribution.csv
    ├── bucket_distribution.csv
    ├── high_complexity_docs.csv
    └── REPORT.md
```
