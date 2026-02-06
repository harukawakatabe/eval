# 日志目录说明

该目录用于存储批量标注过程中的日志文件。

## 使用方法

### 启用日志落盘

在运行 `batch_annotate.py` 时添加 `--log-to-file` 参数：

```bash
# 基本使用
python batch_annotate.py --log-to-file

# 结合其他参数
python batch_annotate.py --log-to-file --parser legacy --verbose

# 使用 Mock 模型测试
python batch_annotate.py --log-to-file --use-mock
```

### 日志文件命名规则

日志文件使用时间戳命名，格式为：`annotation_YYYYMMDD_HHMMSS.log`

示例：
- `annotation_20260206_101404.log`
- `annotation_20260206_143022.log`

### 日志内容

日志文件包含：
- 文件处理进度
- 解析器使用情况
- 元素检测结果（图片、表格、公式、图表）
- OCR 处理信息
- 特征提取结果
- 布局分类结果
- 错误和警告信息
- 处理耗时

## 日志示例

```
[10:14:04] [INFO] ============================================================
[10:14:04] [INFO] [FILE] 开始处理: D:\Project\Test\eval\reference\data\Files\test.pdf
[10:14:04] [INFO]    文件类型: pdf
[10:14:04] [INFO] [PARSER] 使用解析器: Legacy (pdfplumber/python-docx)
[10:14:04] [INFO] [RESULT] 解析结果:
[10:14:04] [INFO]    页数: 5
[10:14:04] [INFO]    图片: 3 个
[10:14:04] [INFO]    表格: 2 个
[10:14:04] [INFO]    公式: 0 个
[10:14:04] [INFO]    图表: 0 个
[10:14:04] [INFO] [LAYOUT] 布局类型: single (LLM分类)
[10:14:04] [INFO] [OK] 处理完成: test.pdf (1234ms)
[10:14:04] [INFO] ============================================================
```

## 注意事项

- 日志文件会随着处理文件数量增多而变大，建议定期清理旧日志
- `.gitignore` 已配置为忽略 `.log` 文件，不会提交到版本控制
- 控制台输出不受影响，启用日志落盘后会同时输出到控制台和文件
