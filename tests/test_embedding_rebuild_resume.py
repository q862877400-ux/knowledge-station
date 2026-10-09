# -*- coding: utf-8 -*-
"""exp-17 影子向量表重建脚本（`eval/recall-funnel/exp-17-embedding-production-plan/rebuild-shadow.py`）的单测。

**为什么必须测**（每条判据都对应一个"看起来对、其实是坏"的失败模式）：

1. **文本公式必须与生产逐字一致**。公式抄错（比如少一个 `\\n`、把 `[:512]` 写成 `[:500]`）会让
   影子表的向量与生产不是同一个东西 —— 而**行数、维度、KNN 全都正常**，下游读数看不出来。
   判据 `test_display_text_matches_production_formula`（含 511/512/513 的截断边界）+ 拿
   `src/core/storage/clause_repo.py` 的**生产源码**做静态锚点。
2. **口径守卫必须硬失败**（`model_id` / `out_dim` / `text_formula_sha` / `limit`）。一张表里混进
   两个模型或两种公式的向量，是**唯一没有任何下游读数能发现**的坏法。判据
   `test_ckpt_guard_*`。
3. **checkpoint 必须与数据同事务**。否则强杀会留下"数据多算了一批、游标还停在上一批"
   ⇒ 续跑时**重算一批**（幂等所以不致命）或更糟：游标超前后漏算一批（**致命且不可见**）。
   可观测的不变量 = `ckpt.done == COUNT(clause_vec_qwen)`。判据
   `test_checkpoint_never_drifts_from_data`。
4. **续跑与一次跑完必须逐行相同**（不是"行数相同"）。判据
   `test_resume_is_row_identical_to_one_shot`。
5. **幂等**：对已完成的库原样重跑不许重算（浪费 GPU）也不许改字节。判据
   `test_rerun_is_idempotent`。
6. **假向量必须确定性 + 归一化**（它是 T1/T2/T3 的仪器；它一变，那三项就失去意义）。
   判据 `test_fake_vector_is_deterministic_and_normalized`。
7. **★ 指令前缀是 Qwen3 官方原串，不许被换成自造中文前缀**。`exp-13` 已实测"自造领域前缀"
   **显著变差**（−6.67pt，p=0.0215）⇒ 这条锚点是**防回归**，不是装饰。判据
   `test_instruct_prefix_is_the_official_string`。
8. **★ 换表不需要改 schema**：影子表与生产 `clause_vec` 同为 `FLOAT[512]`（E4 第三轮已量出
   升到 1024 维只有 +1.67pt ⇒ 保持 512）。判据 `test_shadow_dim_matches_production_schema`
   —— 它同时钉住 `schema.sql` 里的 `FLOAT[512]`：**生产若升维，这条会红**（那是好事）。

⚠ 本文件**不加载真模型、不碰真库**（源库用 `tmp_path` 里现造的小库）⇒ 跑得动、也不受
`conftest.py` 那两个 autouse fixture 影响。
"""
from __future__ import annotations

import importlib.util
import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "eval" / "recall-funnel" / "exp-17-embedding-production-plan" / "rebuild-shadow.py"
CLAUSE_REPO = REPO / "src" / "core" / "storage" / "clause_repo.py"
SCHEMA = REPO / "src" / "core" / "storage" / "schema.sql"


