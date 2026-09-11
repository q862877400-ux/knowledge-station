"""A 组：反熵与既有行为不变（`src/core/quality/` 抽取的差分锁定）。

## 为什么用"冻结副本"做差分
数据体检 6 标签的规则原先内联在 `server.py` 的 handler 里，而**那个端点此前完全没有测试**
（全仓 grep 零命中）。把它抽成纯函数时，唯一的网就是本文件：把抽走前的实现**逐字符冻结**
在这里当基准，逐用例比对"新函数 tags == 冻结副本 tags"。

这意味着：以后想改判据，必须先改这里的冻结副本（= 显式承认行为变更），
不允许"顺手优化"悄悄改变既有端点的输出。
"""

from __future__ import annotations

import re

import pytest

from src.core.quality import clause_health, clause_health_html_to_text

# --------------------------------------------------------------------------- #
# 冻结基准：抽取前 server.py 内联实现的逐字符副本（**不要改**，除非有意变更行为）
# --------------------------------------------------------------------------- #


def _legacy_html_to_text(html: str | None, limit: int = 400) -> str:
    if not html:
        return ""
    from src.core.text_utils import clean_eq_tags, html_unescape
    t = clean_eq_tags(html)
    t = re.sub(r"</t[dh]>", " | ", t)
    t = re.sub(r"</tr>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html_unescape(t)
    t = re.sub(r"[ \t\u3000]+", " ", t)
    t = re.sub(r"(?m) \| +$", "", t)
    return re.sub(r"\n{2,}", "\n", t).strip()[:limit]


def _legacy_tags(content_text: str, content_markdown: str | None) -> list[str]:
    ct = content_text or ""
    table_md = _legacy_html_to_text(content_markdown) if content_markdown else ""
    tags: list[str] = []
    if table_md:
        tokens = {c.strip() for ln in table_md.split("\n")
                  for c in ln.split("|") if c.strip()}
        lines = {re.sub(r"\s+", " ", l.strip()) for l in ct.split("\n") if l.strip()}
        if tokens & lines:
            tags.append("正文含内嵌表格文本")
        counts = [len([c for c in r.split("|") if c.strip()])
                  for r in table_md.split("\n") if "|" in r]
        data_counts = counts[1:] if len(counts) > 1 else counts
        if data_counts and max(data_counts) - min(data_counts) >= 2:
            tags.append("表格列数不一致")
        if re.search(r"\|\s*\d{3,}\s*\|", table_md) or \
                re.search(r"\|\s*(IN|NV|IVI|VI)\s*\|", table_md):
            tags.append("表格脏单元格")
    if re.search(r"[a-z]{16,}", ct):
        tags.append("英文粘连")
    if re.search(r"\d+\s+GB\s+[0-9—–-]+\s*$", ct) or \
            re.search(r"\n\s*\d{1,2}\s+[\u4e00-\u9fa5]{4,}\s*$", ct):
        tags.append("页脚/下节标题泄漏")
    if re.search(r"[\u4e00-\u9fa5A-Za-z0-9]\n[\u4e00-\u9fa5A-Za-z0-9]", ct):
        tags.append("正文换行残留")
    return tags


# --------------------------------------------------------------------------- #
# 用例集：每个判据块的正/负例（正例必须命中，负例必须不命中——防"恒真"空断言）
# --------------------------------------------------------------------------- #

TABLE_HTML_EMBEDDED = "<table><tr><td>公称直径</td><td>壁厚</td></tr><tr><td>100</td><td>4</td></tr></table>"
# 列数阶梯：**跳过首行后**数据行之间仍要有 ≥2 的差（首行是表头，规则刻意不比它）
TABLE_HTML_JAGGED = (
    "<table>"
    "<tr><td>列1</td><td>列2</td><td>列3</td></tr>"
    "<tr><td>a</td><td>b</td><td>c</td><td>d</td></tr>"
    "<tr><td>e</td><td>f</td></tr>"
    "</table>"
)
# 脏单元格：规则匹配的是 `| 值 |`（**夹在两根竖线之间**），所以必须是中间列
TABLE_HTML_DIRTY = "<table><tr><td>x</td><td>IN</td><td>y</td></tr></table>"
TABLE_HTML_DIRTY_NUM = "<table><tr><td>甲</td><td>123</td><td>乙</td></tr></table>"
TABLE_HTML_LONG = "<table><tr><td>" + ("长" * 500) + "</td></tr></table>"
TABLE_HTML_EQ = "<table><tr><td><eq>m \\le 100</eq></td><td>&amp;nbsp;</td></tr></table>"

CASES = [
    # (content_text, content_markdown, must_include, must_exclude, 说明)
    # 注：正/负例用**包含/排除**断言而不是完整集合——完整集合会退化成"照抄实现"（循环论证），
    # 而"这条文本必须命中 X / 必须不命中 X"是人工可判、且能抓出恒真规则的空断言。
    ("公称直径\n4", TABLE_HTML_EMBEDDED, {"正文含内嵌表格文本"}, set(), "内嵌表格文本正例"),
    ("完全无关的正文", TABLE_HTML_EMBEDDED, set(), {"正文含内嵌表格文本"}, "内嵌表格文本负例"),
    ("a", TABLE_HTML_JAGGED, {"表格列数不一致"}, set(), "列数阶梯正例（跳过表头后数据行差 2）"),
    ("a", TABLE_HTML_DIRTY, {"表格脏单元格"}, set(), "脏单元格 IN 正例（夹在双竖线间）"),
    ("123", TABLE_HTML_DIRTY_NUM, {"表格脏单元格", "正文含内嵌表格文本"},
     set(), "脏单元格纯数字正例（正文里出现同一单元格文本）"),
    ("abc", "<table><tr><td>a</td><td>b</td></tr></table>", set(),
     {"表格列数不一致", "表格脏单元格", "正文含内嵌表格文本"}, "规整表格负例"),
    ("thequickbrownfoxjumpsoverthelazydog", None, {"英文粘连"}, set(), "英文粘连正例（16+ 连写）"),
    ("ISO 9001", None, set(), {"英文粘连"}, "英文粘连负例（短词）"),
    ("正文内容\n12 GB 50016-2014", None, {"页脚/下节标题泄漏"}, set(), "页脚泄漏正例 GB 号（行尾/文末）"),
    ("正文内容\n12 总则与术语", None, {"页脚/下节标题泄漏"}, set(), "页脚泄漏正例 下节标题"),
    ("正文内容。", None, set(), {"页脚/下节标题泄漏"}, "页脚泄漏负例"),
    # 既有语义（已知边界，刻意不修）：页脚规则锚定**文本末尾**，GB 号后面还有正文就不算页脚
    ("正文内容\n12 GB 50016-2014\n后续正文", None, set(), {"页脚/下节标题泄漏"},
     "页脚泄漏负例：GB 号不在文末（既有语义）"),
    ("中文\n中文", None, {"正文换行残留"}, set(), "换行残留正例"),
    ("中文，中文", None, set(), {"正文换行残留"}, "换行残留负例（同行）"),
    ("", None, set(), {"正文换行残留", "英文粘连"}, "空正文"),
    ("", "", set(), {"正文含内嵌表格文本"}, "空表格 md"),
    ("<eq>x</eq> 取值", TABLE_HTML_EQ, set(),
     {"表格列数不一致", "表格脏单元格"}, "含公式实体的表格（html_to_text 兼容）"),
    ("x" * 10, TABLE_HTML_LONG, set(),
     {"正文含内嵌表格文本"}, "超长表格（>400 字被截断→已知漏检，见模块头注）"),
    ("AAA\nBBB\nCCC", None, {"正文换行残留"}, set(), "多行连续"),
    ("5.2.1 应按本条规定执行。", None, set(),
     {"正文换行残留", "页脚/下节标题泄漏", "英文粘连"}, "规范条款正文（干净）"),
    ("正文。\n\n（3）条文说明。\n\n正文继续。", None, set(), {"正文换行残留"}, "空行分隔不算换行残留"),
    # ---- 阈值边界（每条规则都要有"擦边不命中"用例，否则放松阈值不会被察觉）----
    ("characteristics", None, set(), {"英文粘连"}, "边界：15 字母不命中（阈值恰为 16）"),
    ("abcdefghijklmnop", None, {"英文粘连"}, set(), "边界：16 字母命中"),
    ("a", "<table><tr><td>h1</td><td>h2</td><td>h3</td></tr>"
          "<tr><td>a</td><td>b</td><td>c</td></tr><tr><td>d</td><td>e</td></tr></table>", set(),
     {"表格列数不一致"}, "边界：数据行列数差 1 不算不一致（阈值 ≥2）"),
    ("甲", "<table><tr><td>x</td><td>12</td><td>y</td></tr></table>", set(),
     {"表格脏单元格"}, "边界：中间列 2 位数字不命中（阈值 ≥3 位）"),
    ("正文内容\n123 总则与术语", None, set(), {"页脚/下节标题泄漏"}, "边界：3 位页码不命中（阈值 1~2 位）"),
    ("正文内容\n12 总则", None, set(), {"页脚/下节标题泄漏"}, "边界：标题仅 3 字不命中（阈值 ≥4 字）"),
    # 组合：多标签同时命中，且**顺序**必须与旧实现一致（页脚号放文末才会命中）
    ("公称直径\n4\n" + ("z" * 20) + "\n12 GB 50016-2014", TABLE_HTML_EMBEDDED,
     {"正文含内嵌表格文本", "英文粘连", "页脚/下节标题泄漏", "正文换行残留"}, set(), "多标签组合"),
]


@pytest.mark.parametrize("ct,md,must_in,must_out,label", CASES)
def test_qh_01_clause_health_diff_vs_inline(ct, md, must_in, must_out, label):
    """两件事一起锁：

    1. **等价性（反熵核心）**：新纯函数的 tags 必须与冻结副本**逐元素相等（含顺序）**；
    2. **非空性**：人工判定的正例必须命中、负例必须不命中（防"两边都错"或恒真规则）。

    FAIL 条件：`new != legacy`（抽取改变了行为），或 must_in 未全部出现 / must_out 出现任一。
    """
    new = clause_health(ct, md).tags
    legacy = _legacy_tags(ct, md)
    assert new == legacy, f"{label}: 新实现与冻结副本不一致 {new} != {legacy}"
    missing = must_in - set(new)
    leaked = must_out & set(new)
    assert not missing, f"{label}: 应命中但未命中 {sorted(missing)}（实际 {new}）"
    assert not leaked, f"{label}: 不应命中却命中 {sorted(leaked)}（实际 {new}）"


@pytest.mark.parametrize("html", [
    TABLE_HTML_EMBEDDED, TABLE_HTML_JAGGED, TABLE_HTML_DIRTY, TABLE_HTML_EQ, TABLE_HTML_LONG,
    "", None,
    "<table><tr><td></td><td> </td></tr></table>",
    "<tr><td>a</td></tr><tr><td>b</td></tr>",
    "<div>无表格</div>",
])
def test_qh_04_html_to_text_byte_identical(html):
    """表格 html→文本 必须与冻结副本**逐字符相等**（含 None/空/无表格）。"""
    assert clause_health_html_to_text(html) == _legacy_html_to_text(html)


def test_qh_04b_html_to_text_custom_limit():
    """limit 参数语义保持（旧签名有 limit 参数）。"""
    html = "<table><tr><td>" + ("字" * 100) + "</td></tr></table>"
    assert clause_health_html_to_text(html, 10) == _legacy_html_to_text(html, 10)
    assert len(clause_health_html_to_text(html, 10)) == 10


def test_qh_05_table_md_400_prefix_semantics():
    """`ClauseHealth.table_md` 保持"先 400 字截断"的既有语义（长表格漏检是已知缺陷，不在此修）。"""
    health = clause_health("x", TABLE_HTML_LONG)
    assert len(health.table_md) == 400
    assert health.table_md == ("长" * 400)


def test_qh_07_no_second_regex():
    """反熵：`src/core/quality/` 里不得出现第二套标准号/文件名正则，也不得 import scripts/。

    FAIL 条件：出现 GB/标准号形态的 `re.compile`（说明另造了一套识别规则），
    或 import 了 `scripts.`（脚本不是库）。
    """
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "src" / "core" / "quality"
    pattern = re.compile(r"re\.compile\(\s*r?[\"'].*(GB|DB\d{2}|JGJ|AQ|HJ|WS|YY|JB|HG|DL)")
    offenders = []
    for py in root.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{py.name}:{i}: {line.strip()}")
            if re.search(r"^\s*(from|import)\s+scripts\b", line):
                offenders.append(f"{py.name}:{i}: imports scripts")
    assert offenders == [], f"quality 包内出现第二套规则或脚本依赖: {offenders}"


# --------------------------------------------------------------------------- #
# 端点行为不变（抽取前该端点**零测试**，这两条是补上的回归网）
# --------------------------------------------------------------------------- #

_ISSUE_KEYS = {"clause_revision_id", "standard_no", "clause_number", "is_suspicious",
               "issues", "content_text", "table_md", "patched_fields"}


def _mk_doc(db, no: str, name: str):
    db.execute(
        "INSERT INTO doc_meta(doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, legal_status, legal_hierarchy, standard_type,"
        " doc_type, domain_tags, effective_from, published_at, ccs_code, ccs_name,"
        " superseded_by, withdrawn_date, catalog_hidden, file_path, file_hash)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (f"qdoc_{no.replace(' ', '')}", no, name, f"qsc_{no.replace(' ', '')}", "qrev",
         "effective", "GB", "mandatory", "standard", "[]", None, None,
         None, None, None, None, 0, f"C:/fake/{no}.pdf", f"qhash_{no}"))
    db.commit()


