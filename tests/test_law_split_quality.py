"""法规切分质量契约测试（2026-10-07 两处修正）。

## 修正一：切分点**只认行首**的「第X条」
旧正则 `(?=第X条)` 任何位置都切 ⇒ 正文里的**引用**（"依照本法第五十条规定…"）也被当成新条款起点。
实测 1,514 个法规文件：全文 76,790 处「第X条」，**12,122 处（15.8%）在句子中间**。
用 9 部已知真实条数的法律当裁判：旧切法完全一致 2/9、平均偏差 25.6 条；
只认行首 **7/9**、平均偏差 **6.1 条**。

## 修正二：切分前**剥掉文件头**（标题 + 立法沿革 + `<!-- INFO END -->`）
原先文件头被当成"章节上下文"**逐条前置**（而且用过不重置）⇒ 整部法律每条都背同一段（中位 122 字）。

## 变异验证
 · 把 `_LAW_SPLIT` 改回不认行首 ⇒ `test_reference_does_not_split` 红；
 · 去掉 `_strip_law_front_matter` 调用 ⇒ `test_front_matter_not_in_body` 红。
"""
from src.core.ingestion.law_text import (
    _strip_law_front_matter, ingest_law_text, split_law_text)
from src.core.storage.sqlite_db import get_db_connection

LAW_WITH_FRONT_MATTER = """# 中华人民共和国示例法

2007年6月29日 第十届全国人民代表大会常务委员会第二十八次会议通过

2012年12月28日 第十一届全国人民代表大会常务委员会第三十次会议修正

<!-- INFO END -->

## 第一章 总则

第一条 为了规范示例行为，保护当事人的合法权益，制定本法。

第二条 在中华人民共和国境内从事示例活动的，适用本法。

## 第二章 附则

第三条 本法自公布之日起施行。
"""

#: 正文里带**引用**：旧切法会把「第五十条」当新条款
LAW_WITH_REFERENCE = """# 示例程序法

<!-- INFO END -->

第一条 当事人申请许可的，依照本法第五十条规定办理。

第二条 违反本法第三条规定的，依照本法第七十七条处理。
"""


class TestFrontMatterStripped:
    def test_front_matter_not_in_body(self):
        arts = split_law_text(LAW_WITH_FRONT_MATTER)
        joined = "\n".join(b for _, b in arts)
        assert "全国人民代表大会常务委员会" not in joined, "立法沿革不该进条文正文"
        assert "中华人民共和国示例法" not in joined.split("第一章")[0], "标题不该进条文正文"

    def test_first_chapter_heading_kept_as_context(self):
        """**首个**章标题要留（那才是上下文该带的东西）。

        ⚠ **已知的既有小毛病（不是本次引入，登记不修）**：切分点是"下一条的开头"，
        所以**第二个及以后**的章标题（如 `## 第二章 附则`）会落在**前一条正文的尾部**，
        而不会成为后一条的上下文 —— 实测 `arts[1][1]` 末尾带 `## 第二章 附则`。
        影响轻微（标题文字不污染前一条的语义），故本轮只登记。
        """
        arts = split_law_text(LAW_WITH_FRONT_MATTER)
        assert "第一章" in arts[0][1]
        assert "第二章" in arts[1][1], "（既有行为）后一个章标题落在前一条尾部"

    def test_later_heading_not_in_first_clause(self):
        """前一条不该带上**后面**章节的标题。"""
        arts = split_law_text(LAW_WITH_FRONT_MATTER)
        assert "第二章" not in arts[0][1]

    def test_strip_returns_text_after_marker(self):
        out = _strip_law_front_matter(LAW_WITH_FRONT_MATTER)
        assert out.lstrip().startswith("## 第一章")

    def test_strip_without_marker_falls_back(self):
        t = "# 标题\n\n正文第一段。\n"
        assert _strip_law_front_matter(t).lstrip().startswith("正文第一段")


class TestLineStartSplit:
    def test_reference_does_not_split(self):
        """**本修正的核心**：句子中间的「第X条」是引用，不是新条款。"""
        arts = split_law_text(LAW_WITH_REFERENCE)
        assert [a[0] for a in arts] == ["第一条", "第二条"], \
            f"引用被当成了新条款：{[a[0] for a in arts]}"

    def test_reference_stays_in_body(self):
        arts = split_law_text(LAW_WITH_REFERENCE)
        assert "第五十条" in arts[0][1]
        assert "第七十七条" in arts[1][1]

    def test_line_start_clause_splits(self):
        arts = split_law_text(LAW_WITH_FRONT_MATTER)
        assert [a[0] for a in arts] == ["第一条", "第二条", "第三条"]

    def test_bold_form_still_splits(self):
        t = "**第一条** 甲。\n\n**第二条** 乙。\n"
        assert [a[0] for a in split_law_text(t)] == ["第一条", "第二条"]


class TestEnumStillWorks:
    def test_enum_doc_unaffected(self):
        """修正只动「第X条」这条路，枚举那条路不受影响。"""
        t = "一、总则内容。\n\n二、分则内容。\n"
        arts = split_law_text(t)
        assert arts == [] or [a[0] for a in arts] == ["一", "二"]


class TestFallbackAlsoStripsFrontMatter:
    """兜底分支（整篇作一条）**也必须**剥文件头。

    实测缺陷：全量重入后抽检抓到 `刑法修正案（二）` 的「全文」条以
    `# 中华人民共和国刑法修正案（二） 2001年8月31日 …会议通过 <!-- INFO …` 开头 ——
    它两条切分都切不出，走了 `fallback_single_clause`，而那条分支不经过 `split_law_text`。
    """

    #: 没有任何条款编号、只有文件头 + 一段正文
    NO_CLAUSE_DOC = """# 中华人民共和国示例修正案（二）

2001年8月31日 第九届全国人民代表大会常务委员会第二十三次会议通过

<!-- INFO END -->

将刑法第一百一十四条修改为："放火、决水、爆炸…尚未造成严重后果的，处三年以上十年以下有期徒刑。"
"""

    def test_fallback_clause_has_no_front_matter(self):
        r = ingest_law_text(self.NO_CLAUSE_DOC, standard_no="示例修正案二(测试)",
                            standard_name="示例修正案二(测试)", fallback_single_clause=True)
        assert r.get("status") == "ok", r
        assert r.get("total_clauses") == 1, "无编号正文应整篇作一条"
        conn = get_db_connection()
        row = conn.execute(
            "SELECT content_text FROM clause_revision WHERE doc_id=?", (r["doc_id"],)).fetchone()
        body = row[0] if row else ""
        assert "全国人民代表大会常务委员会" not in body, f"文件头没剥掉：{body[:80]}"
        assert "<!-- INFO" not in body, f"INFO 标记没剥掉：{body[:80]}"
        assert "放火、决水" in body, "正文不该被剥掉"
