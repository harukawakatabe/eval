# 文档标注测试脚本

本目录包含用于测试文档标注功能的脚本。

## 测试脚本列表

| 脚本 | 说明 |
|---|---|
| `test_cross_page_table.py` | 测试跨页表格检测功能 |
| `test_table_detection.py` | 测试表格检测和 table_dominant 判断 |
| `test_chart_detection.py` | 测试图表检测功能 |
| `test_parser_comparison.py` | 对比 Legacy 和 Docling 解析器 |
| `run_all_tests.py` | 批量运行所有测试 |

## 使用方法

### 1. 测试单个文件

```bash
# 从项目根目录运行
cd docs_annotation

# 测试跨页表格
python -m test.test_cross_page_table "path/to/document.docx"

# 测试表格检测
python -m test.test_table_detection "path/to/document.pdf"

# 测试图表检测
python -m test.test_chart_detection "path/to/document.pdf"
```

### 2. 对比解析器

```bash
# 对比单个文件
python -m test.test_parser_comparison "path/to/document.pdf"

# 批量对比目录
python -m test.test_parser_comparison "path/to/directory" --batch

# 保存结果到 JSON
python -m test.test_parser_comparison "path/to/directory" --batch -o results.json
```

### 3. 批量测试

```bash
# 测试目录下所有文件
python -m test.run_all_tests "path/to/test/data"

# 显示详细日志
python -m test.run_all_tests "path/to/test/data" -v
```

## 测试用例

针对您提到的问题文件：

```bash
# 1. 跨页表格测试
python -m test.test_cross_page_table "reference/data/Files/业务交付管理/12月百应分结果及大区排名.docx"

# 2. 表格误识别为图片
python -m test.test_table_detection "reference/data/Files/业务交付管理/2-联想百应服务商收费标准.pdf"
python -m test.test_table_detection "reference/data/Files/业务交付管理/3-联想百应社区服务站优惠券返还政策.pdf"

# 3. table_dominant 判断
python -m test.test_table_detection "reference/data/Files/业务交付管理/5-联想百应《优选服务商红黄线管理规则》2025年第四版1001.pdf"
```

## 使用 test_one.py

项目根目录下的 `test_one.py` 也支持命令行参数：

```bash
# 基本使用
python test_one.py document.pdf

# 详细日志
python test_one.py document.pdf -v

# 指定解析器
python test_one.py document.pdf --parser docling
python test_one.py document.pdf --parser legacy

# 静默模式
python test_one.py document.pdf -q
```

## 日志级别

- `-v` / `--verbose`: DEBUG 级别，显示所有详细信息
- 默认: INFO 级别，显示关键信息
- `-q` / `--quiet`: WARNING 级别，仅显示警告和错误