def _mk_clause(db, no: str, num: str, text: str, markdown: str | None = None):
    db.execute(
        "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
        " clause_key, clause_number, content_text, content_markdown, page_start,"
        " page_end, content_hash) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (f"qc_{no.replace(' ', '')}_{num}", "qrev", f"qdoc_{no.replace(' ', '')}",
         f"qk_{no}_{num}", num, text, markdown, 1, 1, f"qh_{no}_{num}"))
    db.commit()


@pytest.fixture()
def qworld(db):
    """播 5 条命中条款（跨 2 文档）+ 2 条干净条款；用完全链路清理防污染共享库。"""
    from src.core.storage import clause_repo
    from src.core.storage.clause_repo import ensure_catalog_hidden_column
    from src.core.storage.sqlite_db import get_db_connection

    # catalog_hidden 是 ensure 迁移列（与真实运行时一致先迁移）
    ensure_catalog_hidden_column()

    def clean():
        for r in get_db_connection().execute(
                "SELECT doc_id FROM doc_meta WHERE doc_id LIKE 'qdoc_%'").fetchall():
            clause_repo.delete_document(r["doc_id"])

    clean()
    _mk_doc(db, "GB 9001-2015", "假一号")
    _mk_doc(db, "GB 9002-2016", "假二号")
    # 命中：换行残留 / 英文粘连 / 页脚泄漏 / 内嵌表格文本 / 脏单元格
    _mk_clause(db, "GB 9001-2015", "1.1", "中文\n中文")
    _mk_clause(db, "GB 9001-2015", "1.2", "thequickbrownfoxjumpsoverthelazydog")
    _mk_clause(db, "GB 9001-2015", "1.3", "正文内容\n12 GB 50016-2014")
    _mk_clause(db, "GB 9002-2016", "1.1", "公称直径\n4", TABLE_HTML_EMBEDDED)
    _mk_clause(db, "GB 9002-2016", "1.2", "甲", TABLE_HTML_DIRTY_NUM)
    # 干净：不命中任何标签（用于证明端点不是"全表返回"）
    _mk_clause(db, "GB 9002-2016", "1.3", "5.2.1 应按本条规定执行。")
    _mk_clause(db, "GB 9001-2015", "1.4", "ISO 9001 质量管理体系。")
    yield
    clean()


