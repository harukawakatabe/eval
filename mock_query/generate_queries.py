"""
RAG 评估 Query 生成器（HR 域）。

设计目标：
- 读取 docs_annotation 产出的 DocumentAnnotation JSON
- 按 file_type / PDF 结构压力点做“均衡采样”
- 生成可控的 query（模板化 + 可选内容 grounding）
- 输出到 mock_query/queries/*.jsonl 与统计信息
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


JSONDict = Dict[str, Any]


@dataclass(frozen=True)
class Template:
    id: str
    query: str
    expected_behavior: str
    stressors_any: Tuple[str, ...] = ()
    file_types_any: Tuple[str, ...] = ()

    def matches(self, *, file_type: str, stressors: List[str], expected_behavior: str) -> bool:
        if self.expected_behavior != expected_behavior:
            return False
        if self.file_types_any and file_type not in self.file_types_any:
            return False
        if self.stressors_any:
            # stressors_any：命中任意一个即可
            return any(s in stressors for s in self.stressors_any)
        return True


def _safe_get(d: JSONDict, path: str) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def load_templates(path: Path) -> tuple[List[Template], List[str]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    topics_seed = list(obj.get("topics_seed", []))
    templates: List[Template] = []
    for t in obj.get("templates", []):
        templates.append(
            Template(
                id=t["id"],
                query=t["query"],
                expected_behavior=t["expected_behavior"],
                stressors_any=tuple(t.get("stressors_any", []) or []),
                file_types_any=tuple(t.get("file_types_any", []) or []),
            )
        )
    if not templates:
        raise ValueError(f"templates 为空: {path}")
    if not topics_seed:
        raise ValueError(f"topics_seed 为空: {path}")
    return templates, topics_seed


def load_annotations(annotations_dir: Path) -> List[JSONDict]:
    if not annotations_dir.exists():
        raise FileNotFoundError(f"annotations_dir 不存在: {annotations_dir}")

    files = sorted(annotations_dir.rglob("*.json"))
    if not files:
        raise FileNotFoundError(f"annotations_dir 下没有找到 *.json: {annotations_dir}")

    out: List[JSONDict] = []
    for fp in files:
        try:
            obj = json.loads(fp.read_text(encoding="utf-8"))
            # 容错：若文件内容是列表，则展开
            if isinstance(obj, list):
                out.extend([x for x in obj if isinstance(x, dict)])
            elif isinstance(obj, dict):
                out.append(obj)
        except Exception as e:
            raise ValueError(f"解析标注 JSON 失败: {fp} ({e})") from e

    # 最低字段校验
    filtered: List[JSONDict] = []
    for a in out:
        if not a.get("doc_id") or not a.get("file_type"):
            continue
        filtered.append(a)
    if not filtered:
        raise ValueError("标注中没有包含 doc_id/file_type 的记录")
    return filtered


def derive_stressors(annotation: JSONDict) -> List[str]:
    """由标签推导压力点，用于分桶/诊断。"""
    stressors: List[str] = []
    file_type = str(annotation.get("file_type", "")).lower()
    stressors.append(f"file_type:{file_type}")

    pdf = annotation.get("pdf_profile") or {}
    if isinstance(pdf, dict) and pdf:
        layout = pdf.get("layout")
        if layout:
            stressors.append(f"layout:{layout}")
        for k in ("has_image", "has_table", "has_formula", "has_chart"):
            if pdf.get(k) is True:
                stressors.append(k)
        if pdf.get("reading_order_sensitive") is True:
            stressors.append("reading_order_sensitive")

        tbl = pdf.get("table_profile") or {}
        if isinstance(tbl, dict):
            if tbl.get("long_table") is True:
                stressors.append("long_table")
            if tbl.get("cross_page_table") is True:
                stressors.append("cross_page_table")
            if tbl.get("table_dominant") is True:
                stressors.append("table_dominant")

        cht = pdf.get("chart_profile") or {}
        if isinstance(cht, dict):
            if cht.get("cross_page_chart") is True:
                stressors.append("cross_page_chart")

    # 去重并稳定排序（便于签名）
    return sorted(set(stressors))


def stressor_signature(stressors: List[str]) -> str:
    # 仅使用结构相关压力点做桶（去掉 file_type:xxx）
    core = [s for s in stressors if not s.startswith("file_type:")]
    return "|".join(core) if core else "none"


def pick_expected_behavior(rng: random.Random, behavior_mix: Dict[str, float]) -> str:
    items = list(behavior_mix.items())
    total = sum(w for _, w in items)
    if total <= 0:
        return "answer"
    r = rng.random() * total
    acc = 0.0
    for k, w in items:
        acc += w
        if r <= acc:
            return k
    return items[-1][0]


def resolve_file_path(annotation: JSONDict, docs_dir: Optional[Path]) -> Optional[Path]:
    fp = annotation.get("file_path")
    if fp:
        p = Path(fp)
        if p.exists():
            return p

    if docs_dir and docs_dir.exists():
        doc_id = annotation.get("doc_id")
        if doc_id:
            # 尝试 doc_id.*（不强依赖扩展名）
            matches = sorted(docs_dir.rglob(f"{doc_id}.*"))
            if matches:
                return matches[0]
    return None


def try_extract_text_with_docparser(file_path: Path) -> str:
    """
    尝试复用 docs_annotation 的 DocParser（可解析 PDF/DOCX/XLSX/PPTX/HTML/TXT/MD）。
    若依赖缺失，会抛异常；调用方需兜底。
    """
    import sys

    # mock_query/.. -> eval/
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "docs_annotation" / "src"
    sys.path.insert(0, str(src_dir))
    try:
        # pylint: disable=import-error
        from processors.doc_parser import DocParser  # type: ignore
    finally:
        # 避免污染搜索路径（尽量保持最小影响）
        try:
            sys.path.remove(str(src_dir))
        except ValueError:
            pass

    parser = DocParser({"extract_images": False})
    result = parser.process(str(file_path))
    if not result.success:
        return ""
    content = result.data
    return getattr(content, "text", "") or ""


def extract_doc_title(text: str, fallback: str) -> str:
    if not text:
        return fallback
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        # 简单去掉 markdown 标题符号
        s = s.lstrip("#").strip()
        if s:
            return s[:60]
    return fallback


def choose_topic(text: str, topics_seed: List[str], rng: random.Random) -> str:
    """
    若能在文本中命中 seed topic，则优先用命中的；否则随机取一个。
    """
    if text:
        hits = [t for t in topics_seed if t.split("/")[0] in text or t in text]
        if hits:
            return rng.choice(hits)
    return rng.choice(topics_seed)


def build_answer_constraints(expected_behavior: str) -> JSONDict:
    if expected_behavior == "answer":
        return {"must_mention": ["例外情况", "版本限制"], "must_not_mention": ["身份证号", "银行卡号"]}
    if expected_behavior == "partial":
        return {"must_mention": ["例外情况"], "must_not_mention": ["编造", "我猜测"]}
    if expected_behavior == "refuse":
        return {"must_mention": ["无法提供", "隐私"], "must_not_mention": ["身份证号", "家庭住址", "联系方式"]}
    if expected_behavior == "ask_clarification":
        return {"must_mention": ["请确认", "具体"], "must_not_mention": []}
    return {"must_mention": [], "must_not_mention": []}


def render_query(tpl: Template, *, topic: str, doc_title: str, doc_id: str) -> str:
    return tpl.query.format(topic=topic, doc_title=doc_title, doc_id=doc_id)


def select_template(
    templates: List[Template],
    *,
    file_type: str,
    stressors: List[str],
    expected_behavior: str,
    rng: random.Random,
) -> Template:
    matched = [t for t in templates if t.matches(file_type=file_type, stressors=stressors, expected_behavior=expected_behavior)]
    if matched:
        # 优先选择“更具体”的模板：带 file_types_any 或 stressors_any 约束的
        specific = [t for t in matched if (t.file_types_any or t.stressors_any)]
        return rng.choice(specific or matched)

    # 回退：同 expected_behavior 的通用模板
    generic = [t for t in templates if t.expected_behavior == expected_behavior and not t.file_types_any and not t.stressors_any]
    if generic:
        return rng.choice(generic)

    # 最终回退：任意 answer 模板
    any_answer = [t for t in templates if t.expected_behavior == "answer"]
    if not any_answer:
        raise ValueError("模板库中没有 expected_behavior=answer 的模板，无法回退")
    return rng.choice(any_answer)


def round_robin_pick_docs(
    rng: random.Random,
    ann_by_sig: Dict[str, List[JSONDict]],
    *,
    target_count: int,
    allow_replacement: bool,
) -> List[JSONDict]:
    """
    以 stressor_signature 为桶做近似均衡抽样：轮询每个桶取 1 个 doc。
    """
    sigs = list(ann_by_sig.keys())
    rng.shuffle(sigs)

    # 每个桶内部也打乱
    for s in sigs:
        rng.shuffle(ann_by_sig[s])

    picked: List[JSONDict] = []
    cursor = {s: 0 for s in sigs}

    while len(picked) < target_count and sigs:
        progressed = False
        for s in sigs:
            if len(picked) >= target_count:
                break
            arr = ann_by_sig[s]
            i = cursor[s]
            if i < len(arr):
                picked.append(arr[i])
                cursor[s] = i + 1
                progressed = True
            elif allow_replacement and arr:
                picked.append(rng.choice(arr))
                progressed = True
        if not progressed:
            break

    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotations_dir", type=str, default="docs_annotation/output")
    ap.add_argument("--docs_dir", type=str, default="")
    ap.add_argument("--out_dir", type=str, default="mock_query/queries")
    ap.add_argument("--templates_path", type=str, default="mock_query/templates_hr.json")
    ap.add_argument("--per_file_type", type=int, default=50, help="每种 file_type 生成的 query 数量（目标值）")
    ap.add_argument("--queries_per_doc", type=int, default=2, help="每个 doc 生成多少条 query（用于填充配额）")
    ap.add_argument("--seed", type=int, default=20260204)
    ap.add_argument("--ground_with_content", action="store_true", help="尝试读取文档文本以做 topic grounding")
    ap.add_argument("--allow_sample_with_replacement", action="store_true", help="某类文档不够时允许带放回采样")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    annotations_dir = Path(args.annotations_dir)
    docs_dir = Path(args.docs_dir) if args.docs_dir else None
    out_dir = Path(args.out_dir)
    templates_path = Path(args.templates_path)

    templates, topics_seed = load_templates(templates_path)
    annotations = load_annotations(annotations_dir)

    # 分组：file_type -> stressor_signature -> [annotations...]
    by_type_sig: Dict[str, Dict[str, List[JSONDict]]] = defaultdict(lambda: defaultdict(list))
    for a in annotations:
        ft = str(a.get("file_type")).lower()
        stressors = derive_stressors(a)
        sig = stressor_signature(stressors)
        by_type_sig[ft][sig].append(a)

    # 行为配比（可后续做成配置文件，这里给一个默认 mix）
    behavior_mix = {"answer": 0.75, "partial": 0.10, "refuse": 0.10, "ask_clarification": 0.05}

    out_dir.mkdir(parents=True, exist_ok=True)
    queries_path = out_dir / "queries.jsonl"
    stats_path = out_dir / "stats.json"
    manifest_path = out_dir / "manifest.json"

    dataset: List[JSONDict] = []

    # 为每个 file_type 生成 per_file_type 条 query
    for file_type, ann_by_sig in sorted(by_type_sig.items(), key=lambda x: x[0]):
        target_q = args.per_file_type
        # 估算需要多少 doc 才能产出足够 query
        target_docs = max(1, (target_q + args.queries_per_doc - 1) // args.queries_per_doc)
        picked_docs = round_robin_pick_docs(
            rng,
            ann_by_sig,
            target_count=target_docs,
            allow_replacement=args.allow_sample_with_replacement,
        )

        # 对每个 doc 生成 queries_per_doc 条（直到达到 target_q）
        for doc in picked_docs:
            if sum(1 for x in dataset if str(x["doc_annotation"].get("file_type")).lower() == file_type) >= target_q:
                break

            stressors = derive_stressors(doc)
            doc_id = str(doc.get("doc_id"))

            text = ""
            doc_title = doc_id
            if args.ground_with_content:
                fp = resolve_file_path(doc, docs_dir)
                if fp and fp.exists():
                    try:
                        text = try_extract_text_with_docparser(fp)
                    except Exception:
                        # 依赖缺失/解析失败时兜底：只做无文本生成
                        text = ""
                doc_title = extract_doc_title(text, fallback=doc_id)

            for _ in range(args.queries_per_doc):
                if sum(1 for x in dataset if str(x["doc_annotation"].get("file_type")).lower() == file_type) >= target_q:
                    break

                expected_behavior = pick_expected_behavior(rng, behavior_mix)
                tpl = select_template(
                    templates,
                    file_type=file_type,
                    stressors=stressors,
                    expected_behavior=expected_behavior,
                    rng=rng,
                )
                topic = choose_topic(text, topics_seed, rng)
                q = render_query(tpl, topic=topic, doc_title=doc_title, doc_id=doc_id)

                item: JSONDict = {
                    "id": "",  # 稍后统一编号
                    "query": q,
                    "domain": "hr",
                    "expected_behavior": expected_behavior,
                    "required_chunks": [],
                    "optional_chunks": [],
                    "forbidden_chunks": [],
                    "answer_constraints": build_answer_constraints(expected_behavior),
                    "doc_annotation": doc,
                    "stressors": stressors,
                    "generation": {
                        "template_id": tpl.id,
                        "category_key": file_type,
                        "stressor_signature": stressor_signature(stressors),
                        "seed": args.seed,
                        "ground_with_content": bool(args.ground_with_content),
                    },
                }
                dataset.append(item)

    # 编号（稳定、可复现）
    for i, item in enumerate(dataset, start=1):
        item["id"] = f"q_{i:06d}"

    # 输出 JSONL
    with queries_path.open("w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 统计
    c_type = Counter(str(x["doc_annotation"].get("file_type")).lower() for x in dataset)
    c_beh = Counter(x["expected_behavior"] for x in dataset)
    c_sig = Counter(x["generation"]["stressor_signature"] for x in dataset)
    c_stressor = Counter(s for x in dataset for s in x.get("stressors", []))

    stats = {
        "total": len(dataset),
        "by_file_type": dict(sorted(c_type.items(), key=lambda x: (-x[1], x[0]))),
        "by_expected_behavior": dict(sorted(c_beh.items(), key=lambda x: (-x[1], x[0]))),
        "top_stressor_signatures": c_sig.most_common(20),
        "top_stressors": c_stressor.most_common(30),
    }
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    # manifest（包含输出 hash，便于复现/对齐）
    out_hash = sha256(queries_path.read_bytes()).hexdigest()[:16]
    manifest = {
        "generated_at": int(time.time()),
        "seed": args.seed,
        "inputs": {
            "annotations_dir": str(annotations_dir),
            "docs_dir": str(docs_dir) if docs_dir else "",
            "templates_path": str(templates_path),
        },
        "params": {
            "per_file_type": args.per_file_type,
            "queries_per_doc": args.queries_per_doc,
            "ground_with_content": bool(args.ground_with_content),
            "allow_sample_with_replacement": bool(args.allow_sample_with_replacement),
        },
        "outputs": {
            "queries": str(queries_path),
            "stats": str(stats_path),
            "hash16": out_hash,
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(dataset)} queries to {queries_path}")
    print(f"Stats: {stats_path}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

