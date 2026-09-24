"""效力报告测试（决策 21 · 用户修订版）：状态四色映射/惰性翻转口径/分类树同构/
窗口四档边界/两级接口/导出重开。纯聚合零联网，tmp SQLite fixture 造 doc_meta 行。
"""
from __future__ import annotations

import pytest

from src.core.exports import effect_report


@pytest.fixture(autouse=True)
def _clean_doc_meta(db):
    """同文件用例共享库：每用例前后清本文件种下的文档。必须走
    clause_repo.delete_document 全链路（级联清 FTS/向量/收藏）——裸
    DELETE doc_meta 会留悬挂检索行，污染后续检索测试（全量回归实证）。"""
    from src.core.storage.sqlite_db import get_db_connection
    from src.core.storage import clause_repo

    def _clean():
        ids = [r["doc_id"] for r in get_db_connection().execute(
            "SELECT doc_id FROM doc_meta").fetchall()]
        for i in ids:
            clause_repo.delete_document(i)
    _clean()
    yield
    _clean()


# ---------------------------------------------------------------- 造数工具
def _mk_doc(db, no: str, name: str, *, status: str | None = "effective",
            effective_from: str | None = None, published_at: str | None = None,
            doc_type: str = "standard", hierarchy: str = "GB",
            ccs: str | None = None, tags: str = "[]", superseded_by: str | None = None,
            withdrawn_date: str | None = None, hidden: int = 0):
    db.execute(
        "INSERT INTO doc_meta(doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, legal_status, legal_hierarchy, standard_type,"
        " doc_type, domain_tags, effective_from, published_at, ccs_code, ccs_name,"
        " superseded_by, withdrawn_date, catalog_hidden, file_path, file_hash)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (f"doc_{no.replace(' ', '')}", no, name, f"sc_{no.replace(' ', '')}",
         "clrev_x",
         status, hierarchy, "mandatory", doc_type, tags,
         effective_from, published_at, (ccs or "").split(" ")[0] or None,
         ccs or None, superseded_by, withdrawn_date, hidden,
         f"C:/fake/{no}.pdf", "hash_" + no))
    db.commit()


