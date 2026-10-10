"""测试：数据质量闸门（spec 005 T102/T111）。

**为什么这些用例必须存在**：`gate-quality.py` 是四项静默缺陷判据的**唯一数字源**。
若它的判据没牙（恒真、空过面），那么"质量全绿"又会变成一句空话 ——
这正是本模块此前 297 个提交、0 次独立复核留下的病。

每条用例都对着一个**具体缺陷形态**，不是对着"输出格式"：
- 答复为空 ⇒ `xz-lasa` 那种"条数正常、字段存在、内容是空"的记录
- 内容重复 ⇒ id 不同但 `(question, answer)` 相同（旧闸门只比 id，看不见）
- 时间倒置 ⇒ `answered_at < asked_at`（旧闸门无任何字段语义判据）
- 棘轮 ⇒ **率**不恶化（不是绝对条数：并行采集会持续加数据）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "recon"))

import importlib.util                                            # noqa: E402


def _load_gate():
    """按路径加载 `recon/gate-quality.py`（文件名带连字符，不能直接 import）。"""
    p = Path(__file__).resolve().parent.parent / "recon" / "gate-quality.py"
    spec = importlib.util.spec_from_file_location("gate_quality", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gq = _load_gate()


def _write(tmp_path: Path, recs: list) -> None:
    (tmp_path / "x.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in recs), encoding="utf-8")


def _rec(i, q="q", a="a", asked="2026-01-02 00:00:00", answered="2026-01-01 00:00:00",
         src="s1", label=None):
    ex = {}
    if label:
        ex["msg_type_norm"] = label
    return {"source": src, "id": str(i), "question": q, "answer": a,
            "asked_at": asked, "answered_at": answered, "extra": ex}


class _Data:
    """把 `gate-quality.DATA` 指到临时目录。"""

    def __init__(self, tmp_path: Path):
        self.tmp = tmp_path
        self.old = None

    def __enter__(self):
        self.old = gq.DATA
        gq.DATA = self.tmp
        return self

    def __exit__(self, *a):
        gq.DATA = self.old
        return False


# ---------------------------------------------------------------- 判据 1：答复为空

def test_empty_answer_is_detected(tmp_path):
    """**答复为空必须被数出来** —— `xz-lasa` 那种「条数正常、内容是空」。"""
    _write(tmp_path, [_rec(1, a=""), _rec(2, a="有内容"), _rec(3, a="   ")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["total"] == 3
    assert s["answer_empty"] == 2, f"应为 2（空串 + 纯空白），实际 {s['answer_empty']}"


def test_single_source_with_all_empty_answers_fails(tmp_path):
    """**单个源大面积为空要指名道姓** —— 只报全库平均会被大源稀释掉。"""
    recs = [_rec(i, a="", src="bad-src") for i in range(10)]
    recs += [_rec(100 + i, a="ok", src="big-src") for i in range(990)]
    _write(tmp_path, recs)
    with _Data(tmp_path):
        s = gq.collect()
        checks = dict((n, ok) for n, ok, _d in gq.verdicts(s))
    # 全库空答复率只有 1%（低于 MAX_EMPTY_ANSWER_RATE=0.5%? 不，是 1% > 0.5%，所以也红）
    assert s["answer_empty"] == 10
    assert checks["无单源答复大面积为空"] is False, "bad-src 100% 为空，必须判红"


# ---------------------------------------------------------------- 判据 2：内容重复

def test_content_duplicate_with_different_ids_is_detected(tmp_path):
    """**id 不同但内容相同必须被数出来** —— 旧闸门只比 id，这一项完全看不见。"""
    _write(tmp_path, [
        _rec(1, q="同一个问题", a="同一个答复"),
        _rec(2, q="同一个问题", a="同一个答复"),   # 内容相同、id 不同
        _rec(3, q="别的问题", a="别的答复"),
    ])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["content_dups"] == 1, f"应数出 1 条冗余，实际 {s['content_dups']}"
    assert s["content_dup_groups"] == 1


def test_whitespace_differences_do_not_hide_duplicates(tmp_path):
    """归一化必须吃掉空白 —— 否则「加个换行」就能绕过重复检测。"""
    _write(tmp_path, [
        _rec(1, q="问 题", a="答 复"),
        _rec(2, q="问题", a="答复"),
    ])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["content_dups"] == 1, "去掉空白后是同一内容，必须判重"


def test_distinct_content_is_not_flagged(tmp_path):
    """**反向用例**：不同内容不得被误判成重复（判据不能恒真）。"""
    _write(tmp_path, [_rec(1, q="问题一", a="答复一"), _rec(2, q="问题二", a="答复二")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["content_dups"] == 0


# ---------------------------------------------------------------- 判据 3：时间倒置

def test_time_inversion_is_detected(tmp_path):
    """**答复早于提问必须被数出来** —— `ln-8890` 实测 7,807 条如此。"""
    _write(tmp_path, [
        _rec(1, asked="2026-05-01 00:00:00", answered="2026-01-01 00:00:00"),  # 倒置
        _rec(2, asked="2026-01-01 00:00:00", answered="2026-05-01 00:00:00"),  # 正常
    ])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 1, f"应数出 1 条倒置，实际 {s['inverted']}"


def test_missing_dates_are_not_counted_as_inverted(tmp_path):
    """缺字段**不算**倒置 —— 否则「没数据」会被误报成「数据错」。"""
    _write(tmp_path, [
        {"source": "s", "id": "1", "question": "q", "answer": "a",
         "asked_at": None, "answered_at": None, "extra": {}},
    ])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 0


# ---------------------------------------------------------------- 判据 4：标签口径

def test_label_coverage_counts_only_clean_key(tmp_path):
    """覆盖率只认 `msg_type_norm`（干净 9 分类），**不认原始脏 `msg_type`**。

    这是 spec 005 T105 的统一口径：此前 `health.py`（窄）与
    `label-coverage.py`（宽）对同一份数据报出 99.2 vs 100.0 两个数。
    """
    _write(tmp_path, [
        _rec(1, label="咨询"),
        {"source": "s", "id": "2", "question": "q", "answer": "a",
         "asked_at": None, "answered_at": None,
         "extra": {"msg_type": "省直公积金"}},          # 脏值，不算
        {"source": "s", "id": "3", "question": "q", "answer": "a",
         "asked_at": None, "answered_at": None, "extra": {}},
    ])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["labeled"] == 1, f"只应认 1 条干净标签，实际 {s['labeled']}"
    assert abs(s["coverage"] - 100 / 3) < 0.01


# ---------------------------------------------------------------- 棘轮

def test_ratchet_compares_rate_not_absolute_count(tmp_path, monkeypatch):
    """**棘轮比的是率不是条数** —— 并行采集会持续加数据。

    实测教训：第一版比绝对条数，接进闸门后立刻假红（8470 → 8475），
    而那不是回归，是另一个 Agent 的采集进程在加数据。
    """
    _write(tmp_path, [_rec(i) for i in range(100)])
    with _Data(tmp_path):
        s = gq.collect()
    monkeypatch.setattr(gq, "_load_baseline", lambda: {
        "answer_empty": 1, "content_dups": 0, "time_inverted": 0, "total": 100})
    # 语料翻倍、缺陷按同比例翻倍 ⇒ 率不变 ⇒ **不得报红**
    s2 = dict(s, total=200, answer_empty=2, content_dups=0, inverted=0)
    checks = {n: ok for n, ok, _d in gq.ratchet(s2)}
    assert checks["棘轮·答复为空率不恶化"] is True, "率没变，不该报红"


def test_ratchet_flags_a_real_rate_regression(tmp_path, monkeypatch):
    """**反向用例**：率真的变坏必须报红（棘轮不能恒真）。"""
    _write(tmp_path, [_rec(i) for i in range(100)])
    with _Data(tmp_path):
        s = gq.collect()
    monkeypatch.setattr(gq, "_load_baseline", lambda: {
        "answer_empty": 1, "content_dups": 0, "time_inverted": 0, "total": 100})
    s2 = dict(s, total=100, answer_empty=50, content_dups=0, inverted=0)
    checks = {n: ok for n, ok, _d in gq.ratchet(s2)}
    assert checks["棘轮·答复为空率不恶化"] is False, "率从 1000 涨到 50000/10万，必须报红"


def test_ratchet_is_silent_without_baseline(monkeypatch):
    """没有基线时不判红（否则第一跑就红，没人会去建基线）。"""
    monkeypatch.setattr(gq, "_load_baseline", lambda: {})
    assert gq.ratchet({"answer_empty": 0, "content_dups": 0, "inverted": 0, "total": 1}) == []


# ---------------------------------------------------------------- 纯 ASCII 出口

def test_quiet_output_is_pure_ascii(tmp_path, capsys):
    """`--quiet` 是**给闸门读的**，必须纯 ASCII（GBK 控制台会崩）。"""
    _write(tmp_path, [_rec(1, q="中文问题", a="中文答复")])
    with _Data(tmp_path):
        gq.DATA = tmp_path
        rc = gq.main.__wrapped__() if hasattr(gq.main, "__wrapped__") else None
    # 直接测 ascii_kv 出口，不依赖 main 的 argv
    import io
    from common import ascii_kv
    buf = io.StringIO()
    ascii_kv({"TOTAL": 1, "NOTE": "中文"}, stream=buf)
    buf.getvalue().encode("ascii")            # 非 ASCII 会在这里抛
