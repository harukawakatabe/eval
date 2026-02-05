# RAG 评估数据集（Mock Query）生成系统

本目录用于**生成/管理 RAG 评估数据集的 query**，并把所有产物（queries、统计、日志、示例）统一输出到 `mock_query/` 下。

你的文档标注 schema 由 `docs_annotation/src/core/schema.py` 定义（`DocumentAnnotation`），我们会在生成 query 的同时把文档标签携带到每条样本里，以便后续按标签切片评估、定位优化点。

---

## 1. 这个“生成系统”要解决什么问题

目标不是“随机造问题”，而是构建一套**可解释、可复现、可均衡覆盖**的评估 query 生成流水线，服务于：

- **覆盖面**：不同 `file_type`、不同 PDF 结构特征（表格/跨页/双栏/图表/公式/阅读顺序敏感等）都要被“平均地”覆盖。
- **可诊断**：每条 query 都带上 “压力点/意图/预期行为/标签”，便于把失败样本归因到 RAG 流程环节（解析→切分→召回→重排→生成）。
- **可扩展**：HR 领域优先；后续可通过新增模板/策略扩展到更多领域或更细的评估维度。

---

## 2. 输入与输出约定

### 输入

- **文档标注结果**：由 `docs_annotation` 产出的 `DocumentAnnotation` JSON（建议路径：`docs_annotation/output/*.json`）。
  - 当前工作区没有现成 JSON（`docs_annotation/output/` 为空），所以这里提供的是**生成器与工作流**，等你跑完标注后即可直接生成 query。
- **可选：文档内容**：若标注 JSON 内包含 `file_path` 且文件可访问，则可进一步做“基于内容的 query grounding”（更像真实用户问题）。
- **可选：chunk 映射**：如果你的 RAG 索引层能提供 `doc_id -> chunk_id` 映射（或检索日志），可用于填充 `required_chunks/optional_chunks`，从而做更严格的自动评测。

### 输出（全部在 `mock_query/` 下）

- `mock_query/queries/queries.jsonl`：最终样本集（每行一条 JSON）。
- `mock_query/queries/stats.json`：分布统计（按 file_type、PDF 特征桶、expected_behavior、压力点等）。
- `mock_query/queries/manifest.json`：生成配置、时间戳、随机种子、样本量等元信息。
- `mock_query/mock_annotations/`：示例标注（用于自检/演示格式）。
- `mock_query/templates_hr.json`：HR 域 query 模板库（可扩展）。

---

## 3. 数据结构（建议）

每条样本建议至少包含（结合你给的参考 schema）：

- `query`：自然语言问题（HR 领域）。
- `domain`：固定 `"hr"`。
- `expected_behavior`：`answer | partial | refuse | ask_clarification`。
- `doc_annotation`：原始文档标签（至少 `doc_id`、`file_type`、`pdf_profile`）。
- `stressors`：由标签推导的“压力点”数组（例如：`["has_table","cross_page_table"]`）。
- `required_chunks/optional_chunks/forbidden_chunks`：若暂时没有 chunk 映射，可先置空数组。
- `answer_constraints`：必须提及/不得提及的约束（用于抓住“幻觉/越权/不合规”）。

---

## 4. 生成策略（两段式）

### A. 结构覆盖（仅靠标注就能做）

1. **分层/分桶**：以 `file_type` 为第一层；PDF 再按 `layout + has_table/has_chart/… + table_profile/chart_profile + reading_order_sensitive` 生成桶或压力点集合。
2. **均衡采样**：为每个桶分配配额，缺口用相邻桶回填或允许“带放回”采样（可配置）。
3. **模板化生成**：按桶/压力点选择 HR 模板，生成可控的 query，并标注预期行为。

这一步主要用于“流程健壮性”评估：某类结构一多就崩/召回缺失/排序偏差等。

### B. 内容 grounding（可选，但强烈建议）

1. 解析文档文本（可复用 `docs_annotation` 的 `DocParser`）。
2. 抽取候选主题（标题/小节名/高频关键词/金额比例/时间规则等）。
3. 将主题填入模板，形成“与文档强绑定”的 query。

这一步用于“真实可回答性”评估：防止生成出文档里根本没有的信息，导致评估无意义。

---

## 5. 如何运行（建议流程）

1. **先产出标注 JSON**（示例，按你的实际文档路径改）：

```bash
python docs_annotation/main.py
```

或你自己写个批处理，调用 `AnnotationService.annotate_batch()` 并保存到 `docs_annotation/output/`。

2. **生成 queries**：

```bash
python mock_query/generate_queries.py ^
  --annotations_dir docs_annotation/output ^
  --out_dir mock_query/queries ^
  --per_file_type 50 ^
  --seed 20260204
```

如需内容 grounding（需要能访问文件路径、并安装解析依赖）：

```bash
python mock_query/generate_queries.py ^
  --annotations_dir docs_annotation/output ^
  --out_dir mock_query/queries ^
  --docs_dir <你的文档根目录> ^
  --ground_with_content
```

---

## 6. 这个系统的“能力清单”（面向你的标注项目）

- **均衡覆盖**：自动对不同文档类型/结构特征做配额控制，避免评估集被某类 PDF（或某类简单文本）“垄断”。
- **可诊断失败**：通过 `stressors + expected_behavior + doc_annotation` 让你能快速定位：
  - 解析失败（DocParser）
  - OCR/元素检测导致的结构信息缺失（ElementDetector/FeatureExtractor）
  - 切分策略对跨页表格/双栏的破坏
  - 召回对表格/数字/图表描述的丢失
  - 生成端越权/编造/不回答（refuse/ask_clarification）
- **可扩展模板库**：HR 域模板可持续扩充（假期、薪酬、绩效、入离职、培训、制度合规、隐私等）。