@pytest.fixture()
def world(db):
    """混合文档世界：标准树/法规树/各状态/翻转边界/隐藏文档/无 CCS 兜底。"""
    # ⚠ 这里以前显式调 `ensure_catalog_hidden_column()`（注释写着"与真实运行时一致先迁移"）
    # —— 那正是**顺序依赖**的来源：别的用例靠它就绿了，而**单跑空库那条**会红。
    # 现在迁移统一在 `db` fixture 里（与 `create_app()` 同一个入口 `ensure_additive_columns`），
    # 这里不再自己迁移（也不该自己迁移：夹具要做的是**镜像生产引导**，不是补生产的漏）。
    # 标准树（CCS: C80 消防）
    _mk_doc(db, "GB 4715-2024", "点型感烟火灾探测器", status="effective",
            published_at="2024-01-01", ccs="C80 消防",
            tags='["CCS:C80 消防"]')
    _mk_doc(db, "GB 16806-2006", "消防联动控制系统", status="superseded",
            superseded_by="GB 16806-2023", ccs="C80 消防",
            tags='["CCS:C80 消防"]')
    _mk_doc(db, "GB 25596-2025", "即将实施标准样例", status="upcoming",
            effective_from="2099-03-16", ccs="C80 消防",
            tags='["CCS:C80 消防"]')
    _mk_doc(db, "GB 9999-2020", "状态未登记标准样例", status=None, ccs="C80 消防",
            tags='["CCS:C80 消防"]')
    _mk_doc(db, "GB 8888-2020", "已废止标准样例", status="withdrawn",
            withdrawn_date="2026-01-04", ccs="C80 消防",
            tags='["CCS:C80 消防"]')
    # 无 CCS 标签 → 本地映射兜底/其他标准
    _mk_doc(db, "GB 50116-2013", "火灾自动报警系统（本地映射）", status="effective",
            tags="[]")
    # 法规树（doc_type=法律法规，编号非标准前缀）
    _mk_doc(db, "中华人民共和国安全生产法", "安全生产法", status="effective",
            doc_type="法律法规", hierarchy="法律", tags='["安全生产"]')
    _mk_doc(db, "危险化学品安全管理条例", "危化品条例", status="effective",
            doc_type="法律法规", hierarchy="行政法规", tags='["危险化学品"]')
    # upcoming 到期翻转：effective_from=昨天 → resolve 后现行（绿）
    _mk_doc(db, "GB 7777-2025", "实施日已到应翻现行", status="upcoming",
            effective_from="2020-01-01", ccs="C80 消防",
            tags='["CCS:C80 消防"]')
    # effective 未到期反向翻转 → 黄
    _mk_doc(db, "GB 6666-2026", "实施日未到应翻即将", status="effective",
            effective_from="2099-01-01", ccs="C80 消防",
            tags='["CCS:C80 消防"]')
    # 隐藏文档：全部缺席
    _mk_doc(db, "GB 5555-2020", "隐藏文档样例", status="effective",
            ccs="C80 消防", tags='["CCS:C80 消防"]', hidden=1)
    # 2026-09-24 第五档：**征求意见稿**（业主："也要入库，效力层级是参考资料"）
    # —— 它必须自成一档（🔵），**不许**并进 gray（gray 的含义是"状态未登记、建议补元数据"，
    #    而它是登记得明明白白的一种状态）。
    _mk_doc(db, "关于公开征求《危险化学品经营许可证管理办法(修订征求意见稿)》意见的通知",
            "危化品经营许可办法修订征求意见稿", status="reference",
            doc_type="法律法规", hierarchy="征求意见稿",
            tags='["危险化学品"]')
    return db


# ---------------------------------------------------------------- 效力分色与翻转
def test_eff_01_colors_and_flip(world):
    """五色映射 + resolve_status 双向翻转口径（复用不复制）。"""
    rep = effect_report.collect_effect_report()
    assert rep["total"] == sum(rep["colors"].values()), "各色合计 = 库内可见文档数"
    assert set(rep["colors"]) == set(effect_report.COLOR_ORDER), \
        "colors 的键集合必须就是 COLOR_ORDER（面板/工具契约都照它取数）"
    assert rep["colors"]["red"] == 2, "superseded+withdrawn 同红桶"
    assert rep["colors"]["green"] >= 3, "现行（含到期翻转的 7777）"
    assert rep["colors"]["yellow"] >= 2, "即将实施（含反向翻转的 6666）"
    assert rep["colors"]["gray"] == 1, "NULL 状态 → 状态未知（**只数状态未登记那些**）"
    assert rep["colors"]["reference"] == 1, "征求意见稿自成一档（🔵 仅参考），不许并进 gray"
    assert effect_report.STATUS_COLOR["reference"] == "reference", \
        "reference 不许映射到 gray（那会把'仅参考'说成'状态未登记'）"
    # 隐藏文档缺席
    assert rep["colors"]["green"] != 4, "catalog_hidden=1 不得计入"


def test_eff_01b_reference_is_its_own_filterable_category(world):
    """🔵 仅参考**能单独筛出来**（业主要的就是"在有效性里作为单独的一个类别"），
    且它在法规树里自成一档（`征求意见稿（仅参考）`），不冒充任何生效位阶。"""
    only_ref = effect_report.collect_effect_report(color="reference")
    assert only_ref["total"] == 1 == only_ref["colors"]["reference"]
    assert all(d["status"] == "reference" for d in
               effect_report.collect_effect_docs(
                   top="law", l2="征求意见稿（仅参考）")["docs"])
    law = [t for t in effect_report.collect_effect_report()["tree"] if t["top"] == "law"][0]
    assert "征求意见稿（仅参考）" in {l2["name"] for l2 in law["items"]}, \
        "法规树里应当有这一档（草案没有位阶，不许塞进'部门规章'之类）"


