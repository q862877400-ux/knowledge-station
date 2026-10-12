"""gov-qa 标签复核包的回归判据（spec 005 T501 收口）。

## 抓什么

T501 的出路已从"人工抽检"改成"AI 复核"（业主 2026-10-07 裁定）。
本测试钉住**四件不能退让的事**：

| # | 断言 | 谁被咬住 |
|---|---|---|
| 1 | 产物存在、条数与源一致 | 造包脚本坏了 / 源换了 |
| 2 | **两半分开**：语言半**不含标签字段** | 有人图省事把 label 塞进语言半 ⇒ 两半退化 |
| 3 | **标注了"AI 判定"**，且**不声称准确率** | 有人把 AI 复核写成"人工确认"或"已满足规格" |
| 4 | 事实半**含**标签、语言半**只含 qid+question** | 两半装反 |

## ⚠ 为什么 3 是硬判据

`docs/NOT-DOING.md` 第 23 条明写：
「**规格原文没改** —— 凡写着 `confirmed_by` 必须是人处照旧保留，
且**不许**因为有了 AI 复核就写成"已满足"」。
⇒ 产物里一旦出现"人工确认"或具体准确率，就是**假绿**（宪法 III）。
"""
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1] / "eval" / "govqa-label-review"
FACT_MD = HERE / "ai-review-fact.md"
FACT_JSONL = HERE / "ai-review-fact.jsonl"
LANG_MD = HERE / "ai-review-lang.md"
LANG_JSONL = HERE / "ai-review-lang.jsonl"
SUMMARY = HERE / "review-summary.json"

#: 源 CSV（不在本仓，是业主交付物位置）
SRC = Path(r"D:\AI\output\label-check-200.csv")

#: 标签全集
LABELS = ("咨询", "求助", "投诉", "举报", "建议", "申诉", "表扬",
          "反映", "征求意见", "监察", "其他")


@pytest.fixture(scope="module")
def summary():
    assert SUMMARY.exists(), f"缺产物: {SUMMARY}（先跑 build-review.py）"
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fact_rows():
    return [json.loads(l) for l in FACT_JSONL.read_text(encoding="utf-8").split("\n") if l.strip()]


@pytest.fixture(scope="module")
def lang_rows():
    return [json.loads(l) for l in LANG_JSONL.read_text(encoding="utf-8").split("\n") if l.strip()]


class Test产物存在且规模对:
    def test_四份产物都在(self):
        for p in (FACT_MD, FACT_JSONL, LANG_MD, LANG_JSONL, SUMMARY):
            assert p.exists(), f"缺: {p}"

    def test_两半条数相同且与源一致(self, summary, fact_rows, lang_rows):
        assert len(fact_rows) == len(lang_rows) == summary["source_rows"]

    def test_与源_CSV_条数一致(self, summary):
        if not SRC.exists():
            pytest.skip(f"源 CSV 不在（{SRC}）—— 那是业主交付物，不在本仓")
        import csv
        rows = [r for r in csv.DictReader(SRC.open(encoding="utf-8-sig"))
                if (r.get("question") or "").strip()]
        assert len(rows) == summary["source_rows"]

    def test_两半的_qid_集合相同(self, fact_rows, lang_rows):
        assert {r["qid"] for r in fact_rows} == {r["qid"] for r in lang_rows}

    def test_qid_不重复(self, fact_rows):
        ids = [r["qid"] for r in fact_rows]
        assert len(ids) == len(set(ids))


class Test两半必须分开:
    """⚠ 这是本特性的核心判据 —— 语言半拿到标签就退化成一半。"""

    def test_语言半不含_label_字段(self, lang_rows):
        for r in lang_rows:
            assert "label" not in r, f"语言半泄漏了 label: {r.get('qid')}"
            assert "label_source" not in r, f"语言半泄漏了 label_source: {r.get('qid')}"

    def test_语言半字段恰好是_qid_与_question(self, lang_rows):
        for r in lang_rows:
            assert set(r.keys()) == {"qid", "question"}, f"语言半字段异常: {set(r.keys())}"

    def test_事实半含_label_与_label_source(self, fact_rows):
        for r in fact_rows:
            assert "label" in r and "label_source" in r, f"事实半缺标签: {r.get('qid')}"

    def test_语言半的_md_条目区不出现_现标字样(self):
        t = LANG_MD.read_text(encoding="utf-8")
        body = t[t.find("## 待判条目"):]
        assert "现标" not in body, "语言半的条目区出现了「现标」⇒ 泄漏了标签"

    def test_事实半的_md_每条都有现标(self, fact_rows):
        t = FACT_MD.read_text(encoding="utf-8")
        body = t[t.find("## 待判条目"):]
        assert body.count("现标") == len(fact_rows)


class Test标注为_AI_判定而不是人工确认:
    """⚠ NOT-DOING 第 23 条的硬约束。"""

    def test_事实半标注了_AI_判定(self):
        t = FACT_MD.read_text(encoding="utf-8")
        assert "AI 判定" in t or "AI判定" in t
        assert "不是人工确认" in t

    def test_语言半标注了_AI_判定(self):
        t = LANG_MD.read_text(encoding="utf-8")
        assert "AI 判定" in t or "AI判定" in t
        assert "不是人工确认" in t

    def test_摘要的_kind_是_AI_判定(self, summary):
        assert "AI 判定" in summary["kind"]
        assert "人工确认" in summary["kind"]

    def test_摘要声明了规格原文没改(self, summary):
        assert "confirmed_by" in summary["warning"]
        assert "FR-004" in summary["warning"] or "SC-003" in summary["warning"]

    def test_不声称已满足规格(self):
        """产物里**不许**把"已满足 FR-004/SC-003"当成**结论**说出来。

        ⚠ 排除口径要小心：产物**故意**写了「**不得**被写成「已满足 FR-004 / SC-003」」
        —— 那是**禁令**，不是结论。所以判据是"出现在**断言句**里"，
        而不是"出现过"（后者会把禁令自己咬住 —— 第一版就是这么错的）。
        """
        for p in (FACT_MD, LANG_MD):
            t = p.read_text(encoding="utf-8")
            for ln in t.split("\n"):
                if "已满足 FR-004" not in ln and "已满足 SC-003" not in ln:
                    continue
                # 这一行必须是"禁令"形态（含「不得」/「不许」/「不是」）
                assert any(w in ln for w in ("不得", "不许", "不是")), (
                    f"{p.name} 把「已满足」当结论说了: {ln.strip()[:100]}")


class Test不声称准确率:
    """T501 的完成判据是"复核包就绪"，不是"准确率已知"。"""

    def test_摘要的_accuracy_是_null(self, summary):
        assert summary["accuracy"] is None, (
            "accuracy 不是 null ⇒ 要么真回填了（那要同时改 README 与 T501），"
            "要么有人编了一个数")

    def test_产物里不出现具体准确率数字(self):
        for p in (FACT_MD, LANG_MD):
            t = p.read_text(encoding="utf-8")
            assert "准确率：" not in t and "准确率:" not in t


class Test标签口径:
    def test_摘要的标签全集是_11_类(self, summary):
        assert set(summary["labels_universe"]) == set(LABELS)

    def test_摘要的标签分布合计等于条数(self, summary):
        assert sum(summary["label_distribution"].values()) == summary["source_rows"]

    def test_摘要的_label_source_分布合计等于条数(self, summary):
        assert sum(summary["label_source_distribution"].values()) == summary["source_rows"]

    def test_事实半的标签都在全集内(self, fact_rows):
        for r in fact_rows:
            assert r["label"] in LABELS, f"未知标签: {r['label']}"
