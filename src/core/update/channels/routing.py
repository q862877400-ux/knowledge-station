"""渠道适配器索引：新增渠道在此注册，inspector 按标准号特征路由。

渠道分层（2026-08 四队实测，见 docs/LAW_SOURCE_PLAN.md 附 B）：
- mem_gov：AQ 行业标准状态（应急部公告）+ 全文（标准文本 PDF）
- std_samr_hb：行业标准目录状态（std.samr /hb/search/hbPage JSON）
- hbba：行业标准平台（POST /stdQueryList）
- dbba：地方标准平台（POST /stdQueryList）
- ndls：国家数字标准馆（跨门类状态+废止日期+代替链）
- mohurd：工程建设标准（住建部公告）
- ttzb：团体标准（ttbz 详情 JSON-LD）
- mee：生态环境 HJ（状态弱信号 + 全文下载链接逆向）
"""
from __future__ import annotations

import re

from src.core.text_utils import store_standard_no


def _store_form(standard_no: str | None) -> str:
    """标准号 → 存储形（去空白 + 折半角），供前缀匹配用。

    ⚠ **只此一处**：R6c-2b 已经吃过"每个站点各折一次、漏一个就静默失败"的亏，
    所以这里也是唯一入口——别再在调用方各折各的。
    """
    return store_standard_no((standard_no or "").strip())

# 标准号 → 首选权威渠道（其余走本模块的兜底链 `_FALLBACK`：official_gb→ndls→govcn）
# 状态权威优先 ndls（跨门类，能判 现行/废止/废止日期/代替关系；AQ 3028→作废 2024-07-01 已验证）；
# mem_gov/mohurd 作为 公告+全文 辅助（页面 CMS/JS 结构，图文状态不全，不占状态首选）。
_PREFIX_ROUTE: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(?:AQ/T?\b|AQ)"), "ndls"),                     # 应急管理行业标准→ndls（状态权威）
    (re.compile(r"^T/\b"), "ttbz"),                               # 团体标准→ttbz（专门渠道）
    (re.compile(r"^GB\s?(?:50|55)\d{3}\b"), "ndls"),              # 工程建设标准→ndls（状态权威）
    (re.compile(r"^GB\s?\d{4,5}\b"), "ndls"),                     # 其他国标→ndls（跨门类状态）
    (re.compile(r"^HJ\b", re.I), "mee"),                          # 生态环境标准→mee（含全文逆向）
    (re.compile(r"^DB\d"), "dbba"),                               # 地方标准→dbba
    (re.compile(r"^(?:MT|YB|JB|HG|QB|NY|SL|SN|JB|SH|JGT?|CJJ|CJ)\b", re.I), "hbba"),  # 行业标准→hbba
]

# 兜底：无特征命中时按此顺序（泛查链）
# ⚠ 2026-09-18（§11.0 R5c）：**摘掉 `web`**。理由（R1 的 G6 + R5b 的实测）：
#   `web_fallback.WebFallbackAdapter` 只解 `isinstance(body, dict)`（mock 契约），
#   而它打的是 bing 的 **HTML 搜索页** ⇒ 真实网络下**恒 miss**，每次探测都白花一次请求，
#   而且搜索引擎**不是官方源**（与"不依赖二手信息"的准则相冲突）。
#   它的角色由两根真棒覆盖：`official_gb`（国标全文公开系统）+ `govcn`（政策文件库真接口，R5b 换棒）。
#   `ADAPTER_CLASSES` 里仍保留 `web`（不删代码），只是**不进任何链**——台账据此显示"未接线"。
#
# ⚠ 2026-09-18（§11.0 R6c-3b）：**把 `ndls` 插在 `govcn` 前面**。这是**量出来的**，不是拍脑袋：
#   `govcn` 是**政策/法规库**，在标准号上基本不命中——按前缀分层抽 10 个真库号实测：
#   `official_gb` 命中 4/10、**`govcn` 1/10**（唯一那次命中是`民法典`那类的**法规**行）、`ndls` **6/10**；
#   且 `govcn` 还最慢（未命中时见过 7.1s，`ndls` 只要 1.2s）。
#   `ndls`（国家数字标准馆）是**跨门类状态权威**，正是 `GBZ 37-2024` / `GBZ/T 160.27-2004`
#   这种"`official_gb` miss 而它命中"的号该走的第二棒。
#   为什么**不是**把 `ndls` 提到 `official_gb` 前面：A/B 实测两者在 `GB/T` 上命中率都是 12/12，
#   谁在前不改变"能不能答"；而 `ndls` 默认要发**两次**请求（搜索+详情），保持 `official_gb` 在前
#   就仍是"先命中即止、不额外发请求"。⇒ 只在**第一棒 miss 时**顺序更合理。
#   （`govcn` 不删：它是今天唯一能命中**法规名**行的那根——实测命中 1 次就是法规。）
_FALLBACK = ("official_gb", "ndls", "govcn")