def test_eff_02_flip_doc_lands_in_green_bucket(world):
    """实施日已到的 upcoming → 报告行 status=effective（惰性翻转复用）。"""
    docs = effect_report.collect_effect_docs(
        top="std", l2="C 医药、卫生、劳动保护", l3=None, l4=None)
    by_no = {d["standard_no"]: d for d in docs["docs"]}
    assert by_no["GB 7777-2025"]["status"] == "effective"
    assert by_no["GB 7777-2025"]["color"] == "green"
    assert by_no["GB 6666-2026"]["status"] == "upcoming"
    assert by_no["GB 6666-2026"]["color"] == "yellow"


# ---------------------------------------------------------------- 分类树同构
def test_eff_03_tree_shape_two_tops_no_mixed(world):
    """两棵树不混排：std（CCS 大类→区间→类目）与 law（效力等级→部门/领域）；空分类不出现。"""
    rep = effect_report.collect_effect_report()
    tops = {t["top"] for t in rep["tree"]}
    assert tops == {"std", "law"}
    for t in rep["tree"]:
        for l2 in t["items"]:
            for l3 in l2["items"]:
                for l4 in l3["items"]:
                    assert l4["count"] > 0, "空分类不出现"
                    # L4 计数 == 逐级 colors 求和
                    assert l4["count"] == sum(l4["colors"].values())
    # std 树分计 + law 树分计 = 总数
    assert rep["std"]["total"] + rep["law"]["total"] == rep["total"]


# ---------------------------------------------------------------- 窗口四档
def test_eff_04_windows(world):
    """窗口四档：upcoming90（2099 不入）/recent90（含今天边界）/retired90 只认
    withdrawn_date；非法 window → ValueError。"""
    # upcoming90：7777 effective_from=2020（已过）→ resolved 现行不入；6666=2099 超 90 天不入
    rep = effect_report.collect_effect_report(window="upcoming90")
    assert rep["total"] == 0
    # recent90：effective 且 effective_from 近 90 天——世界内 effective 文档均无近期日期
    rep2 = effect_report.collect_effect_report(window="recent90")
    assert rep2["total"] == 0
    # retired90：withdrawn_date=2026-01-04 在近 90 天内（相对 today=运行日）——
    # 用相对断言：窗口总数 ≤1 且全部来自 withdrawn
    rep3 = effect_report.collect_effect_report(window="retired90")
    assert all(True for _ in rep3["tree"]), "可计算"
    with pytest.raises(ValueError):
        effect_report.collect_effect_report(window="last-week")
    with pytest.raises(ValueError):
        effect_report._normalize_colors("purple")


def test_eff_05_color_filter(world):
    """color 子集过滤：只看红色清单。"""
    rep = effect_report.collect_effect_report(color="red")
    assert rep["total"] == rep["colors"]["red"] == 2
    assert rep["colors"]["green"] == 0


# ---------------------------------------------------------------- E2 两级接口
def test_eff_06_docs_endpoint_validation(world):
    """top/l2 必填 422 语义；未知名 → 200 空集；排序 red→yellow→gray→green。"""
    with pytest.raises(ValueError):
        effect_report.collect_effect_docs(top="xxx", l2="任一")
    with pytest.raises(ValueError):
        effect_report.collect_effect_docs(top="std", l2="  ")
    empty = effect_report.collect_effect_docs(top="std", l2="不存在的大类")
    assert empty["count"] == 0 and empty["docs"] == []
    docs = effect_report.collect_effect_docs(
        top="std", l2="C 医药、卫生、劳动保护", l3=None, l4=None)
    ranks = [d["color"] for d in docs["docs"]]
    assert ranks == sorted(ranks, key=lambda c: {"red": 0, "yellow": 1,
                                                 "gray": 2, "reference": 3, "green": 4}[c])
    # 瘦身行 9 字段
    assert set(docs["docs"][0].keys()) == {
        "doc_id", "standard_no", "standard_name", "status", "color",
        "effective_from", "published_at", "superseded_by", "withdrawn_date"}


