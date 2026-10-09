"""exp-17 · 可续跑的「影子向量表」重建脚本（**不动生产**）。

用途：把 E4 那条**唯一已量出大收益**的方向（换嵌入模型 `Qwen/Qwen3-Embedding-0.6B`
＋ 查询侧官方指令前缀）变成**可执行的重建**，而**不改生产代码、不写真库**。

设计要点（每一条都对应一个"很容易踩回去"的坑）：

1. **只读真库**：源库一律 `file:...?mode=ro`。脚本**没有**任何写源库的路径。
2. **影子表写在独立库文件里**（`--out`），不复制整库（真库 3.1 GB ⇒ 复制一次又慢又占盘）。
   表名默认 `clause_vec_qwen`，DDL 与生产 `clause_vec` **同形**（`vec0(id TEXT PRIMARY KEY,
   doc_id TEXT, embedding FLOAT[512])`）—— E4 第三轮已量出升到 1024 维只有 +1.67pt ⇒ **维度保持 512，
   不改维度**。
   ⚠ 2026-10-09（spec 003）：**加了 `doc_id` 元数据列** —— 生产 `clause_vec` 也加了它
   （「按目录范围提问」的向量通道要靠它下推）。影子表必须跟着加，否则**换表之后**
   范围提问在向量通道上会**静默返回空**。
3. **断点续跑按 `rowid` 游标 + 库内 checkpoint 表**：checkpoint 与数据**同事务提交**
   ⇒ 进程被强杀时，最后一个未提交的批次整批回滚、checkpoint 也停在上一批，**不会错位**。
   （`exp-4/01-embed-qwen.py` 用"把已算 id 全读进内存做集合差"来续跑；那在 66 万行上要多读
   66 万行 + 占几十 MB，且**目标集一变就静默错**。本脚本改成游标 + 口径守卫。）
4. **口径守卫**：`model_id` / `out_dim` / `text_formula_sha` / `limit` 四个字段写进 checkpoint；
   续跑时与本次参数不一致就**当场报错**——防止"两个不同模型/两种文本公式算出来的向量混在一张表里"
   （那种表看起来行数对、KNN 也能跑，**但语义是坏的，且没有任何读数能看出来**）。
5. **文本公式与生产逐字一致**：`f"{title or ''}\n{content_text[:512]}"`
   （出处 `src/core/storage/clause_repo.py` 的 `insert_clauses_in_txn` / `_reindex_clause_indexes`）。
   本脚本**不 import** 生产函数（那会连带拉起 pydantic/配置），而是**把公式抄成一个常量**并
   用 `text_formula_sha()` 钉住；`tests/test_embedding_rebuild_resume.py` 再拿生产源码比对
   （抄错了会被判据抓住）。
6. **向量存储格式**：实测（`var/tmp/exp-17/probe.py`）sqlite-vec 把 `json.dumps(list)` 与
   `array('f').tobytes()` **存成完全相同的 2048 字节 float32**（逐字节相等）⇒ 本脚本用
   **blob 路径**（快得多），与生产 `_serialize_vec`（json）**逐字节等价**，不引入新变量。
7. **`--fake-embed`**：用「id+文本」的 sha256 派生确定性向量（不加载模型）⇒ 断点续跑/幂等
   这类**管道**性质可以秒级验证，不必等 GPU。

用法：
    # 小样验证（假嵌入，秒级）
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-17-embedding-production-plan\\rebuild-shadow.py \\
        --out var/tmp/exp-17/shadow.db --limit 300 --fake-embed

    # 真模型小样
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-17-embedding-production-plan\\rebuild-shadow.py \\
        --out var/tmp/exp-17/shadow-real.db --limit 64

    # 全量（约 1 小时；一轮跑不完 ⇒ 被强杀后**原样重跑同一条命令**即可续）
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-17-embedding-production-plan\\rebuild-shadow.py \\
        --out <影子库路径>
"""
from __future__ import annotations

import argparse
import array
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: 默认源库（真库，**只读**）
DEFAULT_SOURCE = Path(os.environ.get("APPDATA", "")) / "KnowledgeStation" / "database" / "knowledge.db"

MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
OUT_DIM = 512          # E4 第三轮已量出 1024 维只 +1.67pt ⇒ 保持 512，schema 不动
TABLE = "clause_vec_qwen"
CKPT_TABLE = "_shadow_ckpt"
DEFAULT_BATCH = 16     # E4 实测最快（224.9 条/s）
DEFAULT_COMMIT_EVERY = 100   # 单位 = 批

#: Qwen3-Embedding 官方检索指令（英文默认），**逐字照抄**；自造中文版即第二个变量 ⇒ 不做。
#: 只在**查询侧**用；条文侧（本脚本）**不加**。
INSTRUCT_PREFIX = (
    "Instruct: Given a web search query, retrieve relevant passages that answer the query\n"
    "Query: "
)


# --------------------------------------------------------------------------- #
# 纯函数（判据测这些）
# --------------------------------------------------------------------------- #
def display_text(title: str | None, body: str | None) -> str:
    """生产同款条文文本公式，**一字不改**。

    出处：`src/core/storage/clause_repo.py` 的 `insert_clauses_in_txn`（批量入库）与
    `_reindex_clause_indexes`（补丁重算）两处都写 `f"{...title or ''}\\n{...content_text[:512]}"`。
    两处不一致 = 同一批语料两种向量 ⇒ 判据 `test_display_text_matches_production_formula`。
    """
    return f"{title or ''}\n{(body or '')[:512]}"


def text_formula_sha() -> str:
    """把"文本公式"变成可比较的指纹（防止两种公式的向量混进同一张表）。"""
    probe = [
        ("", ""),
        ("标题", "正文" * 400),
        (None, None),
        ("t", "x" * 511),
        ("t", "x" * 512),
        ("t", "x" * 513),
    ]
    payload = json.dumps([display_text(t, b) for t, b in probe], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ckpt_guard(stored: dict, want: dict) -> None:
    """续跑口径守卫：四个字段任一不一致即**抛错**（不是警告）。

    为什么必须硬失败：一张表里混进两个模型的向量，行数、维度、KNN 全都"看起来正常"，
    **没有任何下游读数能发现**。唯一能发现的地方就是这里。
    """
    keys = ("model_id", "out_dim", "text_formula_sha", "limit")
    bad = [k for k in keys if str(stored.get(k)) != str(want.get(k))]
    if bad:
        raise SystemExit(
            "⛔ 影子库口径与本次参数不一致，拒绝续跑（防止两种向量混进一张表）：\n"
            + "\n".join(f"   {k}: 库里={stored.get(k)!r} 本次={want.get(k)!r}" for k in bad)
            + "\n   ⇒ 换一个 --out 路径，或删掉这个影子库重跑。"
        )


def fake_vector(cid: str, text: str, dim: int = OUT_DIM) -> list[float]:
    """确定性假向量（sha256 派生）——只验管道，不验语义。"""
    import math
    seed = hashlib.sha256(f"{cid}\x00{text}".encode("utf-8")).digest()
    vals = []
    i = 0
    while len(vals) < dim:
        blk = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        for j in range(0, 32, 4):
            u = int.from_bytes(blk[j:j + 4], "big") / 2**32
            vals.append(u * 2.0 - 1.0)
        i += 1
    vals = vals[:dim]
    n = math.sqrt(sum(v * v for v in vals)) or 1.0
    return [v / n for v in vals]


def real_embedder_factory(model_id: str = MODEL_ID, out_dim: int = OUT_DIM):
    """返回 `embed(list[str]) -> list[list[float]]`（真模型，GPU fp16，逐字复刻 E4 口径）。

    复刻点（与 `exp-4/01-embed-qwen.py` 一致）：
      · `AutoTokenizer(..., padding_side="left")` + `AutoModel(..., dtype=torch.float16).to("cuda").eval()`
      · `padding=True, truncation=True, max_length=512`
      · **取 `last_hidden_state[:, -1]`（最后一个 token = EOS 池化）**
      · 原生 1024 维 ⇒ `[:, :out_dim]` 截断后**重新 L2 归一化**（MRL）
    """
    import torch
    import torch.nn.functional as Fn
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id, padding_side="left")
    model = AutoModel.from_pretrained(model_id, dtype=torch.float16).to("cuda").eval()

    def _embed(texts: list[str]) -> list[list[float]]:
        with torch.no_grad():
            enc = tok(texts, padding=True, truncation=True, max_length=512,
                      return_tensors="pt").to("cuda")
            out = model(**enc)
            emb = Fn.normalize(out.last_hidden_state[:, -1][:, :out_dim], p=2, dim=1)
            return [[float(x) for x in row] for row in emb.float().cpu().numpy()]

    return _embed