def test_qh_02_quality_issues_endpoint_shape(client, qworld):
    """端点响应形状/键集合/截断长度必须与抽取前一致（FAIL：键多/少，或截断长度不符）。"""
    c, token = client
    r = c.get("/api/v1/data/quality-issues", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == 200 and body["status"] == "success"
    data = body["data"]
    # 5 条命中、2 条干净被排除
    assert len(data) == 5, [d["clause_number"] for d in data]
    assert body["total"] == 5
    for item in data:
        assert set(item) == _ISSUE_KEYS, set(item) ^ _ISSUE_KEYS
        assert isinstance(item["issues"], list) and item["issues"]
        assert len(item["content_text"]) <= 200 and len(item["table_md"]) <= 200
        assert isinstance(item["patched_fields"], list)
    clean_nums = {(d["standard_no"], d["clause_number"]) for d in data}
    assert ("GB 9002-2016", "1.3") not in clean_nums, "干净条款不该出现在体检结果里"


def test_qh_03_quality_issues_limit_break(client, qworld):
    """limit 早停语义 + SQL 排序保持（FAIL：返回 >limit 条，或不是排序后的前 N 条）。"""
    c, token = client
    hdr = {"Authorization": f"Bearer {token}"}
    full = c.get("/api/v1/data/quality-issues", headers=hdr).json()["data"]
    limited = c.get("/api/v1/data/quality-issues?limit=3", headers=hdr).json()["data"]
    assert len(limited) == 3
    assert [(d["standard_no"], d["clause_number"]) for d in limited] == \
           [(d["standard_no"], d["clause_number"]) for d in full[:3]]
    one = c.get("/api/v1/data/quality-issues?limit=1", headers=hdr).json()
    assert one["total"] == 1 and one["data"] == full[:1]

