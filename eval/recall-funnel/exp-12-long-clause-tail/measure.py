"""P0·0.10 只读量化：长条款的尾巴到底漏了什么、影响面多大。

口径（**跑之前写死**；改口径 = 改结论，必须重跑全部读数）
================================================================

背景（已登记事实，本次不重证）
  · 送进嵌入的文本 = `f"{title}\\n{content_text[:512]}"`（`clause_repo.py:285` / `:426`）
    ⇒ **代码层按"512 个字符"截断**（不是按 token）。
  · 模型窗口 512 token（`bge-small-zh-v1.5` HF config）。
  · 总纲 P0·0.10 已实测：全文 vs 只取前 800 字的嵌入余弦**恰好 1.0000** ⇒ 尾巴不进向量。
  · `clause_fts` 索引的是**全文**（`_seg(content_text)`）⇒ 按字找仍能找到尾巴上的词。

本尺子要回答的三个问题（只读真库，不写库、不改生产代码、零网络）
  1. **规模**：现库（663,634 条）里有多少条"尾巴被截掉"？给出
     字符口径（>512 字）与 **token 口径**（用真实 bge 分词器数，替掉总纲那句"1 汉字≈1 token 是推断"）。
     并判"代码截断点（512 字）"与"模型窗口（512 token）"哪个是**更紧的约束**。
  2. **尾巴上"只有尾巴才有的词"有多少**：对每条被截的条款，
     head = content_text[:512]、tail = content_text[512:]，各自用**生产分词器**
     （`text_utils.segment_for_fts` = jieba cut_for_search）分词：
       · `tail_only` = tail 词集 − head 词集 − title 词集
       · 这正是"向量路（只看 head）完全看不到、FTS 路（看全文）看得到"的那批词。
     统计：有 ≥1 个 tail_only 词的条款数、tail_only 词数分布、全库 tail_only 去重词总数。
  3. **对召回的实际影响面**：与考卷交叉（`benchmark-v2.jsonl`，120 主结果 / 171 全量）。
     对每条金标条款：把 query 也用生产分词器切词，看 query 的词**落在 head 还是 tail**：
       · `q_hit_head`  = query 词 ∩ head 词集（含 title）
       · `q_hit_tail_only` = query 词 ∩ tail_only
     ⇒ `q_hit_head 为空 且 q_hit_tail_only 非空` 的题 = **向量路对这条 gold 没有任何字面抓手**
       （字面信号只存在于尾巴）—— 这就是"尾巴丢失"能伤到的题的上界。
     再用 `funnel-per-query.jsonl` 的通道名次交叉：长 gold 条款 vs 短 gold 条款的
     **向量通道名次**分布（看向量路是不是真的在长条款上更差）。

口径边界（如实说，别当全量）
  · head/tail 按**字符**切（512），一个词可能正好被切断 ⇒ 边界词可能被算进 head 或 tail；
    这是**已知的切分噪声**，量级用"边界 8 字符内"的词数单独报一次。
  · `tail_only` 用的是**集合差**，只回答"这个词在 head 里出现过没有"，不回答出现几次。
  · 影响面是**上界**：字面信号只在尾巴 ≠ 一定召回失败（语义路可能仍够得着）。
  · 考卷 120/171 条是**抽样**，不是全部。

输出：`result.json`（机器可读）+ 控制台摘要。
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

DB_PATH = os.path.expandvars(r"%APPDATA%\KnowledgeStation\database\knowledge.db")
MODEL_DIR = Path(os.path.expandvars(
    r"%APPDATA%\KnowledgeStation\models\models--Qdrant--bge-small-zh-v1.5\snapshots"))
BENCH = REPO / "eval" / "recall-funnel" / "benchmark-v2.jsonl"
FUNNEL = REPO / "eval" / "recall-funnel" / "funnel-per-query.jsonl"
OUT = Path(__file__).resolve().parent / "result.json"

#: 代码层截断点（字符）—— 与 `clause_repo.py` 的 `content_text[:512]` 逐字对应。
HEAD_CHARS = 512
#: 模型窗口（token）。
MODEL_WINDOW = 512


def _load_tokenizer():
    """真实 bge-small-zh-v1.5 分词器（本地 HF snapshot，零网络）。"""
    from tokenizers import Tokenizer
    cands = list(MODEL_DIR.glob("*/tokenizer.json"))
    if not cands:
        return None, None
    tok = Tokenizer.from_file(str(cands[0]))
    return tok, str(cands[0].parent.name)


def _tokens(text: str) -> list[str]:
    """生产分词器（与 `clause_fts` 建索引口径同源）。"""
    from src.core.text_utils import segment_for_fts
    return [w for w in segment_for_fts(text).split() if w]


# ---------- 纯函数（供 tests/test_long_clause_tail_ruler.py 直接单测） ----------

def split_head_tail(text: str, head_chars: int = HEAD_CHARS) -> tuple[str, str]:
    """按**字符**切 head/tail —— 与 `clause_repo.py` 的 `content_text[:512]` 同口径。"""
    return text[:head_chars], text[head_chars:]


def tail_only_words(text: str, title: str, head_chars: int = HEAD_CHARS) -> set[str]:
    """tail 里"head+title 完全没出现过"的词集（= 向量路看不到、FTS 看得到的那批）。"""
    head, tail = split_head_tail(text, head_chars)
    hset = set(_tokens(head)) | set(_tokens(title or ""))
    return set(_tokens(tail)) - hset


def token_drop_partition(full_tokens: int, head_tokens: int,
                         window: int = MODEL_WINDOW) -> tuple[int, int]:
    """把"被丢掉的 token"拆成两段：`(gain, residual)`。

    · `gain` = 只去掉**代码层 [:512] 字符上限**、模型仍截到 `window` token 时能白捡的量；
    · `residual` = 即使去掉代码上限、被模型窗口挡掉的量。
    当 `head_tokens <= window`（实测 99.95% 的情形）时满足
    `gain + residual == full_tokens - head_tokens`（供测试钉住）。
    """
    gain = max(0, min(full_tokens, window) - head_tokens)
    residual = max(0, full_tokens - window)
    return gain, residual


def main() -> int:
    from src.core.text_utils import segment_for_fts  # noqa: F401  (提前导入，避免计时污染)

    tok, snap = _load_tokenizer()
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    result: dict = {
        "generated_at": None,
        "db_path": DB_PATH,
        "head_chars": HEAD_CHARS,
        "model_window": MODEL_WINDOW,
        "tokenizer_snapshot": snap,
        "scale": {},
        "tail_words": {},
        "benchmark_impact": {},
        "funnel_cross": {},
        "boundaries": {},
    }

    # ---------- 1. 规模 ----------
    total = con.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    scale = {"clause_revision_total": total}
    for lim in (512, 768, 1000, 2000):
        n = con.execute(
            "SELECT COUNT(*) FROM clause_revision WHERE LENGTH(content_text) > ?",
            (lim,)).fetchone()[0]
        scale[f"chars_gt_{lim}"] = n
        scale[f"chars_gt_{lim}_pct"] = round(100.0 * n / total, 4)
    scale["max_chars"] = con.execute(
        "SELECT MAX(LENGTH(content_text)) FROM clause_revision").fetchone()[0]
    scale["total_content_chars"] = con.execute(
        "SELECT SUM(LENGTH(content_text)) FROM clause_revision").fetchone()[0]

    # token 口径：对"可能超过 512 token"的条款（用字符上限 900 兜）逐条数
    long_rows = con.execute(
        "SELECT clause_revision_id, title, content_text FROM clause_revision "
        "WHERE LENGTH(content_text) > ?", (HEAD_CHARS,)).fetchall()
    scale["n_long_rows_fetched"] = len(long_rows)

    if tok is not None:
        # 抽样上限 4000 条（按 id 稳定排序，可复跑），避免全量 13k 条分词器调用过慢
        import random
        sample = sorted(long_rows, key=lambda r: r["clause_revision_id"])
        random.Random(20261009).shuffle(sample)
        sample = sample[:4000]
        gt_win = 0
        gt_win_head = 0  # head+title 单独也超窗口
        tok_lens = []
        tok_head_lens = []
        for r in sample:
            text = f"{r['title'] or ''}\n{r['content_text']}"
            n_tok = len(tok.encode(text).ids)
            head = f"{r['title'] or ''}\n{r['content_text'][:HEAD_CHARS]}"
            n_head_tok = len(tok.encode(head).ids)
            tok_lens.append(n_tok)
            tok_head_lens.append(n_head_tok)
            if n_tok > MODEL_WINDOW:
                gt_win += 1
            if n_head_tok > MODEL_WINDOW:
                gt_win_head += 1
        scale["token_sample_n"] = len(sample)
        scale["token_sample_gt_window"] = gt_win
        scale["token_sample_gt_window_pct"] = round(100.0 * gt_win / len(sample), 3)
        scale["token_sample_head_gt_window"] = gt_win_head
        scale["token_sample_head_gt_window_pct"] = round(
            100.0 * gt_win_head / len(sample), 3)
        scale["token_len_min"] = min(tok_lens)
        scale["token_len_median"] = sorted(tok_lens)[len(tok_lens) // 2]
        scale["token_len_max"] = max(tok_lens)
        scale["token_head_len_median"] = sorted(tok_head_lens)[len(tok_head_lens) // 2]
        dropped = sorted(a - b for a, b in zip(tok_lens, tok_head_lens))
        scale["token_tail_dropped_median"] = dropped[len(dropped) // 2]
        scale["token_tail_dropped_max"] = dropped[-1]
        # 若**只去掉代码层 [:512] 字符上限**（模型仍截到 512 token）：能白捡多少、还剩多少丢
        gain = sorted(token_drop_partition(a, b)[0]
                      for a, b in zip(tok_lens, tok_head_lens))
        resid = sorted(token_drop_partition(a, b)[1]
                       for a, b in zip(tok_lens, tok_head_lens))
        scale["token_gain_if_code_cap_removed_median"] = gain[len(gain) // 2]
        scale["token_gain_if_code_cap_removed_max"] = gain[-1]
        scale["token_residual_loss_after_cap_removed_median"] = resid[len(resid) // 2]
        scale["token_residual_loss_after_cap_removed_max"] = resid[-1]
        # 总量（可相加，比中位数更能说明"去掉代码上限能挽回多少"）
        scale["token_dropped_sum"] = sum(dropped)
        scale["token_gain_if_cap_removed_sum"] = sum(gain)
        scale["token_residual_loss_sum"] = sum(resid)
        scale["token_gain_share_pct"] = round(100.0 * sum(gain) / max(sum(dropped), 1), 2)
    result["scale"] = scale

    # ---------- 2. 尾巴上"只有尾巴才有的词" ----------
    n_with_tail_only = 0
    n_with_tail_only_ge5 = 0
    tail_only_counts: list[int] = []
    union_tail_only: set[str] = set()
    boundary_words = 0          # 切分点前后 8 字符内产生的词（切分噪声代理量）
    head_chars_lost_total = 0
    for r in long_rows:
        title = r["title"] or ""
        text = r["content_text"]
        head, tail = split_head_tail(text)
        t_only = tail_only_words(text, title)
        tail_only_counts.append(len(t_only))
        if t_only:
            n_with_tail_only += 1
            union_tail_only |= t_only
            if len(t_only) >= 5:
                n_with_tail_only_ge5 += 1
        head_chars_lost_total += len(tail)
        # 边界噪声：head 尾 8 字符 + tail 头 8 字符各自切出的词
        boundary_words += len(set(_tokens(head[-8:])) | set(_tokens(tail[:8])))

    n_long = len(long_rows)
    # 例子里剔掉标点/纯符号/单字，只留中文词（≥2 字）—— 原始 union 前 40 个全是标点，没有可读性
    cjk_words = sorted(w for w in union_tail_only
                       if len(w) >= 2 and any("\u4e00" <= ch <= "\u9fff" for ch in w))
    tail_words = {
        "n_long_clauses": n_long,
        "n_with_ge1_tail_only": n_with_tail_only,
        "n_with_ge1_tail_only_pct": round(100.0 * n_with_tail_only / max(n_long, 1), 3),
        "n_with_ge5_tail_only": n_with_tail_only_ge5,
        "tail_only_per_clause_median": (
            sorted(tail_only_counts)[len(tail_only_counts) // 2] if tail_only_counts else 0),
        "tail_only_per_clause_max": max(tail_only_counts) if tail_only_counts else 0,
        "tail_only_union_distinct_words": len(union_tail_only),
        "tail_only_union_cjk_words_ge2": len(cjk_words),
        "tail_chars_total_lost_to_vector": head_chars_lost_total,
        "boundary_words_total": boundary_words,
        "examples_cjk": cjk_words[:40],
    }
    result["tail_words"] = tail_words

    # ---------- 3. 对召回的实际影响面（与考卷交叉） ----------
    bench = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
    # 只取主结果 120（bucket==keep 且 flags ∩ {gold_multi_def, gold_dup_text} == ∅），与全仓口径一致
    keep_flags = {"gold_multi_def", "gold_dup_text"}
    headline = [b for b in bench
                if b["v2"]["bucket"] == "keep"
                and not (set(b["v2"]["flags"]) & keep_flags)]

    def clause_of(crid: str):
        return con.execute(
            "SELECT clause_revision_id, title, content_text FROM clause_revision "
            "WHERE clause_revision_id=?", (crid,)).fetchone()

    def impact_for(items, label):
        n = len(items)
        n_long_gold = 0
        n_q_head_hit = 0
        n_q_tail_only_only = 0      # 字面信号只在尾巴（head 零命中、tail_only 非空）
        n_q_no_lexical = 0          # head/tail 都没有 query 词（纯语义题）
        rows = []
        for b in items:
            crid = b["v2"]["gold_cr_id"]
            row = clause_of(crid)
            if row is None:
                continue
            text = row["content_text"] or ""
            title = row["title"] or ""
            is_long = len(text) > HEAD_CHARS
            if is_long:
                n_long_gold += 1
            head = text[:HEAD_CHARS]
            tail = text[HEAD_CHARS:]
            hset = set(_tokens(head)) | set(_tokens(title))
            tset = set(_tokens(tail))
            t_only = tset - hset
            qset = set(_tokens(b["query"]))
            q_head = qset & hset
            q_tail_only = qset & t_only
            if q_head:
                n_q_head_hit += 1
            elif q_tail_only:
                n_q_tail_only_only += 1
            else:
                n_q_no_lexical += 1
            rows.append({
                "i": b["i"], "is_long": is_long, "len": len(text),
                "q_hit_head": len(q_head), "q_hit_tail_only": len(q_tail_only),
            })
        return {
            "label": label, "n": n,
            "n_long_gold": n_long_gold,
            "n_long_gold_pct": round(100.0 * n_long_gold / max(n, 1), 3),
            "n_q_head_hit": n_q_head_hit,
            "n_q_tail_only_only": n_q_tail_only_only,
            "n_q_no_lexical": n_q_no_lexical,
            "rows": rows,
        }

    # 金标条款自身的长度分布（解释"为什么影响面是 0"）
    gold_lens = []
    for b in bench:
        row = clause_of(b["v2"]["gold_cr_id"])
        if row is not None:
            gold_lens.append(len(row["content_text"] or ""))
    gl = sorted(gold_lens)
    result["gold_clause_lengths"] = {
        "n": len(gl),
        "min": gl[0] if gl else None,
        "median": gl[len(gl) // 2] if gl else None,
        "p90": gl[int(0.9 * (len(gl) - 1))] if gl else None,
        "max": gl[-1] if gl else None,
        "n_gt_512": sum(1 for x in gl if x > HEAD_CHARS),
        "n_gt_256": sum(1 for x in gl if x > 256),
    }

    result["benchmark_impact"] = {
        "headline120": impact_for(headline, "headline120"),
        "all171": impact_for(bench, "all171"),
    }

    # ---------- 4. 与漏斗通道名次交叉（向量路在长条款上是否更差） ----------
    if FUNNEL.exists():
        funnel = {json.loads(l)["i"]: json.loads(l)
                  for l in FUNNEL.read_text(encoding="utf-8").splitlines() if l.strip()}
        short_ranks, long_ranks = [], []
        for b in headline:
            f = funnel.get(b["i"])
            if not f:
                continue
            vec = f.get("channels", {}).get("vec", {})
            rank = vec.get("deep_gold_rank")
            crid = b["v2"]["gold_cr_id"]
            row = clause_of(crid)
            if row is None:
                continue
            is_long = len(row["content_text"] or "") > HEAD_CHARS
            if rank is None:
                continue
            (long_ranks if is_long else short_ranks).append(rank)

        def stats(xs):
            if not xs:
                return {"n": 0}
            s = sorted(xs)
            return {"n": len(xs), "median": s[len(s) // 2],
                    "p90": s[int(0.9 * (len(s) - 1))], "max": s[-1]}

        result["funnel_cross"] = {
            "vec_deep_rank_short_gold": stats(short_ranks),
            "vec_deep_rank_long_gold": stats(long_ranks),
            "note": "deep_gold_rank = 向量通道 @1000 里 gold 的名次；越小越好",
        }

    con.close()
    import datetime
    result["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k != "benchmark_impact"}, ensure_ascii=False, indent=2)[:4000])
    bi = result["benchmark_impact"]
    for k in ("headline120", "all171"):
        d = dict(bi[k]); d.pop("rows", None)
        print(k, json.dumps(d, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
