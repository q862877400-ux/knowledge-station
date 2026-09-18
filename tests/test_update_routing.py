"""渠道路由测试（2026-08 巡检渠道升级）：select_chain 按标准号特征正确路由。

官方实测结论：AQ→ndls、GB 50/55→ndls、T/→ttbz、HJ→mee、DB→dbba、
其他国标→ndls、行标→hbba；无特征→泛查兜底 **official_gb→govcn**。

⚠ 2026-09-18（§11.0 R5c）：兜底链**摘掉了原来的第二棒 `web`**（bing）。
理由：`WebFallbackAdapter` 只解 `isinstance(body, dict)` 的 mock 契约，而它打的是 bing 的
**HTML** 搜索页 ⇒ 真实网络**恒 miss**（R1 的 G6 实测）；且搜索引擎**不是官方源**。
它的角色由两根真棒覆盖：`official_gb`（国标全文公开系统）+ `govcn`（政策文件库真接口，R5b 换棒）。
"""
from src.core.update.channels.routing import select_chain

#: 泛查兜底链的**期望顺序**（无特征命中时）。`web` 于 R5c 摘除，见模块 docstring。
TRAIL = ("official_gb", "govcn")


def test_route_aq_to_ndls():
    # 状态权威优先 ndls（跨门类，AQ 3028 作废已验证；mem_gov 作公告/全文辅助不占首选）
    chain = select_chain("AQ 3028-2008")
    assert chain[0] == "ndls"
    assert set(chain[1:]) == set(TRAIL)
    assert select_chain("AQ/T 3016-2008")[0] == "ndls"


def test_route_engineering_to_ndls():
    for no in ("GB 55037-2022", "GB 50140-2005", "GB 50444-2008"):
        assert select_chain(no)[0] == "ndls", no


def test_route_group_to_ttbz():
    assert select_chain("T/ZSA 328-2026")[0] == "ttbz"


def test_route_hj_to_mee():
    assert select_chain("HJ 819-2017")[0] == "mee"


def test_route_local_to_dbba():
    assert select_chain("DB11/T 3031-2022")[0] == "dbba"


def test_route_other_gb_to_ndls():
    assert select_chain("GB 18218-2018")[0] == "ndls"
    # 推荐性国标带斜杠走官方兜底（official_gb）
    assert select_chain("GB/T 50493-2019")[0] == "official_gb"


def test_route_industry_to_hbba():
    for no in ("MT/T 1000-2019", "YB/T 4000-2019", "JB/T 5000-2020"):
        assert select_chain(no)[0] == "hbba", no


def test_route_no_feature_falls_back():
    chain = select_chain("XYZ 9999-2099")
    assert chain == TRAIL


def test_route_foreign_prefix_no_match():
    # 无任何已知前导 → 泛查
    assert select_chain("ISO 9001:2015") == TRAIL


def test_降级链只有一个所有者():
    """§11.0 R6：兜底链**只有一份**，且 inspector 拿到的就是 routing 那个对象。

    背景（R5c 的教训）：`inspector.CHAIN` 与 `inspector._FALLBACK_CHAIN` 各自写了一份
    `("official_gb", ...)` 字面量 ⇒ "摘掉一棒"要改三处，改漏一处的现场表现是
    "巡检把失败归因到一根已经不存在的棒"（安静的错）。用 `is` 钉住同一对象，
    以后任何"再抄一份"的改动都会在这里红。
    """
    from src.core.update import inspector
    from src.core.update.channels import routing

    assert not hasattr(inspector, "CHAIN"), "CHAIN 是重复所有者（R6 已删），不许复活"
    assert inspector._FALLBACK_CHAIN is routing.fallback_chain(), (
        "inspector._FALLBACK_CHAIN 必须是 routing.fallback_chain() 返回的同一个 tuple 对象")
    assert routing.fallback_chain() is routing._FALLBACK, "唯一所有者在 routing._FALLBACK"
