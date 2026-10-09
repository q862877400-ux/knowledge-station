"""benchmark-v2 构建器：对 `benchmark-171.jsonl` 做**轻清洗**（不重新生成问题、不重判）。

只做四件事（外部评估建议的"体检"口径）：
  1. 按票数分桶：3/3 PASS = 主结果；2/3（早期批次只记 2 票）= 保留但标记；
  2. 机械标记 **Gold 不唯一**：同一条定义标题在**别的文档**里也出现，或同 `content_hash`
     的条文字节级重复 ⇒ 正确答案不止一条，"没找到 gold"不等于"没答对"；
  3. 机械标记 **部分回答**：gold 是**分节标题**（有子条款）⇒ 一个问法要的答案可能跨子条款；
  4. 统计并落盘（唯一条款数 / 唯一文档数 / 类型分布 / 票型分布 / 移出样本与原因）。
  5. **（2026-10-09 T016 新增）标注 FR-005 的四个难度子集** ⇒ `v2.subset`
     （短条款 / 字面零重合 / 带标准号 / 普通；口径与出处逐条写在 `main()` 里，
     解释与边界见 `eval/recall-funnel/README.md` §五）。
  6. **（2026-10-09 T017 新增）标出"答案不在库内"的题** ⇒ `v2.answer_out_of_corpus`（FR-006）。
     ⚠ 原样是一句 `assert gold is not None` —— 那会把"换考卷"变成不可能，已改成记布尔字段。

⚠ 本脚本**只读**真库（URI `mode=ro`），不写库、不改源文件、不产生新考卷。
用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\build-v2.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent
BENCH = ROOT / "eval" / "reverse-benchmark" / "benchmark-171.jsonl"
VERDICTS = ROOT / "eval" / "reverse-benchmark" / "verdicts-raw.jsonl"
OUT_JSONL = HERE / "benchmark-v2.jsonl"
OUT_STATS = HERE / "benchmark-v2-stats.json"

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"


def ro_conn(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    from src.core.storage.sqlite_db import load_vec_extension
    load_vec_extension(conn)
    return conn


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def head_term(gold_text: str) -> str | None:
    """定义形态条文的**术语名**：条文正文第二行「术语名 英文名 定义…」的第一个词。"""
    lines = [l for l in (gold_text or "").splitlines() if l.strip()]
    if len(lines) < 2:
        return None
    t = lines[1].strip().split()
    if not t:
        return None
    term = t[0].strip()
    return term if len(term) >= 2 else None


def main() -> int:
    from src.core.text_utils import standard_key
    # FR-005 的"带标准号"子集必须与**通道 A 的真实触发条件**同一把尺子 ⇒ 直接借生产的两件：
    from src.core.retrieval.hybrid_engine import _STD_IN_QUERY_RE, _known_standard_keys

    items = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
    verd = {}
    if VERDICTS.exists():
        for l in VERDICTS.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            v = json.loads(l)
            verd[(v.get("q"), v.get("std"), str(v.get("no")))] = v

    conn = ro_conn(DB)
    # 标准号键 → 库里的标准号原文（比对用 standard_key，与全仓唯一口径一致）
    std_of_key = {standard_key(r[0]): r[0] for r in conn.execute("SELECT standard_no FROM doc_meta")}

    out_lines = []
    drop_reasons: list[dict] = []
    for it in items:
        votes = list(it.get("votes") or [])
        n_pass = sum(1 for v in votes if v == "PASS")
        n_fail = sum(1 for v in votes if v == "FAIL")
        scores = []
        if it.get("confidence"):
            scores.append(it["confidence"])

        stk = standard_key(it["gold_std"])
        std_no = std_of_key.get(stk)
        gold = conn.execute(
            "SELECT cr.clause_revision_id, cr.doc_id, cr.hierarchy_path, cr.content_hash,"
            " cr.content_text"
            " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
            " WHERE dm.standard_no=? AND cr.clause_number=?",
            (std_no, it["gold_clause"])).fetchone()
        # 2026-10-09（T016/T017）：原样是一句 `assert gold is not None`。
        # ⚠ 那句话把"换考卷"变成不可能：按 FR-006，**答案不在库内的题必须能被标出并排除**，
        #   而不是让构建器当场崩掉。⇒ 改成记一个布尔字段（`answer_out_of_corpus`），
        #   下游统计按它排除。本批 171 条实测**全部在库内** ⇒ 该字段全 False（不是没实现，
        #   是这批考卷本来就没有库外题；换考卷时它才会变 True）。
        answer_out_of_corpus = gold is None

        flags: list[str] = []
        flag_detail: dict[str, object] = {}

        # ── Gold 不唯一 (a)：同一条定义标题在**别的文档**里也出现 ──────────────
        term = head_term(it["gold_text"]) if it["kind"] == "定义" else None
        if term:
            pat = f"%{_like_escape(chr(10) + term + ' ')}%"
            n_doc = conn.execute(
                "SELECT COUNT(DISTINCT doc_id) FROM clause_revision"
                " WHERE content_text LIKE ? ESCAPE '\\'", (pat,)).fetchone()[0]
            if n_doc >= 2:
                flags.append("gold_multi_def")
                flag_detail["same_def_docs"] = n_doc
                flag_detail["term"] = term

        # ── Gold 不唯一 (b)：条文字节级重复（content_hash 相同）───────────────
        if gold is not None and gold["content_hash"]:
            n_dup = conn.execute(
                "SELECT COUNT(DISTINCT doc_id) FROM clause_revision WHERE content_hash=?",
                (gold["content_hash"],)).fetchone()[0]
            if n_dup >= 2:
                flags.append("gold_dup_text")
                flag_detail["dup_text_docs"] = n_dup

        # ── 部分回答：gold 是分节标题（存在子条款）────────────────────────────
        # ⚠ `hierarchy_path` 的语义**实测**（2026-10-06）：它存的是**祖先链、不含自己** ——
        #   `3.1 → '3'`；`5.6.1.12 → '5 > 5.6 > 5.6.1'`；章号（`3`）为 NULL。
        #   ⇒ gold 的**完整路径** = (hp + ' > ' + 号) 或（hp 为空时）号本身；
        #     直接子条款的 hp **恰好等于**该完整路径，更深的后代以 `完整路径 + ' > '` 开头。
        #   ⚠ 本判据改过两版（都留痕）：先按 `'5.2.%'` 点号前缀（空转，错）；
        #     再按 `hp + ' > %'`（**匹配到的是兄弟节点**，把 153 条判成"有子条款"、
        #     单条子条款数一度报到 20,928）。现在这版才是语义正确的。
        #   这条是**备注**，不是移出主结果的理由（命中仍成立，只是"答案可能跨子条款"）。
        if gold is not None:
            hp = (gold["hierarchy_path"] or "").strip()
            num = str(it["gold_clause"]).strip()
            gold_path = f"{hp} > {num}" if hp else num
            esc = _like_escape(gold_path)
            n_child = conn.execute(
                "SELECT COUNT(*) FROM clause_revision"
                " WHERE doc_id = ?"
                "   AND (hierarchy_path = ?"
                "        OR hierarchy_path LIKE ? ESCAPE '\\')",
                (gold["doc_id"], gold_path, f"{esc} > %")).fetchone()[0]
            flag_detail["gold_path"] = gold_path
            if n_child > 0:
                flags.append("has_subclauses")
                flag_detail["n_subclauses"] = n_child

        # ── FR-005 难度子集（2026-10-09 T016 补）──────────────────────────────
        # 口径与出处**逐条写死在代码里**，别处只链接（见 eval/recall-funnel/README.md §五）：
        #   · `short_clause`      gold 条款正文 < 40 字（取自 `clause_revision.content_text`，
        #                         与 spec.md 边界条"短条款占 36.8%（<40 字）"同一口径）。
        #   · `zero_overlap_char` 提问与 gold 条文**没有 ≥2 字的公共子串** ——
        #                         与 `docs/research/lay-phrasing-scaleup-test.md` L80 那张表
        #                         "与定义条款有 ≥2 字重合"的**字符级**判据同口径（53.0% 那一档）。
        #                         直接取 `overlap`（生成时算的最长公共子串长度）⇒ `< 2` 即零重合。
        #   · `has_standard_no`   提问里出现标准号**形态**（`_STD_IN_QUERY_RE`，生产同一把正则）。
        #   · `has_standard_no_verified` 再经 `_known_standard_keys` 在 `doc_meta` 里验过
        #                         （**与通道 A 的真实触发条件同口径**：库里没有就不筛）。
        # `label` = 互斥分区，优先级按 spec.md 列举顺序（短条款 → 字面零重合 → 带标准号 → 普通）；
        # "普通" 只有在互斥分区下才有意义（否则 = 全体）⇒ 四个子集必须互斥。
        _std_form = _STD_IN_QUERY_RE.findall(it["query"])
        _std_verified = bool(_std_form) and bool(
            _known_standard_keys({standard_key(s) for s in _std_form}, doc_stds))
        _short = gold is not None and len(gold["content_text"] or "") < 40
        _zero = (it.get("overlap") or 0) < 2
        subset = {
            "short_clause": _short,
            "zero_overlap_char": _zero,
            "has_standard_no": bool(_std_form),
            "has_standard_no_verified": _std_verified,
            "label": ("短条款" if _short else
                      "字面零重合" if _zero else
                      "带标准号" if _std_verified else "普通"),
            "gold_text_len": len(gold["content_text"] or "") if gold is not None else None,
        }

        bucket = "keep" if (n_pass == 3 and len(votes) == 3) else "split"
        if bucket == "split":
            v = verd.get((it["query"], it["gold_std"], str(it["gold_clause"]))) or {}
            main_reasons = Counter()
            for d in (v.get("detail") or []):
                if d.get("结论") == "FAIL":
                    main_reasons[d.get("主因") or "未写主因"] += 1
            drop_reasons.append({
                "i": it["i"], "votes": votes, "n_pass": n_pass, "n_fail": n_fail,
                "kind": it["kind"], "confidence": it.get("confidence"),
                "fail_main_reasons": dict(main_reasons),
                "query": it["query"], "gold_std": it["gold_std"],
                "gold_clause": it["gold_clause"],
            })

        row = dict(it)
        row["v2"] = {
            "bucket": bucket,
            "n_pass": n_pass, "n_fail": n_fail, "n_votes": len(votes),
            "flags": flags,
            "flag_detail": flag_detail,
            "gold_cr_id": gold["clause_revision_id"] if gold is not None else None,
            "gold_doc_id": gold["doc_id"] if gold is not None else None,
            # FR-006：答案不在库内的题（换考卷时才会出现）—— 统计侧按它排除
            "answer_out_of_corpus": answer_out_of_corpus,
            # FR-005：难度子集标签
            "subset": subset,
        }
        out_lines.append(row)

    OUT_JSONL.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out_lines), encoding="utf-8")

    # ── 统计 ────────────────────────────────────────────────────────────────
    main_rows = [r for r in out_lines if r["v2"]["bucket"] == "keep"]
    #: 只有"gold 在库里不唯一"才把条目移出主结果 —— 那是**量错**（没找到 gold 不等于没答对）；
    #: `has_subclauses` 只是备注（命中照样成立），不移出。
    _EXCLUDE = {"gold_multi_def", "gold_dup_text"}
    headline = [r for r in main_rows if not (_EXCLUDE & set(r["v2"]["flags"]))]
    flagged = [r for r in main_rows if _EXCLUDE & set(r["v2"]["flags"])]

    def _dist(rows, key):
        return dict(Counter(r[key] for r in rows))

    per_gold = defaultdict(list)
    for r in out_lines:
        per_gold[(r["gold_std"], str(r["gold_clause"]))].append(r["i"])
    repeated = {f"{k[0]} {k[1]}": v for k, v in per_gold.items() if len(v) > 1}

    stats = {
        "meta": {
            "source": "eval/reverse-benchmark/benchmark-171.jsonl",
            "db": str(DB),
            "n_input": len(items),
            "note": "只做轻清洗：不重新生成问题、不重判；gold 在库里 (标准号,条款号) 唯一已实测",
        },
        "counts": {
            "all": len(out_lines),
            "bucket_keep_3of3": len(main_rows),
            "bucket_split": len(out_lines) - len(main_rows),
            "headline": len(headline),
            "headline_excluded_gold_not_unique": len(flagged),
            "flagged_has_subclauses": sum(1 for r in out_lines if "has_subclauses" in r["v2"]["flags"]),
            # FR-006：答案不在库内的题（本批 0 条 —— 字段存在的意义是换考卷时不裸奔）
            "answer_out_of_corpus": sum(1 for r in out_lines if r["v2"]["answer_out_of_corpus"]),
        },
        "vote_shapes": {str(k): v for k, v in Counter(
            tuple(r.get("votes") or []) for r in out_lines).items()},
        "kind": {k: _dist(out_lines, "kind").get(k, 0) for k in ("定义", "要求")},
        "kind_main_clean": {k: _dist(headline, "kind").get(k, 0) for k in ("定义", "要求")},
        "register": _dist(out_lines, "register"),
        "confidence": _dist(out_lines, "confidence"),
        "uniqueness": {
            "unique_gold_clause": len(per_gold),
            "unique_gold_doc": len({r["v2"]["gold_doc_id"] for r in out_lines}),
            "gold_clause_with_multi_query": len(repeated),
            "top_repeated": dict(sorted(repeated.items(), key=lambda kv: -len(kv[1]))[:10]),
        },
        "flags": {
            "counts": dict(Counter(f for r in out_lines for f in r["v2"]["flags"])),
            "in_main_3of3": dict(Counter(f for r in main_rows for f in r["v2"]["flags"])),
        },
        # FR-005 难度子集（2026-10-09 T016 新增）。`label` 是**互斥分区**（优先级见 main 里注释）；
        # 四个 `markers` 是**各标记的独立命中条数**（可重叠）⇒ 想换优先级的人能自己重算。
        "subset": {
            "priority": ["短条款", "字面零重合", "带标准号", "普通"],
            "partition_all": dict(Counter(r["v2"]["subset"]["label"] for r in out_lines)),
            "partition_headline": dict(Counter(r["v2"]["subset"]["label"] for r in headline)),
            "markers_all": {
                "short_clause": sum(1 for r in out_lines if r["v2"]["subset"]["short_clause"]),
                "zero_overlap_char": sum(1 for r in out_lines if r["v2"]["subset"]["zero_overlap_char"]),
                "has_standard_no": sum(1 for r in out_lines if r["v2"]["subset"]["has_standard_no"]),
                "has_standard_no_verified": sum(
                    1 for r in out_lines if r["v2"]["subset"]["has_standard_no_verified"]),
            },
            "note": "⚠ 本批考卷对四个难度子集几乎不承载：带标准号 0 条、短条款 8 条；"
                    "字面零重合 121 条（字符级口径）。原因见 eval/recall-funnel/README.md §五。",
        },
        "dropped_from_main": {
            "n": len(drop_reasons),
            "reason": "非 3/3 一致（2/3 或只记 2 票）⇒ 移出主结果，样本保留在 benchmark-v2.jsonl",
            "fail_main_reasons": dict(Counter(
                m for d in drop_reasons for m, c in d["fail_main_reasons"].items() for _ in range(c))),
            "samples": sorted(drop_reasons, key=lambda d: d["n_pass"])[:12],
        },
    }
    OUT_STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT_JSONL}\n已写 {OUT_STATS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
