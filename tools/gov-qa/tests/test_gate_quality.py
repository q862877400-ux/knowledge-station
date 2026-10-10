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
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # tools/gov-qa
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "recon"))

import importlib.util                                            # noqa: E402

SCRIPT = ROOT / "recon" / "gate-quality.py"


def _python() -> str:
    """解释器路径。

    ⚠ **不要硬编码 `../../.venv/Scripts/python.exe`**（独立复核发现 9）：
    提取树（`git worktree`）里 `.venv` 被 gitignore ⇒ 那个路径不存在
    ⇒ 用例在**任何提取树/CI 上都会红**（复核实测 FileNotFoundError）。
    ⇒ 优先用 `sys.executable`（正在跑本用例的那个解释器，必然是好的）。
    """
    return sys.executable


PY = _python()


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


def test_date_only_answered_at_same_day_is_not_inverted(tmp_path):
    """**同一天、`answered_at` 只精确到天 ⇒ 不算倒置**（2026-10-10 第 3 次修）。

    实测 1,517 条"倒置"里 **329 条（21.7%）** 是这种：
    `asked_at='2025-05-27 13:57:05'` vs `answered_at='2025-05-27'`（**同一天**）。
    解析后 `answered_at` 落在当天 00:00，永远早于 13:57 ⇒ 被判倒置，
    但**它们是同一天**。

    ⇒ 判据：**`answered_at` 只精确到天就只比到天**。
    谁改回"一律比到秒"，本用例必红。
    """
    _write(tmp_path, [_rec(1, asked="2025-05-27 13:57:05", answered="2025-05-27")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 0, "同一天、答复只精确到天，不算倒置"


def test_date_only_answered_at_across_days_IS_inverted(tmp_path):
    """**反向用例**：`answered_at` 是纯日期但**跨天更早** ⇒ 仍须判倒置。

    （不能因为"只比到天"就把真倒置也放过。）
    """
    _write(tmp_path, [_rec(1, asked="2025-05-27 13:57:05", answered="2025-05-20")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 1, "答复日期早于提问日期 7 天，必须判倒置"


def test_full_timestamp_same_day_hours_earlier_is_inverted(tmp_path):
    """**反向用例**：两个都是完整时间戳、答复早几小时 ⇒ 仍判倒置。

    （"只比到天"的放宽**只**适用于 `answered_at` 是纯日期的情况。）
    """
    _write(tmp_path, [_rec(1, asked="2016-08-03 07:26:08", answered="2016-08-03 04:04:19")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 1, "完整时间戳早 3 小时，应判倒置"


def test_midnight_answered_at_is_treated_as_day_precision(tmp_path):
    """`answered_at` 恰为 **00:00:00** 也按"只到天"处理（2026-10-10 第 4 次修）。

    实测 1,188 条里又有 **666 条**是这种：`answered_at = '2018-06-26 00:00:00'`
    —— 带时分秒但**恰为午夜整点**，那是"只给日期、时分秒填 0"的**另一种写法**。
    字符串正则 `_DATE_ONLY` 匹配不到它，所以第三次修时漏了。

    ⇒ 判据：**解析后恰为午夜 00:00:00 也按"只到天"处理**（同一天不算倒置）。
    """
    _write(tmp_path, [_rec(1, asked="2018-06-26 11:10:17",
                           answered="2018-06-26 00:00:00")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 0, "同一天、答复是午夜整点，不算倒置"


def test_midnight_answered_at_across_days_IS_inverted(tmp_path):
    """**反向用例**：午夜整点但**跨天更早** ⇒ 仍判倒置。

    （这正是为什么修完只降 337 而不是 666：666 里有一部分是跨天的，必须留着。）
    """
    _write(tmp_path, [_rec(1, asked="2018-06-26 11:10:17",
                           answered="2018-06-20 00:00:00")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 1, "答复早 6 天，必须判倒置"


def test_non_midnight_same_day_hours_earlier_is_inverted(tmp_path):
    """**反向用例**：同一天但答复**不是**午夜（真实时刻）⇒ 仍判倒置。"""
    _write(tmp_path, [_rec(1, asked="2016-08-03 07:26:08",
                           answered="2016-08-03 04:04:19")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 1, "同一天但早 3 小时（非午夜），仍判倒置"


def test_missing_dates_are_not_counted_as_inverted(tmp_path):
    """缺字段**不算**倒置 —— 否则「没数据」会被误报成「数据错」。"""
    _write(tmp_path, [
        {"source": "s", "id": "1", "question": "q", "answer": "a",
         "asked_at": None, "answered_at": None, "extra": {}},
    ])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 0


# ------------------------------------------- 判据 3 的解析（防"裸比字符串"回归）

def test_java_date_string_is_not_a_false_inversion(tmp_path):
    """**`Thu Oct 19` vs `Fri Oct 20` 不是倒置** —— 字母序 `Fri` < `Thu`。

    这是实测踩到的最大一类假阳性（`nat-tax` 5,720 条全是这个）。
    若谁把实现改回 `str(b) < str(a)`，这条必须红。
    """
    _write(tmp_path, [_rec(1, asked="Thu Oct 19 10:57:25 CST 2023",
                           answered="Fri Oct 20 16:35:05 CST 2023")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 0, "10-20 晚于 10-19，不是倒置"


def test_minute_truncation_is_not_a_false_inversion(tmp_path):
    """`15:02:00` vs `15:02` 是同一分钟，**不算倒置**（容忍 60 秒）。"""
    _write(tmp_path, [_rec(1, asked="2021-09-22 15:02:00",
                           answered="2021-09-22 15:02")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 0


def test_chinese_date_string_is_parsed_correctly(tmp_path):
    """`2026年09月7日` 早于 `2026年09月09日` —— 裸比字符串会判反。"""
    _write(tmp_path, [_rec(1, asked="2026年09月7日", answered="2026年09月09日")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 0, "9-7 早于 9-9，不是倒置"


def test_real_inversion_in_chinese_format_is_caught(tmp_path):
    """**反向用例**：中文格式下真倒置必须被抓住（解析不能把判据变恒假）。"""
    _write(tmp_path, [_rec(1, asked="2026年09月09日", answered="2026年09月7日")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 1


def test_unparsable_dates_are_counted_separately(tmp_path):
    """两个字段都有值但解析不了 ⇒ 计入 `unparsed_time`，**不当倒置也不当没事**。"""
    _write(tmp_path, [_rec(1, asked="某个怪格式", answered="另一个怪格式")])
    with _Data(tmp_path):
        s = gq.collect()
    assert s["inverted"] == 0
    assert s["unparsed_time"] == 1, "解析不了的要单独计数，不许悄悄放过"


def test_parse_time_handles_all_three_observed_formats():
    """三种实测格式都要能解析（ISO / 中文 / Java toString）。"""
    from datetime import datetime
    assert gq.parse_time("2026-09-30 02:37:41") == datetime(2026, 9, 30, 2, 37, 41)
    assert gq.parse_time("2026年09月7日") == datetime(2026, 9, 7)
    assert gq.parse_time("Thu Oct 19 10:57:25 CST 2023") == datetime(2023, 10, 19, 10, 57, 25)
    assert gq.parse_time("") is None
    assert gq.parse_time(None) is None
    assert gq.parse_time("不是日期") is None


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


def test_save_baseline_key_mapping_does_not_crash(tmp_path, monkeypatch):
    """`--update-baseline` 不得因键名不一致而崩（实测踩过）。

    `collect()` 里时间倒置的键叫 `inverted`，而基线文件里叫 `time_inverted`。
    第一版 `_save_baseline` 拿 `cur[skey]` 去取 `inverted` ⇒ `KeyError`，
    **记基线这条命令整个不可用**（而它是缺陷修好后锁定成果的唯一途径）。
    """
    monkeypatch.setattr(gq, "BASELINE", tmp_path / "b.json")
    s = {"answer_empty": 1, "content_dups": 2, "inverted": 3, "total": 100}
    monkeypatch.setattr(gq, "_load_baseline", lambda: {})
    rc = gq._save_baseline(s)
    assert rc == 0
    import json as _json
    got = _json.loads((tmp_path / "b.json").read_text(encoding="utf-8"))
    assert got["time_inverted"] == 3, f"应写入 time_inverted=3，实际 {got}"


def test_ratchet_skips_sources_still_being_harvested(monkeypatch):
    """**采集中**的来源不判恶化（样本还在长，不下结论）。

    ⚠ 2026-10-10 第 3 次修同一判据。实测 `nx-igi-259` 从 1,562 涨到 1,599 条时
    重复率 1698 → 2049/10万，棘轮报红。查证**不是回归**：
    重复组全是**相邻 id**（`10142046/47/48/49`）⇒ 站方一次公示多条；
    `dup_ids = 0` ⇒ 不是采集器重复写。
    ⇒ 根源：**正在采集中的来源，重复率会随样本增长而波动**
      （小样本没采到那几条重复的，样本一大就出现）。

    判据：样本量比基线**增长 >20%** ⇒ 视为"采集中"，不判恶化。
    """
    monkeypatch.setattr(gq, "_load_baseline", lambda: {
        "total": 1000,
        "per_source": {"srcGrowing": {"total": 100, "dups": 1, "dup_rate": 1000.0}},
    })
    s = {
        "answer_empty": 0, "content_dups": 0, "inverted": 0, "total": 1000,
        "per_source_dup": {
            # 样本涨了 50%（100 -> 150），重复率也涨了 ⇒ **不该判恶化**
            "srcGrowing": {"total": 150, "dups": 5, "dup_rate": 33333.0},
        },
    }
    checks = {n: ok for n, ok, _d in gq.ratchet(s)}
    key = next(iter(checks))
    assert checks[key] is True, f"采集中（样本 +50%）的来源不该判恶化：{checks}"


def test_ratchet_still_flags_a_settled_source(monkeypatch):
    """**反向用例**：样本量**没怎么变**（已采完）的来源，重复率变坏 ⇒ 必须报红。"""
    monkeypatch.setattr(gq, "_load_baseline", lambda: {
        "total": 1000,
        "per_source": {"srcDone": {"total": 100, "dups": 1, "dup_rate": 1000.0}},
    })
    s = {
        "answer_empty": 0, "content_dups": 0, "inverted": 0, "total": 1000,
        "per_source_dup": {
            # 样本只涨 5%（100 -> 105，不算"采集中"），但重复率暴涨
            "srcDone": {"total": 105, "dups": 50, "dup_rate": 47619.0},
        },
    }
    checks = {n: ok for n, ok, _d in gq.ratchet(s)}
    key = next(iter(checks))
    assert checks[key] is False, f"已采完的来源重复率变坏，必须报红：{checks}"


def test_save_baseline_refuses_regression(tmp_path, monkeypatch):
    """**反向用例**：**已有来源**的重复率变坏时必须**拒绝**写基线。

    ⚠ 2026-10-10 改（棘轮从"全库率"改成"**按来源**的率"）：
    原用例把全库 `answer_empty` 从 1 调到 500 期望拒绝 ——
    但新语义下 `answer_empty` 不再逐项比（只有**按来源的重复率**在比）。
    ⇒ 改为：给基线一个来源、当前值比它差 ⇒ 必须拒绝。
    """
    monkeypatch.setattr(gq, "BASELINE", tmp_path / "b.json")
    monkeypatch.setattr(gq, "_load_baseline", lambda: {
        "total": 1000,
        "per_source": {"srcA": {"total": 100, "dups": 1, "dup_rate": 1000.0}},
    })
    s = {
        "answer_empty": 1, "content_dups": 50, "inverted": 1, "total": 1000,
        "per_source_dup": {"srcA": {"total": 100, "dups": 50, "dup_rate": 50000.0}},
    }
    rc = gq._save_baseline(s)
    assert rc == 1, "已有来源 srcA 的重复率从 1000 涨到 50000/10万，必须拒绝记基线"


def test_save_baseline_allows_a_new_high_dup_source(tmp_path, monkeypatch):
    """**新来源**即使重复率高也**不算恶化**（它没有基线可比）。

    ⚠ 这正是 2026-10-10 那次假红的根因：新采的 `nx-igi-259` 源内重复率
    2.38% 高于全库均值 2.12% ⇒ 全库率被拉高 ⇒ 棘轮误判"变坏"。
    """
    monkeypatch.setattr(gq, "BASELINE", tmp_path / "b.json")
    monkeypatch.setattr(gq, "_load_baseline", lambda: {
        "total": 1000,
        "per_source": {"srcA": {"total": 100, "dups": 1, "dup_rate": 1000.0}},
    })
    s = {
        "answer_empty": 1, "content_dups": 60, "inverted": 1, "total": 1100,
        "per_source_dup": {
            "srcA": {"total": 100, "dups": 1, "dup_rate": 1000.0},   # 没变
            "srcNEW": {"total": 100, "dups": 50, "dup_rate": 50000.0},  # 新来源，高
        },
    }
    rc = gq._save_baseline(s)
    assert rc == 0, "新来源没有基线可比，不该判成恶化"


# ---------------------------------------------------------------- 纯 ASCII 出口

def test_quiet_output_is_pure_ascii():
    """`--quiet` 是**给闸门读的**，必须纯 ASCII（GBK 控制台会崩）。

    ⚠⚠ **2026-10-10 修（独立复核发现 4.1，严重度高）**：原用例的正文是

    ```python
    ascii_kv({"TOTAL": 1, "NOTE": "中文"}, stream=buf)
    buf.getvalue().encode("ascii")
    ```

    ⇒ 它测的是 **`common.ascii_kv` 会不会替换非 ASCII**（那一条由
    `test_ascii_kv_is_pure_ascii` 正确钉住），**根本没执行 `gate-quality.py --quiet`**。
    复核实测：把 `--quiet` 里真正决定输出内容的 `MODE` 值改成中文，
    **闸门输出真的变脏了，而这条用例仍然全绿**。
    ⇒ 这正是"判据有牙但咬错了对象"的第 4 处 —— 而它守的是
    "**给门禁读的机器接口必须纯 ASCII**"这条硬约束。

    ⇒ 现在**真的跑 `--quiet` 并检查它的字节**。
    """
    r = subprocess.run([str(PY), str(SCRIPT), "--quiet"], cwd=str(ROOT),
                       capture_output=True, timeout=600)
    stdout = r.stdout or b""
    stderr = r.stderr or b""
    # ⚠⚠ **必须分开看 stdout 与 stderr**（我自己第一版又漏了，两次返工）：
    #   实测往 `--quiet` 分支插一句裸 `print("⚠ …")` ⇒ 它 **UnicodeEncodeError 崩掉**，
    #   而 **stdout 是空的、stderr 里也没有非 ASCII 字节**（崩在写出之前）。
    #   ⇒ 把两者拼起来查"有没有非 ASCII"会**漏掉"它崩了"**这种最严重的形态。
    #   正确判据：**stdout 必须非空、纯 ASCII、且含闸门要读的键**。
    assert stdout, (f"--quiet 的 stdout 是空的 —— 它崩了？\n"
                    f"rc={r.returncode}  stderr 末尾：{stderr[-400:]!r}")
    # ⚠⚠ **必须查 stderr 里有没有异常**（我自己前两版都漏了这一条，两次返工）：
    #   实测往 `--quiet` 分支插一句裸 `print("⚠ …")` ⇒ 它 **UnicodeEncodeError 崩掉**。
    #   而 `ascii_kv(...)` 已经先写进了 stdout ⇒ **stdout 非空、且纯 ASCII**，
    #   崩的痕迹**只在 stderr**（`UnicodeEncodeError: 'gbk' codec ...`）。
    #   ⇒ 不查 stderr 就永远看不见这个形态。
    assert b"Traceback" not in stderr and b"Error" not in stderr, (
        f"--quiet 的 stderr 里有异常（它崩了）：{stderr[-400:]!r}")
    try:
        stdout.decode("ascii")
    except UnicodeDecodeError as e:
        raise AssertionError(
            f"--quiet 的 stdout 不是纯 ASCII（GBK 控制台会崩）：{e}\n"
            f"原始字节前 200：{stdout[:200]!r}")
    assert b"TOTAL=" in stdout, f"--quiet 的 stdout 里没有闸门要读的键：{stdout[:200]!r}"


def test_quiet_output_has_the_expected_keys():
    """**补强**：`--quiet` 必须打出闸门要解析的那些键。

    只测"纯 ASCII"不够 —— 一个空输出也是纯 ASCII。
    这条钉住**输出里真的有闸门读的键**。
    """
    r = subprocess.run([str(PY), str(SCRIPT), "--quiet"], cwd=str(ROOT),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    out = r.stdout or ""
    for key in ("TOTAL=", "ANSWER_EMPTY=", "CONTENT_DUPS=", "TIME_INVERTED=", "MODE="):
        assert key in out, f"--quiet 输出缺 {key}，实际：{out[:300]}"
