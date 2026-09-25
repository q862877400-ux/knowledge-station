"""术语桥（P1 第 2 步）的单元判据。

**这个文件管什么、不管什么**（别把它当"术语表对不对"的证明）：

* **管**：`TERM_ENTRY_RE` 的**行为边界**（收什么、拒什么、三个字段各是哪一段）、
  `merge_round_robin` 的**轮转语义**（那是 P1 全部收益的机制所在）、
  `topk_by_cos` 的**两条实现必须给出同一个答案**（numpy 那条只是加速等价物）。
* **不管**：术语表覆盖真库到什么程度。那件事由
  `scripts/measure-term-bridge.py` 扫真库量（实测 42,181 条），**不是**靠本文件的
  合成样例。本文件的样例是按**实测形态**手写的，**别把它读成"真库长这样"**。

⚠ `topk_by_cos` 那条是**判据**（不是普通用例）：numpy 路径与纯 Python 参照实现的
逐点一致是"加速没改变结论"的**唯一机械证据**。将来谁改了其中一条而没改另一条，
它会红。
"""
from __future__ import annotations

import json

import pytest

from src.core.retrieval.term_bridge import (
    TERM_ENTRY_RE, TermEntry, TermIndex, extract_term_entries, merge_round_robin,
    topk_by_cos,
)

# ── 样例（按实测形态手写：`编号 中文名 英文名 中文定义`）─────────────────────
REAL_SHAPE = "3.1 危险作业 special work 危险化学品……"


# ── TERM_ENTRY_RE 的行为边界 ───────────────────────────────────────────────
def test_term_entry_re_splits_number_name_english_and_definition():
    m = TERM_ENTRY_RE.match(REAL_SHAPE)
    assert m is not None
    assert m.group(1).strip() == "危险作业"
    assert m.group(2).strip() == "special work"


def test_term_entry_re_accepts_unnumbered_and_dotted_numbering():
    for text in ("危险作业 special work 定义正文",
                 "3.4.8 词典生产平台 dictionary production system 定义正文",
                 "3.1 危险作业 special work 定义正文"):
        m = TERM_ENTRY_RE.match(text)
        assert m is not None, text
        assert m.group(1).strip() in ("危险作业", "词典生产平台"), text


def test_term_entry_re_rejects_full_width_paren_numbering_and_that_is_measured():
    """全角括号编号（`（3）危险作业 …`）**收不下** —— 这是**有意的边界，不是洞**。

    我一度把这一条写成"应当接受"，跑出来是红的。**去真库量了**（探针
    `var/tmp/probe-term-re-numbering.py`，全库 522,021 条逐条跑）：
    把编号段放宽成 `（数字）` 后，命中条款 **48,524 条不变**、去重术语
    **42,181 个不变**、新增 **0 个**。
    ⇒ 这个库里的术语条款不用这种编号。**放宽不会多收一个术语，只会让正则更松**，
    所以保持拒绝，并把实测数字写在这里（免得下次又有人以为是漏的）。
    """
    assert TERM_ENTRY_RE.match("（3）危险作业 special work 定义正文") is None


def test_term_entry_re_rejects_rows_without_an_english_name():
    """没有英文名的行**不是**术语条款 —— 拒掉才不会把正文句子当成术语。"""
    assert TERM_ENTRY_RE.match("危险作业 是指在危险化学品……") is None
    assert TERM_ENTRY_RE.match("4.1 本章适用于下列各项要求") is None


def test_term_entry_re_requires_a_chinese_definition_after_the_english_name():
    """英文名后面必须还有中文 —— 否则只是一行英文标题。"""
    assert TERM_ENTRY_RE.match("危险作业 special work") is None


# ── merge_round_robin：P1 收益的机制本身 ───────────────────────────────────
def test_merge_round_robin_interleaves_rather_than_concatenates():
    """**这条是 P1 扇出收益的机制**：轮转必须让第二份的第一条**插在**第一份的第二条前面。

    顺序拼接（`list1 + list2`）时 top-1 术语的 20 条把返回位占满，后面选中的术语
    一条都进不了前 20（实测前 20：顺序 20.6% vs 轮转 29.4%，同一批、同样查询数）。
    """
    out = merge_round_robin([["a1", "a2", "a3"], ["b1", "b2"]])
    assert out == ["a1", "b1", "a2", "b2", "a3"]
    assert out.index("b1") < out.index("a2")


def test_merge_round_robin_dedups_keeping_first_occurrence():
    out = merge_round_robin([["a", "x"], ["x", "b"]])
    assert out == ["a", "x", "b"]


def test_merge_round_robin_tolerates_empty_and_missing_lists():
    assert merge_round_robin([]) == []
    assert merge_round_robin([[], []]) == []
    assert merge_round_robin([[], ["a"], ["b", "c"]]) == ["a", "b", "c"]


