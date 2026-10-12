"""真人问答召回尺子的回归判据（spec 010）。

## 抓什么

尺子必须：① 不把测不出来的算进分数；② 不偏科；③ 每条可追溯；④ 可复现。
每条断言**各自**都有牙（变异自验见 `specs/010-real-question-ruler/tasks.md`）。

## 为什么用**产物文件**而不是跑 build

build 要读 41.5 万条记录（约 2 分钟）⇒ 不适合放进每轮门禁。
本测试读**已提交的产物**（`ruler-v1.jsonl` / `stats-v1.json`），
判据与 `verify.py` 同一套（但不依赖它运行）。

⚠ **代价（必须写明）**：本测试**不能**发现"build.py 的代码被改坏了但产物没重跑"。
那个由 `verify.py`（重读原始数据）覆盖，它是独立复算。
"""
import json
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1] / "eval" / "real-question-ruler"
RULER = HERE / "ruler-v1.jsonl"
STATS = HERE / "stats-v1.json"

#: 与 build.py 同一张表（这里独立抄一份：测试不该 import 被测实现）
COMPLAINT = ("投诉", "举报", "辱骂", "态度", "不作为", "推诿", "拒不开门", "乱收费",
             "噪音", "扰民", "违建", "拖欠", "索赔", "纠纷", "上访", "信访", "曝光",
             "我反映", "我要举报", "投诉电话", "处理结果", "迟迟不")
MAX_Q = 200


@pytest.fixture(scope="module")
def ruler():
    assert RULER.exists(), f"尺子产物不存在: {RULER}（先跑 build.py）"
    return [json.loads(l) for l in RULER.read_text(encoding="utf-8").split("\n") if l.strip()]


@pytest.fixture(scope="module")
def stats():
    assert STATS.exists(), f"统计产物不存在: {STATS}"
    return json.loads(STATS.read_text(encoding="utf-8"))


class Test规模与结构:
    def test_恰好_500_条(self, ruler):
        assert len(ruler) == 500

    def test_每条都有必填字段(self, ruler):
        need = {"id", "source", "trace_key", "url", "dept", "question", "q_len",
                "gold_std", "gold_doc_id", "gold_weak", "layering", "dup_count",
                "has_clause_ref"}
        for c in ruler:
            assert need.issubset(c.keys()), f"缺字段: {need - set(c.keys())}"

    def test_gold_std_不为空(self, ruler):
        for c in ruler:
            assert c["gold_std"], f"gold 为空: {c['id']}"

    def test_q_len_与实际长度一致(self, ruler):
        for c in ruler:
            assert c["q_len"] == len(c["question"]), c["id"]


class Test不把测不出来的算进分数:
    """SC-002 —— 这三条是这个尺子"有没有意义"的底线。"""

    def test_没有投诉举报类(self, ruler):
        bad = [c["id"] for c in ruler
               if any(w in c["question"] for w in COMPLAINT)]
        assert not bad, f"投诉类混入 {len(bad)} 条: {bad[:3]}"

    def test_没有超长问句(self, ruler):
        bad = [c["id"] for c in ruler if len(c["question"]) > MAX_Q]
        assert not bad, f">200 字混入 {len(bad)} 条: {bad[:3]}"

    def test_没有过短问句(self, ruler):
        bad = [c["id"] for c in ruler if len(c["question"]) < 8]
        assert not bad, f"<8 字混入 {len(bad)} 条: {bad[:3]}"

    def test_stats_也如实声明(self, stats):
        assert stats["complaint_in_ruler"] == 0
        assert stats["over_maxlen_in_ruler"] == 0


class Test不偏科:
    """SC-003。"""

    def test_最大单一来源不超过_10_百分比(self, ruler):
        dist = Counter(str(c["source"]) for c in ruler)
        share = max(dist.values()) / len(ruler)
        assert share <= 0.10, f"最大来源占 {share:.1%}: {dist.most_common(3)}"

    def test_覆盖至少_20_个来源(self, ruler):
        assert len({str(c["source"]) for c in ruler}) >= 20

    def test_stats_与复算一致(self, ruler, stats):
        dist = Counter(str(c["source"]) for c in ruler)
        assert stats["n_sources"] == len(dist)
        assert round(stats["max_source_share"], 4) == round(max(dist.values()) / len(ruler), 4)


class Test可追溯:
    """SC-006。追溯键必须是 (source, id) —— 实测 url 不唯一且有 None。"""

    def test_trace_key_格式正确(self, ruler):
        for c in ruler:
            assert c["trace_key"] == f"{c['source']}|{c['id']}", c["id"]

    def test_trace_key_不重复(self, ruler):
        keys = [c["trace_key"] for c in ruler]
        dup = [k for k, n in Counter(keys).items() if n > 1]
        assert not dup, f"trace_key 重复: {dup[:3]}"

    def test_url_允许为空但不允许错(self, ruler):
        # 实测 27 条 url 为 None（合法 —— 那批数据本来就没 url）
        n_none = sum(1 for c in ruler if not c.get("url"))
        assert n_none == 27, f"url 为空的条数变了: {n_none}"


class Test可复现:
    """SC-004。种子与输入规模必须写进产物。"""

    def test_种子被记录(self, stats):
        assert stats["seed"] == 20261012

    def test_输入规模被记录(self, stats):
        assert stats["generated_from"]["total_records"] == 415742
        assert stats["generated_from"]["data_files"] == 592

    def test_五道过滤计数齐全(self, stats):
        f = stats["filters"]
        for k in ("F1 非考卷（没点名库内文件）",
                  "F2 投诉/举报（无对错标准）",
                  "F3 问句过长（>200 字，是来信全文）",
                  "F4 问句过短（<8 字，多半是标题）",
                  "F5 重复问题（同题只留 1 条）"):
            assert k in f, f"缺排除计数: {k}"
        # 漏斗必须闭合：总记录 = F1 排除 + 过四道过滤 + 那三道排除
        total = stats["generated_from"]["total_records"]
        f1 = f["F1 非考卷（没点名库内文件）"]
        f2 = f["F2 投诉/举报（无对错标准）"]
        f3 = f["F3 问句过长（>200 字，是来信全文）"]
        f4 = f["F4 问句过短（<8 字，多半是标题）"]
        after = stats["candidates_after_filters"]
        assert f1 + f2 + f3 + f4 + after == total, (
            f"漏斗不闭合: {f1}+{f2}+{f3}+{f4}+{after} != {total}")


class Test分层如实:
    """分层必须如实记录 —— 尤其 `zero_overlap` 很少这件事实。"""

    def test_分层计数与复算一致(self, ruler, stats):
        lay = Counter(c["layering"] for c in ruler)
        assert stats["layering"] == dict(lay)

    def test_zero_overlap_很少是已知事实(self, ruler):
        """⚠ 这条**故意断言它很少** —— 防止有人把 0.8% 说成"大白话损耗很小"。

        文档级口径下 `zero_overlap` 几乎必然很低（一篇法规几万字，与任何问句
        都大概率有 2 字公共子串）⇒ 它**不是**一个有效的"大白话"信号。
        见 `eval/real-question-ruler/README.md` 的"已知缺陷 1"。
        """
        n = sum(1 for c in ruler if c["layering"] == "zero_overlap")
        assert n < 50, (
            f"zero_overlap 有 {n} 条 —— 与已知事实不符。若这是真的改善了，"
            "必须同时更新 README 的『已知缺陷 1』并说明口径变化。")
