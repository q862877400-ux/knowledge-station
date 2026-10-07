"""「一、二、三、」式法规切分契约测试（2026-10-07 新增）。

## 背景（实测）
业主那批 LawRefBook 法规入库时，**39 件全是司法解释**报
`未识别到任何'第X条'条文`。查原文发现它们用的是：

    一、对于行政执法机关移送检察机关的涉嫌犯罪案件……
    二、人民检察院控告检察部门审查……

而 `split_law_text` 只认「第X条」⇒ 一条都切不出。

## 变异验证（本文件为什么这么写）
 · 把 `ingest_law_text` 里 `articles = split_law_enum_text(text)` 那两行删掉
   ⇒ `TestEndToEnd::test_enum_doc_ingests` 红（回退成"未识别到条文"）；
 · 把 `_LAW_ENUM_SPLIT` 的 `^` 去掉（不再要求行首）⇒ `test_subitem_not_split` 红
   （「（一）」这类子项会被误切）。
"""
from src.core.ingestion.law_text import (
    ingest_law_text, split_law_enum_text, split_gb_text, split_law_text)

#: 与业主那批里真实失败件同型（节选自《人民检察院办理行政执法机关移送涉嫌犯罪案件的规定》）
ENUM_DOC = """# 人民检察院办理行政执法机关移送涉嫌犯罪案件的规定

2001年9月10日 最高人民检察院第九届检察委员会第九十六次会议讨论通过

<!-- INFO END -->

根据《中华人民共和国刑事诉讼法》的有关规定，现就有关问题作如下规定：

一、对于行政执法机关移送检察机关的涉嫌犯罪案件，统一由人民检察院控告检察部门受理。

二、人民检察院控告检察部门审查行政执法机关移送的涉嫌犯罪案件，应当根据不同情况，
提出移送有关部门的处理意见，并通知移送的行政执法机关：

（一）对于不属于检察机关管辖的案件，移送其他有管辖权的机关处理；

（二）对于属于检察机关管辖，但不属于本院管辖的案件，移送有管辖权的人民检察院办理。

三、对于不属于本院管辖但又必须采取紧急措施的案件，应当先采取紧急措施，再行移送。
"""

#: 正常「第X条」法规（用于证明新分支不影响既有行为）
ARTICLE_DOC = """# 中华人民共和国示例法

第一条 为了规范示例行为，制定本法。

第二条 在中华人民共和国境内从事示例活动的，适用本法。
本法所称示例活动，是指下列情形：
一、第一类示例；
二、第二类示例。

第三条 本法自公布之日起施行。
"""


class TestEnumSplit:
    def test_splits_enum_numbering(self):
        arts = split_law_enum_text(ENUM_DOC)
        assert [a[0] for a in arts] == ["一", "二", "三"]

    def test_body_kept(self):
        arts = split_law_enum_text(ENUM_DOC)
        assert "统一由人民检察院控告检察部门受理" in arts[0][1]
        assert "先采取紧急措施" in arts[2][1]

    def test_subitem_not_split(self):
        """「（一）（二）」是子项，不是条款 —— 必须留在所属条目正文里。"""
        arts = split_law_enum_text(ENUM_DOC)
        assert len(arts) == 3
        assert "（一）对于不属于检察机关管辖的案件" in arts[1][1]

    def test_enum_number_not_matched_mid_line(self):
        """行内出现的「一、」不算条款头（要求行首）。"""
        t = "前言：一、这不是条款。\n二、这才是条款。\n"
        assert [a[0] for a in split_law_enum_text(t)] == ["二"]

    def test_law_text_finds_nothing_here(self):
        # 这正是当初报"未识别到条文"的原因
        assert split_law_text(ENUM_DOC) == []

    def test_article_doc_unaffected_by_enum_splitter(self):
        # 「第X条」正文里的「一、二、」子项：法令切分器不受影响
        assert [a[0] for a in split_law_text(ARTICLE_DOC)] == ["第一条", "第二条", "第三条"]


class TestEndToEnd:
    def test_enum_doc_ingests(self):
        """端到端：这种文件**必须能入库**，而不是回退成"未识别到条文"。"""
        r = ingest_law_text(ENUM_DOC, standard_no="示例规定(枚举体)", standard_name="示例规定(枚举体)")
        assert r.get("status") == "ok", r
        assert r.get("total_clauses") == 3

    def test_article_doc_still_uses_article_splitter(self):
        r = ingest_law_text(ARTICLE_DOC, standard_no="示例法(条文体)", standard_name="示例法(条文体)")
        assert r.get("status") == "ok", r
        assert r.get("total_clauses") == 3          # 仍是「第X条」口径，没被枚举切分器抢走

    def test_unparseable_still_errors(self):
        """两种编号都没有 ⇒ 仍须**如实报错**，不许静默当一条。"""
        r = ingest_law_text("这里没有任何条款编号，只是一段话。", standard_no="无编号(测试)",
                            standard_name="无编号(测试)")
        assert r.get("status") == "error"