def _load():
    spec = importlib.util.spec_from_file_location("rebuild_shadow_under_test", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


RS = _load()


# --------------------------------------------------------------------------- #
# 1. 文本公式 = 生产口径
# --------------------------------------------------------------------------- #
def test_display_text_matches_production_formula():
    assert RS.display_text(None, None) == "\n"
    assert RS.display_text("", "") == "\n"
    assert RS.display_text("t", "") == "t\n"
    # 截断边界：511 / 512 / 513 —— 写错成 [:500] 或 [:1024] 会在这里红
    assert RS.display_text("", "x" * 511) == "\n" + "x" * 511
    assert RS.display_text("", "x" * 512) == "\n" + "x" * 512
    assert RS.display_text("", "x" * 513) == "\n" + "x" * 512      # 第 513 个字符被切掉
    assert len(RS.display_text("t", "y" * 4000)) == 1 + 1 + 512
    # 标题**不截断**（生产也只截正文）
    assert RS.display_text("z" * 900, "b") == "z" * 900 + "\n" + "b"


def test_production_source_still_has_the_same_formula():
    """静态锚点：生产源码里必须仍有 `title or ''` + `content_text[:512]` 的 f-string。

    生产改了公式而本脚本没跟 ⇒ 这条红（那是好事）；比它更糟的是**没人发现**。
    """
    src = CLAUSE_REPO.read_text(encoding="utf-8")
    hits = re.findall(r'f"\{[a-z_]*\.?title or \'\'\}\\n\{[a-z_]*\.?content_text\[:512\]\}"', src)
    assert len(hits) >= 2, f"生产条文文本公式的锚点变了（找到 {len(hits)} 处，期望 ≥2）：{hits}"


def test_text_formula_sha_is_stable_and_sensitive():
    assert RS.text_formula_sha() == RS.text_formula_sha()
    assert len(RS.text_formula_sha()) == 64
    # 换一种公式 ⇒ 指纹必须不同（否则这个"守卫"是装饰）
    alt = [RS.display_text(t, (b or "")[:500] if b else b) for t, b in
           [("", ""), ("标题", "正文" * 400), (None, None), ("t", "x" * 511),
            ("t", "x" * 512), ("t", "x" * 513)]]
    import hashlib
    alt_sha = hashlib.sha256(json.dumps(alt, ensure_ascii=False).encode("utf-8")).hexdigest()
    assert alt_sha != RS.text_formula_sha()


# --------------------------------------------------------------------------- #
# 2. 口径守卫
# --------------------------------------------------------------------------- #
def test_ckpt_guard_allows_matching():
    want = {"model_id": RS.MODEL_ID, "out_dim": RS.OUT_DIM,
            "text_formula_sha": RS.text_formula_sha(), "limit": 300}
    RS.ckpt_guard(dict(want), dict(want))          # 不抛


@pytest.mark.parametrize("key,value", [
    ("model_id", "BAAI/bge-small-zh-v1.5"),
    ("out_dim", 1024),
    ("text_formula_sha", "0" * 64),
    ("limit", 400),
])
def test_ckpt_guard_rejects_each_mismatch(key, value):
    want = {"model_id": RS.MODEL_ID, "out_dim": RS.OUT_DIM,
            "text_formula_sha": RS.text_formula_sha(), "limit": 300}
    stored = dict(want)
    stored[key] = value
    with pytest.raises(SystemExit):
        RS.ckpt_guard(stored, want)


# --------------------------------------------------------------------------- #
# 3~6. 端到端（小库 + 假嵌入）
# --------------------------------------------------------------------------- #
def _make_source(path: Path, n: int = 50) -> None:
    c = sqlite3.connect(str(path))
    c.execute("CREATE TABLE clause_revision (clause_revision_id TEXT PRIMARY KEY,"
              " title TEXT, content_text TEXT)")
    rows = []
    for i in range(n):
        cid = f"clrev_test_{i:04d}"
        # 混入 None / 空正文 / 超 512 字，覆盖真实数据的三种形态
        title = None if i % 7 == 0 else f"标题{i}"
        body = "" if i % 11 == 0 else ("正文" * (i % 3 + 1)) + ("尾巴" * (i * 13))
        rows.append((cid, title, body))
    c.executemany("INSERT INTO clause_revision VALUES (?,?,?)", rows)
    c.commit()
    c.close()


def _fake(mod):
    e = mod.fake_embedder_factory()
    e._is_fake = True
    return e


def _rows(db: Path) -> dict:
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    assert load_vec_extension(c)
    try:
        return {r[0]: r[1] for r in c.execute("SELECT clause_revision_id, embedding FROM clause_vec_qwen")}
    finally:
        c.close()


def test_fake_vector_is_deterministic_and_normalized():
    import math
    a = RS.fake_vector("id1", "文本", 512)
    b = RS.fake_vector("id1", "文本", 512)
    c = RS.fake_vector("id2", "文本", 512)
    assert a == b and a != c and len(a) == 512
    assert abs(math.sqrt(sum(x * x for x in a)) - 1.0) < 1e-12


def test_resume_is_row_identical_to_one_shot(tmp_path):
    src = tmp_path / "src.db"
    _make_source(src, 50)
    one, two = tmp_path / "one.db", tmp_path / "two.db"

    RS.run(src, one, batch=4, commit_every=2, embedder=_fake(RS))
    RS.run(src, two, batch=4, commit_every=2, stop_after_batches=3, embedder=_fake(RS))
    partial = _rows(two)
    assert 0 < len(partial) < 45, "中断后应当只落了一部分（否则这项没验到东西）"
    r = RS.run(src, two, batch=4, commit_every=2, embedder=_fake(RS))

    r1, r2 = _rows(one), _rows(two)
    # 50 条里有 5 条正文为空（i % 11 == 0）⇒ 与生产同款 `trim(coalesce(content_text,''))<>''` 过滤后 45 条
    assert len(r1) == len(r2) == 45
    assert r1 == r2, "续跑与一次跑完必须**逐行**相同（不是只比行数）"
    # ★ 空正文必须被**排除**（不是"凑够 45 条"）：去掉过滤条件会让取样整体前移而**行数照样是 45**
    assert set(r1) == {f"clrev_test_{i:04d}" for i in range(50) if i % 11 != 0}, \
        "影子表里混进了正文为空的条款 ⇒ 取样没复刻生产的 `trim(coalesce(content_text,''))<>''`"
    # ★ 续跑只许补算缺口：多算 = 游标读错（幂等会掩盖它 ⇒ 必须单独钉住）
    assert r["rows_written"] == 45 - len(partial), "续跑重算了已完成的条 ⇒ 游标（last_rowid）读错了"


def _open(db: Path):
    """打开影子库（**必须加载 vec0 扩展**，否则连 `COUNT(*)` 都报 `no such module`）。"""
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    assert load_vec_extension(c)
    return c


def test_checkpoint_never_drifts_from_data(tmp_path):
    """`ckpt.done` 必须恒等于影子表行数 —— 这是"checkpoint 与数据同事务"的可观测不变量。"""
    src = tmp_path / "src.db"
    _make_source(src, 30)
    out = tmp_path / "o.db"
    RS.run(src, out, batch=4, commit_every=3, stop_after_batches=2, embedder=_fake(RS))

    c = _open(out)
    kv = dict(c.execute("SELECT key, value FROM _shadow_ckpt"))
    n = c.execute("SELECT COUNT(*) FROM clause_vec_qwen").fetchone()[0]
    c.close()
    assert int(kv["done"]) == n, f"checkpoint done={kv['done']} 与影子表 {n} 行不一致 ⇒ 强杀会错位"
    assert int(kv["last_rowid"]) > 0


def test_rerun_is_idempotent(tmp_path):
    src = tmp_path / "src.db"
    _make_source(src, 30)
    out = tmp_path / "o.db"
    RS.run(src, out, batch=4, commit_every=3, embedder=_fake(RS))
    before = _rows(out)
    r = RS.run(src, out, batch=4, commit_every=3, embedder=_fake(RS))
    after = _rows(out)
    assert r["rows_written"] == 0, "已完成的库不该重算"
    assert before == after


def test_ckpt_records_all_guard_keys(tmp_path):
    src = tmp_path / "src.db"
    _make_source(src, 12)
    out = tmp_path / "o.db"
    RS.run(src, out, limit=12, batch=4, commit_every=1, embedder=_fake(RS))
    c = _open(out)
    kv = dict(c.execute("SELECT key, value FROM _shadow_ckpt"))
    c.close()
    for k in ("model_id", "out_dim", "text_formula_sha", "limit", "last_rowid", "done", "target"):
        assert k in kv, f"checkpoint 缺字段 {k}"


# --------------------------------------------------------------------------- #
# 7~8. 静态锚点
# --------------------------------------------------------------------------- #
def test_instruct_prefix_is_the_official_string():
    """官方原串，逐字。⚠ `exp-13` 已实测"自造领域前缀"显著变差（−6.67pt，p=0.0215）⇒ 防回归。"""
    assert RS.INSTRUCT_PREFIX == (
        "Instruct: Given a web search query, retrieve relevant passages that answer the query\n"
        "Query: ")
    assert RS.INSTRUCT_PREFIX.count("\n") == 1
    assert not any("\u4e00" <= ch <= "\u9fff" for ch in RS.INSTRUCT_PREFIX), \
        "前缀里出现中文 ⇒ 像是被换成了自造前缀"


def test_shadow_dim_matches_production_schema():
    """影子表维度必须 = 生产 `clause_vec` 的维度 ⇒ 换表**不需要改 schema**。

    生产若升维（`FLOAT[512]` → 别的），这条会红 —— 那时必须同步改 `OUT_DIM` 并重跑 E4 那一格。
    """
    sql = SCHEMA.read_text(encoding="utf-8")
    m = re.search(r"CREATE VIRTUAL TABLE IF NOT EXISTS clause_vec USING vec0\("
                  r"\s*clause_revision_id TEXT PRIMARY KEY,\s*embedding FLOAT\[(\d+)\]", sql)
    assert m, "schema.sql 里 clause_vec 的 DDL 形状变了"
    assert int(m.group(1)) == RS.OUT_DIM == 512
    assert RS.TABLE == "clause_vec_qwen" and RS.CKPT_TABLE == "_shadow_ckpt"


def test_ckpt_and_data_are_committed_in_the_same_transaction():
    """**静态锚点**：提交块里 `_write_ckpt(...)` 必须**先于**唯一的 `conn.commit()`。

    为什么只能静态测：把 checkpoint 与数据分成两次提交，**只在"两次提交之间被强杀"时才出错**
    （表现 = 数据多了一批、游标停在上一批 ⇒ 下次续跑**重算一批**；幂等所以不会错数据，
    但若反过来把游标写超了就会**漏算且不可见**）。运行期测不出这个窗口，只能钉住代码结构。
    """
    src = SCRIPT.read_text(encoding="utf-8")
    start = src.index("if batches % commit_every == 0")
    end = src.index("if stop_after_batches is not None")
    block = src[start:end]
    i_ckpt = block.index("_write_ckpt(conn,")
    i_commit = block.index("conn.commit()")
    assert i_ckpt < i_commit, "checkpoint 写在提交之后 ⇒ 强杀窗口里数据与游标会错位"
    assert block.count("conn.commit()") == 1, \
        "提交块里出现了多个 conn.commit() ⇒ 数据与 checkpoint 可能被拆成两次提交"


def test_module_has_no_write_path_to_source():
    """只读承诺的机械检查：脚本源码里不许出现对 `--source` 的写语句。"""
    src = SCRIPT.read_text(encoding="utf-8")
    assert "mode=ro" in src
    for bad in ("INSERT INTO clause_revision", "UPDATE clause_revision", "DELETE FROM clause_revision"):
        assert bad not in src, f"脚本里出现了写源库的语句：{bad}"