def fallback_chain() -> tuple[str, ...]:
    """泛查兜底链的**唯一访问点**（§11.0 R6）。

    为什么要有这个函数，而不是让调用方自己写一份字面量：`inspector` 原先也抄了一份
    `_FALLBACK_CHAIN = ("official_gb", "govcn")`——于是 R5c 摘 `web` 时**必须改两处**，
    改漏一处的现场表现是"巡检把失败归因到一根不存在的棒"，很难看出来。
    现在 inspector 导入本函数，拿到的是**同一个 tuple 对象**（用例用 `is` 钉住这一点）。
    """
    return _FALLBACK


def first_route(standard_no: str) -> str | None:
    """这一号的**前缀首选**渠道（没命中任何前缀规则 ⇒ `None`）。

    为什么要单独暴露它（§11.0 R6c-3b）：`scripts/chain-snapshot.py` 原先靠
    "`select_chain(no)[0]` 不在兜底名单里 ⇒ 它是前缀首选"来推断——R6c-3b 把 `ndls`
    插进兜底名单后，`GB`/`AQ` 这类**以 ndls 打头**的号就被误判成"没有前缀首选"，
    于是快照把 3 个样例报成"⚠ 链会变"（**假差异**）。推断规则本来就该问路由本身，
    而不是靠"不在名单里"这种反推。现在两边都从这里取，谁改都不会再错位。
    """
    no = _store_form(standard_no)
    for pat, ch in _PREFIX_ROUTE:
        if pat.match(no):
            return ch
    return None


def select_chain(standard_no: str) -> tuple[str, ...]:
    """按标准号特征返回降级链（首选权威渠道在前，其余兜底在后）。

    ⚠ **原始号先折半角再匹配**（§11.0 R6c-3b）：R6c-2b 统一了 6 个"查询侧"站点，
    但**漏了这里**——`select_chain` 是第 7 个读原始号的站点。用的是**存储形**
    `store_standard_no`（只折 `／`/`－`，不动空格大小写），与写库侧同一口径：别再抄一份替换表。

    ⚠ **这个折叠到底修了什么，说准确**（我第一版把理由写得比证据强，自己核实时改掉）：
    - **有真实差别的**是那些"前缀规则里就带斜杠"的号：`T／ZSA 328-2026`（全角）匹配不上
      `^T/\\b`，于是**静默掉进泛查兜底链**、丢掉"团体标准→专门渠道"的首选（半角写法不会）。
      这类号今天库里没有，但规则在，入口也在。
    - **没有差别的**：`GB／T 14308-2010`（库里现存那 1 行全角）——半角的 `GB/T …` 同样不匹配
      任何 GB 规则（`^GB\\s?\\d{4,5}` 要求 GB 后就是数字），所以这一行**旧写法也没丢首选**。
      我最初写的是"它掉了国标→状态权威的首选"，**那句是错的**，用例里也一并纠正。
    """
    first = first_route(standard_no)
    if first is None:
        return _FALLBACK
    chain = [first]
    for c in _FALLBACK:
        if c != first:
            chain.append(c)
    return tuple(chain)


def _fold_segment(raw: str | None) -> str:
    """号段写法与标准号**共用的折叠口径**（`_store_form` + 去掉所有空白）。

    为什么还要去空白（§11.0 R7）：号段是**人写进台账**的，`GB 50` 与 `GB50` 是同一个人
    隔一天可能写出的两种写法；而库里的号有的带空格（`GB 30871-2022`）、有的不带。
    两边都去空白后，台账里写 `GB50` / `GB 50` 都能命中同一批号 —— 否则"写法差异"会表现成
    "我明明填了号段，它就是不进链"。⚠ 代价：`GBT` 这种写法会同时命中 `GB T …`；
    号段本就是**前缀**、不是全等，这个代价以文档写明、不隐藏。
    ⚠ **大小写不折叠**（复核 2026-09-19 提醒：这条原先没写明）：台账里写 `hj` / `Gb/t`
    **永远不命中**。刻意如此——标准号本身大写（`HJ 1234-2020`），`hj` 更可能是手滑；
    但"手滑会静默失效"必须写在人看得到的地方（面板提示语与这里各一处）。
    """
    return re.sub(r"\s+", "", _store_form(raw))


def segment_matches(standard_no: str, segment: str) -> bool:
    """这一号的**存储形**是否落在该号段内（前缀匹配；两侧同一折叠口径）。

    ⚠ 这里是号段匹配的**唯一实现**：`ledger_chain.chain_for_number` 与报告都从这里走，
    别在调用方各折各的（R6c-2b 已吃过"每个站点各折一次、漏一个就静默失败"的亏）。
    """
    seg = _fold_segment(segment)
    if not seg:
        return False
    return _fold_segment(standard_no).startswith(seg)