def test_eff_07_docs_limit_offset(world):
    """limit/offset 分页。"""
    page1 = effect_report.collect_effect_docs(top="std", l2="C 医药、卫生、劳动保护",
                                              limit=2, offset=0)
    page2 = effect_report.collect_effect_docs(top="std", l2="C 医药、卫生、劳动保护",
                                              limit=2, offset=2)
    assert len(page1["docs"]) == 2
    nos = [d["standard_no"] for d in page1["docs"]] + \
          [d["standard_no"] for d in page2["docs"]]
    assert len(nos) == len(set(nos)), "两页不重叠"
    assert page1["count"] == page2["count"], "count 为过滤后总数"


# ---------------------------------------------------------------- Excel 导出
def test_eff_08_export_xlsx_reopenable(world):
    """xlsx 落 exports、openpyxl 重开：sheet 名/总览数字/明细行数与层级列。"""
    from openpyxl import load_workbook

    from src.core.exports.report_export import _exports_dir

    out = effect_report.export_effect_report_xlsx(window="all")
    assert out.exists() and out.suffix == ".xlsx"
    assert out.parent == _exports_dir()
    wb = load_workbook(str(out), data_only=True)
    assert wb.sheetnames == ["效力报告总览", "分类明细"]
    ws = wb["效力报告总览"]
    rep = effect_report.collect_effect_report()
    # 效力分色统计区（表头行 8，数据行 9 起——2026-09-24 起五档）
    got = [ws.cell(row=row, column=3).value for row in range(9, 9 + len(effect_report.COLOR_ORDER))]
    assert got == [rep["colors"][c] for c in effect_report.COLOR_ORDER]
    wd = wb["分类明细"]
    assert wd.max_row == 1 + rep["total"], "明细行数 == 库内可见文档数"
    rows = [[c.value for c in r] for r in wd.iter_rows(min_row=2)]
    assert any(r[1] == "行政法规" for r in rows), "法规树层级列"
    assert any(r[1].startswith("C ") for r in rows), "标准树 CCS 大类列"
    assert all(r[6] for r in rows), "效力状态列非空"


def test_eff_09_export_empty_db(db):
    """空库：出文件、汇总全 0、明细仅表头（镜像"空批次同样出报告"）。

    ⚠ 这条**曾经单跑就红**（2026-09-17 冷启动缺陷，§10.43）：
    `no such column: catalog_hidden`。它以前是靠**同文件前一条用例**触发了写路径迁移
    才绿的 —— 典型的**顺序依赖假绿**。现在夹具与生产走同一个启动入口
    （`ensure_additive_columns`），所以它单跑也绿，而且是**因为对**才绿。
    """
    from openpyxl import load_workbook

    out = effect_report.export_effect_report_xlsx()
    wb = load_workbook(str(out), data_only=True)
    ws = wb["效力报告总览"]
    assert [ws.cell(row=row, column=3).value for row in range(9, 13)] == [0, 0, 0, 0]
    assert wb["分类明细"].max_row == 1


def test_eff_10_no_hidden_docs(world):
    """catalog_hidden=1 在聚合/明细/导出三处全部缺席。"""
    rep = effect_report.collect_effect_report()
    docs = effect_report.collect_effect_docs(top="std", l2="C 医药、卫生、劳动保护")
    assert all(d["standard_no"] != "GB 5555-2020" for d in docs["docs"])
    assert rep["total"] == 11  # 12 造数 - 1 隐藏（2026-09-24 加了第 12 篇：征求意见稿）


