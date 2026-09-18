"""渠道路由测试（2026-08 巡检渠道升级）：select_chain 按标准号特征正确路由。

官方实测结论：AQ→ndls、GB 50/55→ndls、T/→ttbz、HJ→mee、DB→dbba、
其他国标→ndls、行标→hbba；无特征→泛查兜底 **official_gb→ndls→govcn**。

⚠ 2026-09-18（§11.0 R5c）：兜底链**摘掉了原来的第二棒 `web`**（bing）。
理由：`WebFallbackAdapter` 只解 `isinstance(body, dict)` 的 mock 契约，而它打的是 bing 的
**HTML** 搜索页 ⇒ 真实网络**恒 miss**（R1 的 G6 实测）；且搜索引擎**不是官方源**。

⚠ 2026-09-18（§11.0 R6c-3b）：兜底链里**把 `ndls` 插到 `govcn` 前**。这是**量出来的**：
按前缀分层抽 10 个真库号实测命中率 —— `official_gb` 4/10、**`govcn` 1/10**
（唯一命中是`民法典`那类**法规**行）、`ndls` **6/10**，且 `govcn` 最慢（未命中时见过 7.1s）。
`GBZ 37-2024` / `GBZ/T 160.27-2004` 就是"`official_gb` miss、`ndls` 命中"的真例。
`govcn` **不删**（它是今天唯一能命中法规名行的那根），只是排到最后。
"""
from src.core.update.channels.routing import fallback_chain, select_chain

#: 泛查兜底链的**期望顺序**（无特征命中时）。`web` 于 R5c 摘除、`ndls` 于 R6c-3b 插到 govcn 前。
TRAIL = ("official_gb", "ndls", "govcn")


def test_route_aq_to_ndls():
    # 状态权威优先 ndls（跨门类，AQ 3028 作废已验证；mem_gov 作公告/全文辅助不占首选）
    chain = select_chain("AQ 3028-2008")
    assert chain[0] == "ndls"
    # 尾巴 = 兜底链减去"已经打头的自己"（R6c-3b 之后兜底链有三根，见模块 docstring）
    assert set(chain[1:]) == set(TRAIL) - {chain[0]}
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
    # 推荐性国标（GB/T）首选 official_gb（A/B 实测两者命中率都是 12/12，谁在前不改变"能不能答"，
    # 而 ndls 默认要发两次请求 ⇒ 保持"先命中即止"更省），但 **ndls 必须在它的链里**（R6c-3b）：
    # 一旦 official_gb miss（实测真例：GBZ 37-2024 / GBZ/T 160.27-2004），
    # 第二棒是状态权威 ndls，而不是基本不索引标准号的 govcn。
    chain = select_chain("GB/T 50493-2019")
    assert chain[0] == "official_gb"
    assert chain == TRAIL, chain


def test_全角号与半角号同链():
    """§11.0 R6c-3b：`select_chain` 是**第 7 个读原始号的站点**（R6c-2b 统一 6 个查询点漏了它）。

    ⚠ 两种情形要分开说（我第一版把理由写得比证据强，被自己核实纠正）：
    - `T／ZSA …`（全角）**确实**会因为匹配不上 `^T/\\b` 而掉进泛查兜底链、丢掉"团体标准→专门渠道"；
      这是**有真实差别**的那一类 ⬇；
    - `GB／T 14308-2010`（库里现存那 1 行全角）**没有差别**：半角的 `GB/T …` 同样不匹配 GB 规则
      （`^GB\\s?\\d{4,5}` 要求 GB 后就是数字）⇒ 两种写法本来都走泛查兜底。
      所以下面那条断言只是"形状不敏感"的护栏，**不能**当成"修好了一个漏路由的号"。
    """
    # 有真实差别的一类：全角 T／ 拿不到 ttbz（旧写法会掉进泛查兜底）
    assert select_chain("T/ZSA 328-2026")[0] == "ttbz"
    assert select_chain("T／ZSA 328-2026")[0] == "ttbz"
    assert select_chain("T／ZSA 328-2026") == select_chain("T/ZSA 328-2026")
    # 无差别的一类（护栏）：形状不同、链相同
    assert select_chain("GB／T 14308-2010") == select_chain("GB/T 14308-2010")
    assert select_chain("GB／T 14308-2010") == TRAIL


def test_前缀首选要问路由本身():
    """R6c-3b：`first_route` 是"前缀首选"的**唯一来源**。

    为什么单独立一条：`scripts/chain-snapshot.py` 原先靠"`select_chain(no)[0]` 不在兜底名单里"
    反推前缀首选——`ndls` 进兜底名单后，`GB`/`AQ` 这类以 ndls 打头的号被反推成"没有前缀首选"，
    快照于是报出**假差异**（实测 3 个样例被误报 ⚠ 变）。下面最后一行就是钉住这个陷阱。
    """
    from src.core.update.channels.routing import fallback_chain, first_route

    assert first_route("GB 18218-2018") == "ndls"
    assert first_route("T/CECS 2350-2026") == "ttbz"
    assert first_route("HJ 819-2017") == "mee"
    assert first_route("ISO 9001:2015") is None
    # ⚠ 陷阱本身：前缀首选**可以同时**是兜底成员（ndls 现在就是）——"不在名单里"不是判据
    assert first_route("GB 18218-2018") in fallback_chain()


def test_兜底链第二棒是状态权威而不是政策库():
    """R6c-3b 的核心断言（量出来的）：`ndls` 在 `govcn` 之前。

    实测（10 个真库号，按前缀分层）：`govcn` 只在**法规**行命中过 1 次，
    标准号上 0/9；`ndls` 命中 6/10。**这条用例红了就说明链又被改回去了。**

    ⚠ 第一句**必须问实现**（`fallback_chain()`），不能断言本文件顶部那个 `TRAIL` 字面量——
    复核 b34 的 F 项指出：断言自己的常量是**永真**的，任何实现下都过（等于没有这条护栏）。
    """
    assert fallback_chain().index("ndls") < fallback_chain().index("govcn")
    for no in ("GBZ 37-2024", "GBZ/T 160.27-2004", "HJ 819-2017", "AQ 3028-2008"):
        chain = select_chain(no)
        assert "ndls" in chain, no
        assert chain.index("ndls") < chain.index("govcn"), no


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