def fake_embedder_factory(dim: int = OUT_DIM):
    def _embed(texts: list[str]) -> list[list[float]]:
        # 与真嵌入同形：需要 id 才能派生 ⇒ 由调用方把 id 塞进 texts 的第一段（见 run()）
        return [fake_vector(t.split("\x01", 1)[0], t.split("\x01", 1)[1], dim) for t in texts]
    return _embed


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def _open_shadow(out: Path, dim: int) -> sqlite3.Connection:
    from src.core.storage.sqlite_db import load_vec_extension

    out.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(out))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=120000")
    if not load_vec_extension(conn):
        raise SystemExit("⛔ sqlite-vec 加载失败")
    conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS {TABLE} USING vec0("
                 f"clause_revision_id TEXT PRIMARY KEY, doc_id TEXT, embedding FLOAT[{dim}])")
    conn.execute(f"CREATE TABLE IF NOT EXISTS {CKPT_TABLE} (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn


def _read_ckpt(conn: sqlite3.Connection) -> dict:
    return {k: v for k, v in conn.execute(f"SELECT key, value FROM {CKPT_TABLE}")}


def _write_ckpt(conn: sqlite3.Connection, kv: dict) -> None:
    conn.executemany(f"INSERT OR REPLACE INTO {CKPT_TABLE}(key, value) VALUES (?,?)",
                     [(k, str(v)) for k, v in kv.items()])


def _source_counts(src: sqlite3.Connection) -> tuple[int, int]:
    """返回 (非空正文条数, 全表条数)。"""
    total = src.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    nonempty = src.execute(
        "SELECT COUNT(*) FROM clause_revision WHERE trim(coalesce(content_text,'')) <> ''"
    ).fetchone()[0]
    return nonempty, total


def run(source: Path, out: Path, *, limit: int | None = None, batch: int = DEFAULT_BATCH,
        commit_every: int = DEFAULT_COMMIT_EVERY, stop_after_batches: int | None = None,
        embedder=None, model_id: str = MODEL_ID, out_dim: int = OUT_DIM,
        log=print) -> dict:
    """执行（或续跑）重建。返回读数字典。

    `stop_after_batches` 是**测试钩子**：跑满 N 批就**干净退出**（checkpoint 已提交），
    用来复现"进程被杀在批次边界"。
    """
    from src.core.storage.sqlite_db import load_vec_extension

    if not source.exists():
        raise SystemExit(f"⛔ 源库不存在：{source}")
    src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    load_vec_extension(src)      # 源库侧也需要（读 clause_vec 时）；只读连接同样能加载
    nonempty, total = _source_counts(src)

    conn = _open_shadow(out, out_dim)
    want = {"model_id": model_id, "out_dim": out_dim, "text_formula_sha": text_formula_sha(),
            "limit": "" if limit is None else limit}
    stored = _read_ckpt(conn)
    resumed = bool(stored)
    if resumed:
        ckpt_guard(stored, want)
        last_rowid = int(stored.get("last_rowid", 0))
        done = int(stored.get("done", 0))
        log(f"[exp-17] 续跑：checkpoint last_rowid={last_rowid} done={done}")
    else:
        last_rowid, done = 0, 0

    target = nonempty if limit is None else min(limit, nonempty)
    rows = src.execute(
        # ⚠ doc_id 放在**末尾**（spec 003）：这样 r[2]/r[3] 仍是 title/content_text，
        #   不会因为加一列而让下面的下标集体位移。
        "SELECT rowid, clause_revision_id, title, content_text, doc_id FROM clause_revision"
        " WHERE trim(coalesce(content_text,'')) <> '' AND rowid > ? ORDER BY rowid LIMIT ?",
        (last_rowid, max(0, target - done))).fetchall()
    log(f"[exp-17] 源库 clause_revision={total}（非空正文 {nonempty}）；目标 {target}；"
        f"已算 {done}；本段待算 {len(rows)}；模型 {model_id}；维度 {out_dim}")

    if not rows:
        n = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
        log(f"[exp-17] 无待算；影子表 {n} 行（目标 {target}）"
            f"{' ✅' if n == target else ' ⛔ 不一致'}")
        conn.close(); src.close()
        return {"rows_written": 0, "shadow_rows": n, "target": target, "resumed": resumed,
                "batches": 0, "elapsed_s": 0.0, "rate": None}

    if embedder is None:
        embedder = real_embedder_factory(model_id, out_dim)
    # 假嵌入需要 id 参与派生 ⇒ 统一把 "id\x01文本" 传进去，真嵌入侧只取文本
    is_fake = bool(getattr(embedder, "_is_fake", False))

    t0 = time.perf_counter()
    written = 0
    batches = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        if is_fake:
            embs = embedder([f"{r[1]}\x01{display_text(r[2], r[3])}" for r in chunk])
        else:
            embs = embedder([display_text(r[2], r[3]) for r in chunk])
        # ⚠ 必须带 doc_id（spec 003）：影子表要"与生产同形"，否则将来换表后
        #   「按目录范围提问」在向量通道上会静默返回空。
        payload = [(r[1], r[4], array.array("f", e).tobytes()) for r, e in zip(chunk, embs)]
        conn.executemany(f"INSERT OR REPLACE INTO {TABLE}"
                         " (clause_revision_id, doc_id, embedding) VALUES (?, ?, ?)", payload)
        written += len(chunk)
        done += len(chunk)
        batches += 1
        if batches % commit_every == 0 or batches == 1 or i + batch >= len(rows):
            # ★ checkpoint 与数据**同事务**提交 ⇒ 强杀不会错位
            _write_ckpt(conn, {**want, "last_rowid": chunk[-1][0], "done": done,
                               "target": target, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            conn.commit()
        if stop_after_batches is not None and batches >= stop_after_batches:
            log(f"[exp-17] --stop-after-batches {stop_after_batches} 命中 ⇒ 干净退出（可续跑）")
            break
        if batches % 200 == 0:
            el = time.perf_counter() - t0
            log(f"[exp-17] {done}/{target}  {el:.0f}s  {written / el:.1f} 条/s")

    n = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
    el = time.perf_counter() - t0
    log(f"[exp-17] 本段写入 {written}；影子表 {n} / 目标 {target}"
        f"{' ✅' if n == target else '（未完成，可原样重跑续跑）'}；用时 {el:.1f}s")
    conn.close(); src.close()
    return {"rows_written": written, "shadow_rows": n, "target": target, "resumed": resumed,
            "batches": batches, "elapsed_s": round(el, 3),
            "rate": round(written / el, 1) if el > 0 else None}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="可续跑影子向量表重建（不动生产）")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    ap.add_argument("--commit-every", type=int, default=DEFAULT_COMMIT_EVERY,
                    help="每多少**批**提交一次 checkpoint（默认 100）")
    ap.add_argument("--stop-after-batches", type=int, default=None,
                    help="测试钩子：跑满 N 批即干净退出（checkpoint 已提交）")
    ap.add_argument("--fake-embed", action="store_true", help="用确定性假向量（不加载模型）")
    ap.add_argument("--model-id", default=MODEL_ID)
    ap.add_argument("--out-dim", type=int, default=OUT_DIM)
    a = ap.parse_args(argv)

    emb = None
    if a.fake_embed:
        emb = fake_embedder_factory(a.out_dim)
        emb._is_fake = True
    r = run(a.source, a.out, limit=a.limit, batch=a.batch, commit_every=a.commit_every,
            stop_after_batches=a.stop_after_batches, embedder=emb,
            model_id=a.model_id, out_dim=a.out_dim)
    print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