# ── topk_by_cos：加速实现必须与参照实现逐点一致（判据）────────────────────
def test_topk_by_cos_numpy_path_agrees_with_the_python_reference():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(20260925)
    vectors = rng.normal(size=(200, 32)).tolist()
    for q in rng.normal(size=(20, 32)).tolist():
        for k in (1, 5, 20):
            fast = topk_by_cos(q, vectors, k, use_numpy=True)
            ref = topk_by_cos(q, vectors, k, use_numpy=False)
            assert fast == ref, (k, fast[:3], ref[:3])


def test_topk_by_cos_ties_break_by_smallest_index_on_both_paths():
    """同分必须**按下标**定序，否则两条实现会在边界上给出不同答案。"""
    v = [1.0, 0.0, 0.0]
    vectors = [v, v, v, v]
    assert topk_by_cos(v, vectors, 2, use_numpy=True) == [0, 1]
    assert topk_by_cos(v, vectors, 2, use_numpy=False) == [0, 1]


def test_topk_by_cos_caps_k_at_the_number_of_candidates():
    vectors = [[1.0, 0.0], [0.0, 1.0]]
    assert sorted(topk_by_cos([1.0, 0.0], vectors, 99, use_numpy=False)) == [0, 1]


def test_topk_by_cos_zero_vector_is_not_a_crash():
    assert topk_by_cos([0.0, 0.0], [[0.0, 0.0], [1.0, 0.0]], 1, use_numpy=False) == [0]


# ── TermIndex：存取与缓存失效 ──────────────────────────────────────────────
def test_term_index_save_load_round_trip(tmp_path):
    idx = TermIndex(
        entries=[TermEntry(term="危险作业", english="special work",
                           clause_revision_id="c1", doc_id="d1", definition="定义正文")],
        vectors=[[0.1, 0.2]],
    )
    p = tmp_path / "idx.json"
    idx.save(p)
    back = TermIndex.load(p)
    assert back.entries == idx.entries
    assert back.vectors == idx.vectors


def test_term_index_select_returns_empty_without_vectors():
    idx = TermIndex(entries=[TermEntry("甲", "jia", "c", "d", "定义")], vectors=[])
    assert idx.select("随便问一句", k=3) == []


def test_term_index_matrix_cache_invalidates_when_the_candidate_set_changes():
    """候选集被收窄（`entries`/`vectors` 重新赋值）后，矩阵不许还是旧的那份。"""
    np = pytest.importorskip("numpy")
    idx = TermIndex(vectors=[[1.0, 0.0], [0.0, 1.0]])
    assert idx._matrix().shape == (2, 2)
    idx.vectors = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    assert idx._matrix().shape == (3, 2)


def test_term_index_matrix_is_normalised():
    np = pytest.importorskip("numpy")
    idx = TermIndex(vectors=[[3.0, 4.0]])
    assert np.allclose(idx._matrix(), [[0.6, 0.8]])


# ── extract_term_entries：同一术语只留第一条 ───────────────────────────────
def _fake_conn(rows):
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE clause_revision "
                 "(clause_revision_id TEXT, doc_id TEXT, content_text TEXT)")
    conn.executemany("INSERT INTO clause_revision VALUES (?,?,?)", rows)
    return conn


def test_extract_term_entries_keeps_only_the_first_clause_per_term():
    conn = _fake_conn([
        ("c1", "d1", "3.1 危险作业 special work 第一条定义"),
        ("c2", "d2", "3.1 危险作业 special work 某标准里的另一条定义"),
        ("c3", "d1", "3.2 动火作业 hot work 定义正文"),
    ])
    out = extract_term_entries(conn)
    assert [e.term for e in out] == ["危险作业", "动火作业"]
    assert out[0].clause_revision_id == "c1"
    assert out[0].doc_id == "d1"


def test_extract_term_entries_strips_wrapping_punctuation_and_folds_whitespace():
    conn = _fake_conn([("c1", "d1", "3.1 危险作业· special work 定义正文\n续行")])
    out = extract_term_entries(conn)
    assert out[0].term == "危险作业"
    assert "\n" not in out[0].definition


def test_extract_term_entries_skips_non_term_rows():
    conn = _fake_conn([("c1", "d1", "4.1 本章适用于下列各项要求")])
    assert extract_term_entries(conn) == []


# ── 缓存文件的口径（`scripts/measure-term-bridge.py` 依赖它）───────────────
def test_saved_cache_keeps_the_field_names_the_script_expects(tmp_path):
    """`measure-term-bridge.py` 按字段名读缓存；改名会让它**静默读空**（分母变 0）。"""
    idx = TermIndex(entries=[TermEntry("甲", "jia", "c1", "d1", "定义")], vectors=[[1.0]])
    p = tmp_path / "idx.json"
    idx.save(p)
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert set(raw) == {"entries", "vectors"}
    assert set(raw["entries"][0]) == {
        "term", "english", "clause_revision_id", "doc_id", "definition"}