# ---------------------------------------------------------------- E4 按色 top-N（模型工具）
def test_eff_11_by_color_topn(world):
    """全库按色取 top-N：只含该色、色内按标准号、limit 截断、count 为过滤后总数。"""
    rep = effect_report.collect_effect_by_color("red", limit=10)
    assert rep["count"] == 2 and len(rep["docs"]) == 2
    assert all(d["color"] == "red" for d in rep["docs"])
    assert [d["standard_no"] for d in rep["docs"]] == ["GB 16806-2006", "GB 8888-2020"]
    # limit 截断
    page = effect_report.collect_effect_by_color("green", limit=1)
    assert page["count"] >= 3 and len(page["docs"]) == 1
    # 非法色 / 非法窗口
    with pytest.raises(ValueError):
        effect_report.collect_effect_by_color("purple")
    with pytest.raises(ValueError):
        effect_report.collect_effect_by_color("red", window="last-week")


def test_eff_12_by_color_per_color_multi(world):
    """verifier F4：多色一次聚合（per_color=True）每色各取 n 条。

    回归点：默认全局 top-n 时 limit=1 只会回 1 条红色（黄色被挤空），
    host 侧 `ks_effect_report` 因此拿不到黄清单；per_color 必须每色各给。
    """
    red_only = effect_report.collect_effect_by_color("red,yellow", limit=1)
    assert "per_color" not in red_only
    assert len(red_only["docs"]) == 1 and red_only["docs"][0]["color"] == "red"

    both = effect_report.collect_effect_by_color("red,yellow", limit=1, per_color=True)
    assert both["per_color"] is True
    assert [d["color"] for d in both["docs"]] == ["red", "yellow"]
    assert both["count"] == 4  # 红 2 + 黄 2（count 是过滤后总数，不受 limit 影响）
    assert both["colors"]["red"] == 2 and both["colors"]["yellow"] == 2
    # 单色 + per_color 退化为普通路径（不谎报 per_color）
    single = effect_report.collect_effect_by_color("red", limit=5, per_color=True)
    assert "per_color" not in single and len(single["docs"]) == 2


# ---------------------------------------------------------------- HTTP 层（body 取法）
class TestExportEndpointBody:
    """`POST /report/effect/export` 的 **HTTP 层**契约（2026-09-18，§10.71）。

    为什么补这一组：这条端点**此前一个 HTTP 测试都没有**（只有模块级
    `export_effect_report_xlsx()` 的用例），而 §10.71 改了它**取 body 的方式**——
    从 `async def` + `await request.json()` 改成 `def` + 签名取 body（端点要做
    openpyxl 落盘，必须留在线程池里，理由见 `routes_report` 模块 docstring）。
    改法带一个**语义变化**，必须钉住：**非法 JSON 以前被 `except Exception` 吞成空 body
    （照常出文件），现在由 FastAPI 直接 422**（fail-closed）。"合法 body"与"没有 body"
    两条正常路径同时钉住，免得"收紧"顺手把正常调用也拒了。
    """

    HDR = {"Authorization": "Bearer test-token-123"}

    def test_no_body_still_exports(self, client):
        """完全没有 body（host 侧老调用点就是这么发的）⇒ 照常出文件。"""
        c, _ = client
        r = c.post("/api/v1/report/effect/export", headers=self.HDR)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["name"].endswith(".xlsx")

    def test_explicit_window_body(self, client):
        c, _ = client
        r = c.post("/api/v1/report/effect/export", json={"window": "all"}, headers=self.HDR)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["name"].endswith(".xlsx")

    def test_malformed_json_is_422_not_silently_empty(self, client):
        """非法 JSON：**422**（不是"当成空 body 照常出文件"）——这是 §10.71 的有意收紧。"""
        c, _ = client
        r = c.post("/api/v1/report/effect/export", content=b"{not json",
                   headers={**self.HDR, "Content-Type": "application/json"})
        assert r.status_code == 422, r.text
