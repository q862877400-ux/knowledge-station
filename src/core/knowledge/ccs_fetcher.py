"""入库/补全时查询中国标准分类号（CCS）——**一条链、来源有序、每条都记来源**。

════════════ 这条链是什么（2026-09-22 重做，业主口径「修机制不是补数据」）════════

**① 官方接口** ``cssn /api/standards/list``（JSON，字段 ``a825``=CCS 码、``a825name``=类名）
→ **② 网页抓取** ``cssn /api/cssn/list``（HTML 列表页，``【CCS分类】`` 标签）
→ **③ 本地兜底** ``LOCAL_CCS``（人工核实表） + 种子文件（``KS_CCS_SEED_FILE``，命中零网络）。

**每一篇都要能说出**：是哪一层命中的、前几层为什么没命中、命中的是**哪种关键词形式**
（``full`` 完整号 / ``compact`` 去空格 / ``core`` 数字主体含分部号 / ``bare`` 数字首段）。
这些都随结果返回，并可由 ``ccs_store`` 落进 ``doc_ccs_state`` 供审计与界面查。

════════════ 为什么重做（旧实现的三个真毛病，都有实测取证）════════════

1. **请求根本发不出去，却显示"查无"**。旧实现 ``httpx.Client(...)`` 在本机环境
   （``NO_PROXY`` 含 ``[::1]``）**构造即抛** ``InvalidURL: Invalid port: ':1]'``，
   而外层是 ``except Exception: return None`` ⇒ **0.1 秒返回 None**，看上去像
   "官方没有这个号"。实测：``fetch_ccs("GB 1094.2-2013")`` 0.1s 返回 None，
   同一时刻官方接口其实**有**它（``GB/T 1094.2-2013`` / ``K41 变压器``）。
   ⇒ 现在统一走 ``channels.base.default_transport()``（curl_cffi 优先、httpx 兜底
   且**带自检**），本模块**不再自己 new 一个 HTTP 客户端**。
2. **把标准号抠成裸数字去搜**（``\\d{4,6}`` ⇒ ``1094``），返回的 20 条一条都不是要的。
   ⇒ 现在按 **完整号 → 去空格变体 → 数字主体（含分部号） → 数字首段** 依次试，
   每次都在结果里按**归一化标准号精确匹配**（``norm_no``），并记录**哪种形式命中**。
3. **网页那一路的块边界锚错了元素**。旧实现按 ``a301``（**标题**）切块，再拿标准号去
   **标题文本**里找 ⇒ 永不相等。实测同一页里 ``GB/T 1094.3-2017`` 的 CCS 就在
   ``K41变压器``，而旧实现 20 条一条都挑不出来（标题是"电力变压器 第3部分…"）。
   正确锚点是 ``class="ph_list_title"``（**标准号**本身）：实测条目顺序是
   **号在前、标题与 CCS 在后**（对齐已验证，见 ``_parse_html_items``）。

════════════ 失败**不静默**（降级可以，必须留痕）════════════

每次查询都返回一个 ``outcome``，四选一，**不许把"发不出去"说成"官方查无"**：

* ``found``          —— 某一层命中；
* ``not_found``      —— 网络层**确实答了**，但结果里没有这个号（官方/网页查无）；
* ``network_failed`` —— 所有网络层都在**传输层**失败（超时/不可达/构造不出来）；
* ``parse_failed``   —— 答了但**解不开**（JSON 坏 / HTML 结构变了 / CCS 标签缺失）。

调用方（``pipeline`` 入库、``ccs_backfill`` 自愈）拿这个 outcome 落 ``doc_ccs_state``，
界面上就能看见"这一篇没有分类号：查询失败"还是"官方查无"。
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from src.core.update.channels.base import looks_like_captcha

logger = logging.getLogger("ks.knowledge.ccs")

# ─────────────────────────────── 层与来源 ───────────────────────────────

#: 来源（命中它的那一层）。有序 = 这就是优先级。
SOURCE_OFFICIAL_API = "official_api"
SOURCE_WEB_SCRAPE = "web_scrape"
SOURCE_LOCAL_TABLE = "local_table"
SOURCE_SEED_FILE = "seed_file"
#: 有序来源表（文档/界面照这个顺序讲"第几层"）
SOURCES: tuple[str, ...] = (SOURCE_OFFICIAL_API, SOURCE_WEB_SCRAPE,
                            SOURCE_LOCAL_TABLE, SOURCE_SEED_FILE)
SOURCE_LABELS: dict[str, str] = {
    SOURCE_OFFICIAL_API: "官方接口",
    SOURCE_WEB_SCRAPE: "网页抓取",
    SOURCE_LOCAL_TABLE: "本地对照表",
    SOURCE_SEED_FILE: "本地种子文件",
}

#: 查询结论（四枚举，**不设"未知"** —— 每种失败都有自己的名字）
OUTCOME_FOUND = "found"
OUTCOME_NOT_FOUND = "not_found"
OUTCOME_NETWORK_FAILED = "network_failed"
OUTCOME_PARSE_FAILED = "parse_failed"
OUTCOMES: tuple[str, ...] = (OUTCOME_FOUND, OUTCOME_NOT_FOUND,
                             OUTCOME_NETWORK_FAILED, OUTCOME_PARSE_FAILED)
OUTCOME_LABELS: dict[str, str] = {
    OUTCOME_FOUND: "已补全",
    OUTCOME_NOT_FOUND: "查无（答话的站点里都没有这个号）",
    OUTCOME_NETWORK_FAILED: "查询失败（网络不通/被拦，一个站点都没答上）",
    OUTCOME_PARSE_FAILED: "读不出来（站点答了，但没有分类号或读不出条目）",
}

#: 关键词形式的说法（记录"哪一种形式命中"，界面/审计可查）
FORM_LABELS: dict[str, str] = {
    "full": "完整标准号",
    "compact": "去空格变体",
    "core": "数字主体（含分部号）",
    "bare": "数字首段",
}


class _LayerFacts:
    """一层网络查询跑完后的三个事实（**结论由这三个事实算出来，不靠猜**）。

    * ``saw_response``   —— 传输层答了（拿到过 HTTP 回应）；
    * ``saw_parseable``  —— 至少有一种关键词形式解出了**条目列表**；
    * ``no_ccs_seen``    —— 标准号在站点上**找到了**，但那一行/那一条**没有分类号**。

    ⇒ ``saw_response=False`` 才是"发不出去"；只要答过、且解得出条目列表，"没有这个号"
    才是官方查无。旧实现把这两件事混成一个 ``None``，现场表现为"0.1 秒查无"。
    """

    __slots__ = ("saw_response", "saw_parseable", "no_ccs_seen")

    def __init__(self) -> None:
        self.saw_response = False
        self.saw_parseable = False
        self.no_ccs_seen = False

    def verdict(self) -> str:
        """本层结论（四枚举之一；命中不在这里表达 —— 命中会直接 return）。"""
        if self.no_ccs_seen:
            return OUTCOME_PARSE_FAILED       # 号找到了，站点却没给分类号
        if self.saw_parseable:
            return OUTCOME_NOT_FOUND          # 站点答了、解得出条目，就是没有这个号
        if self.saw_response:
            return OUTCOME_PARSE_FAILED       # 答了，但一种形式都解不出条目
        return OUTCOME_NETWORK_FAILED         # 一种形式都没答上（传输层）


def _combine_verdicts(verdicts: list[str]) -> str:
    """两层网络查询的结论合成**一个**如实的总结论。

    规则（三条互斥、覆盖全部情形）：

    1. **一个站点都没答上** ⇒ ``network_failed``（"发不出去"永远不许被说成"查无"）；
    2. 有站点答上了，但其中任何一层**答而读不出**（结构变了 / 有这个号但不给分类号）
       ⇒ ``parse_failed`` —— 宁可说"读不出"，也不把一件读不出的情况压成"查无"；
    3. 其余（答上的层都解出了条目、且里面确实没有这个号）⇒ ``not_found``。
    """
    answered = [v for v in verdicts if v != OUTCOME_NETWORK_FAILED]
    if not answered:
        return OUTCOME_NETWORK_FAILED
    if any(v != OUTCOME_NOT_FOUND for v in answered):
        return OUTCOME_PARSE_FAILED
    return OUTCOME_NOT_FOUND

# ─────────────────────────────── 站点地址 ───────────────────────────────

#: ① 官方 JSON 接口（与 ``channels/cssn.py`` 的 ``CssnAdapter.SEARCH_URL`` 同一个端点；
#: 这里是**查询 CCS** 的用法，那边是**探测效力状态**的用法 —— 同一个事实源，两种用途）
_CSSN_API = "https://www.cssn.net.cn/api/standards/list"
#: ② 网页列表页（HTML，含 ``【CCS分类】``）
_CSSN_LIST = "https://www.cssn.net.cn/api/cssn/list"
_INDEX = "https://www.cssn.net.cn/cssn/index"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
_HEADERS = {"User-Agent": _UA, "Referer": _INDEX, "Accept": "application/json"}

# ─────────────────────────── 本地兜底（第③层）───────────────────────────
#
# 本地 CCS 种子库：批量入库前由 ``std_bulk_import.py`` 从 CSSN 体检结果一次性生成
# ``<jsonl同级>/ccs_seed.json``（数据区，数据/代码分离），经 ``KS_CCS_SEED_FILE`` 注入。
# 未设置环境变量时行为完全不变（测试基线不受影响）。
_CCS_SEED_ENV = "KS_CCS_SEED_FILE"
_seed_cache: dict[str, dict] | None = None


def _seed_key(standard_no: str) -> str:
    """种子键归一（与 std_bulk_import.write_ccs_seed 同一约定）。"""
    return standard_no.upper().replace("／", "/").replace(" ", "")


def _load_ccs_seed(seed_path: str | Path | None = None) -> dict[str, dict]:
    """懒加载种子文件；只缓存成功解析的结果。

    未配置环境变量 / 文件缺失损坏时不缓存（每次仅一次 env 读取的成本），
    避免进程早期被错误地固化成"无种子"，导致后配的种子永远不可见。
    ``seed_path`` 显式给出时不走缓存（调用方要的是"这个文件里有什么"）。
    """
    global _seed_cache
    if seed_path is not None:
        return _read_seed(Path(seed_path))
    if _seed_cache:
        return _seed_cache
    p = os.environ.get(_CCS_SEED_ENV)
    if not p:
        return {}
    _seed_cache = _read_seed(Path(p))
    return _seed_cache


def _read_seed(path: Path) -> dict[str, dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 —— 种子不可用≠入库失败：走原在线路径
        logger.warning("CCS 种子文件读不出（%s）：%s: %s", path, type(e).__name__, e)
        return {}
    if not isinstance(data, dict):
        logger.warning("CCS 种子文件形状不对（不是对象）：%s", path)
        return {}
    return {str(k): v for k, v in data.items()
            if isinstance(v, dict) and v.get("code")}


# 本地兜底映射表（已人工核实官方 CCS；网络不可用时用，优先官方/网页实时结果）
LOCAL_CCS: dict[str, tuple[str, str]] = {
    "GB 30871-2022": ("C", "C65 劳动安全技术"),
    "GB 18218-2018": ("A", "A80 标志包装运输贮存"),
    "GB 3608-2025": ("C", "C75 劳动保护管理"),
    "GB/T 3608-2008": ("C", "C75 劳动保护管理"),
    "GB/T 29639-2020": ("C", "C78 劳动保护管理(应急)"),
    "AQ 3028-2008": ("B", "B09 农业、林业综合"),
    "GB 50140-2005": ("P", "P16 工程防火"),
    "GB 50444-2008": ("P", "P16 工程防火"),
    "GB 55010-2021": ("P", "P46 供热、采暖工程"),
    "GB 55036-2022": ("P", "P16 工程防火"),
    "GB 55037-2022": ("P", "P16 工程防火"),
    "GB/T 50493-2019": ("P", "P72 石化、化工工程"),
}

# ─────────────────────────── 关键词形式 ───────────────────────────

#: 标准号拆解：可选的字母前缀 + 数字主体（可带分部号）+ 可选年代
_NO_RE = re.compile(r"^\s*([A-Za-z]{1,6})?\s*[/／]?\s*([A-Za-z]{0,4})?\s*(\d+(?:\.\d+)*)"
                    r"\s*[-－—–‐]?\s*(\d{4})?\s*$")


def keyword_forms(standard_no: str) -> list[tuple[str, str]]:
    """标准号 → **有序**的 ``[(形式名, 关键词)]``（去重且去掉空串）。

    业主定的口径：「搜索改用完整标准号容易搜不到」⇒ 别只赌一种形式。
    顺序 = 由**精确到宽泛**，前一种命中了就不试后一种（省请求也省得引入噪声）：

    1. ``full``    —— 半角斜杠、**保留空格**的完整号（``GB/T 5405-2002``）。
       ⚠ 空格必须留：cssn 实测"带空格完整号"才排第一（``norm_no`` 会把空格吃掉）。
    2. ``compact`` —— 去空格/去斜杠/大写（``GBT5405-2002``，真库 92% 的号写全角斜杠，
       这一形式专治"站点按半角认、库里写全角"）。
    3. ``core``    —— 数字主体**含分部号**、去年代（``5405`` / ``1094.3``）。
    4. ``bare``    —— 数字**首段**（``1094``）。最宽也最吵（``1094`` 会捞出 HJ/JJF/DB），
       只在前面全落空时用，且**仍按归一化标准号精确挑选**。
    """
    from src.core.update.channels.base import norm_no, query_no

    raw = (standard_no or "").strip()
    if not raw:
        return []
    out: list[tuple[str, str]] = []

    def _add(form: str, kw: str) -> None:
        kw = (kw or "").strip()
        if kw and all(kw != k for _, k in out):
            out.append((form, kw))

    _add("full", query_no(raw))
    _add("compact", norm_no(raw))
    m = _NO_RE.match(query_no(raw))
    if m:
        core = m.group(3) or ""
        _add("core", core)
        if "." in core:
            _add("bare", core.split(".", 1)[0])
        else:
            _add("bare", core)
    return out


# ─────────────────────────── 结果容器 ───────────────────────────


def _major_from_code(code: str) -> str:
    """CCS 代码首字母 → 大类字母（P16 → P）。"""
    return code[:1] if code else ""


def _split_ccs(raw: str) -> tuple[str, str]:
    """``"K41变压器"`` → ``("K41", "变压器")``；拆不开就原样当代码、类名留空。"""
    text = (raw or "").strip()
    m = re.match(r"^([A-Z]\d{2})\s*(.*)$", text)
    if not m:
        return text, ""
    return m.group(1), m.group(2).strip()


def _lookup_dict(code: str, sub: str, *, source: str, keyword_form: str | None = None,
                 matched_no: str | None = None, attempts: list[dict] | None = None,
                 outcome: str = OUTCOME_FOUND) -> dict[str, Any]:
    """统一的结果字典（``fetch_ccs`` 的返回形状 = 旧字段 + 来源字段，**只增不改**）。

    旧字段 ``code`` / ``major`` / ``sub`` 原样保留（``ccs_to_tag`` 与既有调用方靠它们活）；
    新增 ``source`` / ``source_label`` / ``keyword_form`` / ``matched_no`` / ``attempts`` /
    ``outcome`` —— 这就是"每篇都能说出是哪一层命中的"那部分。
    """
    return {
        "code": code, "major": _major_from_code(code), "sub": sub,
        "source": source, "source_label": SOURCE_LABELS.get(source, source),
        "keyword_form": keyword_form,
        "keyword_form_label": FORM_LABELS.get(keyword_form or "", None),
        "matched_no": matched_no,
        "outcome": outcome,
        "attempts": list(attempts or []),
    }


def empty_lookup(outcome: str, attempts: list[dict], reason: str = "") -> dict[str, Any]:
    """没命中时的结果（``found=False``）——**必须**带 outcome 与逐层尝试记录。"""
    if outcome not in OUTCOMES:
        raise ValueError(f"未知 outcome: {outcome!r}（合法：{list(OUTCOMES)}）")
    return {"code": None, "major": "", "sub": None, "found": False,
            "source": None, "source_label": None, "keyword_form": None,
            "keyword_form_label": None, "matched_no": None,
            "outcome": outcome, "reason": reason or OUTCOME_LABELS.get(outcome, ""),
            "attempts": list(attempts or [])}


# ─────────────────────────── ① 官方 JSON 接口 ───────────────────────────


def _pick_row(rows: list[Any], standard_no: str) -> tuple[dict | None, str | None]:
    """按**归一化标准号**精确挑选匹配行（跨前缀同主体是兜底，且把 mode 如实上报）。

    这里**刻意复用** ``CssnAdapter._pick`` 的判断（那是 CSSN 搜索语义的唯一所有者：
    它知道 GB→GB/T 强制转推荐后库里只剩推荐版，也知道同年份优先）。复制一份到这里
    迟早跟那边漂移，所以直接调它。
    """
    from src.core.update.channels.cssn import CssnAdapter
    return CssnAdapter._pick(rows, standard_no)


def _layer_official_api(standard_no: str, transport: Any,
                        attempts: list[dict], pause_s: float | None = None
                        ) -> tuple[dict | None, str]:
    """① 官方 JSON 接口：多形式依次试，每形式按归一号精确挑。

    返回 ``(结果|None, 本层结论)``；本层结论 ∈ found|not_found|network_failed|parse_failed。
    """
    facts = _LayerFacts()
    for form, kw in keyword_forms(standard_no):
        try:
            status, body = transport.fetch(_CSSN_API, params={"keyword": kw},
                                           headers=_HEADERS, timeout=25)
        except Exception as e:  # noqa: BLE001 —— 归一成"没查成"，不猜"查无"
            attempts.append({"layer": SOURCE_OFFICIAL_API, "keyword_form": form,
                             "keyword": kw, "result": "network_error",
                             "detail": f"{type(e).__name__}: {e}"})
            _pace(transport, pause_s)
            continue
        _pace(transport, pause_s)
        facts.saw_response = True
        if looks_like_captcha(body):
            attempts.append({"layer": SOURCE_OFFICIAL_API, "keyword_form": form,
                             "keyword": kw, "result": "captcha",
                             "detail": "站点要求人机验证（未硬闯）"})
            continue
        rows = _rows_of(body)
        if rows is None:
            attempts.append({"layer": SOURCE_OFFICIAL_API, "keyword_form": form,
                             "keyword": kw, "result": "unparsable",
                             "detail": f"应答不是预期的 JSON 形状（http={status}）"})
            continue
        facts.saw_parseable = True
        row, mode = _pick_row(rows, standard_no)
        if row is None:
            attempts.append({"layer": SOURCE_OFFICIAL_API, "keyword_form": form,
                             "keyword": kw, "result": "no_match",
                             "detail": f"应答 {len(rows)} 条，无归一号相等的行"})
            continue
        ccs_code = str(row.get("a825") or "").strip()
        ccs_name = str(row.get("a825name") or "").strip()
        matched = str(row.get("a100") or "").strip()
        if not ccs_code:
            # 号匹配上了，但这一行**没有** CCS 字段（实测老标准会这样）
            facts.no_ccs_seen = True
            attempts.append({"layer": SOURCE_OFFICIAL_API, "keyword_form": form,
                             "keyword": kw, "result": "no_ccs_field",
                             "detail": f"命中 {matched or '?'}（{mode}）但该行 a825 为空"})
            continue
        attempts.append({"layer": SOURCE_OFFICIAL_API, "keyword_form": form,
                         "keyword": kw, "result": "hit", "detail": f"{matched} ({mode})"})
        return _lookup_dict(ccs_code, ccs_name, source=SOURCE_OFFICIAL_API,
                            keyword_form=form, matched_no=matched), OUTCOME_FOUND
    return None, facts.verdict()


def _rows_of(body: Any) -> list[Any] | None:
    """JSON 应答 → 结果行列表；形状不对返回 None（**不猜**）。"""
    if not isinstance(body, dict):
        return None
    if body.get("code") not in (0, None):
        return None
    results = body.get("results")
    return results if isinstance(results, list) else None


def _should_pace(transport: Any, pause_s: float | None) -> float:
    """两次请求之间该睡多久（0 = 不睡）。

    ⚠ 规则**抄渠道层的**（``CssnAdapter._pace``）：真实 transport 才睡，注入的假
    transport 不睡（否则离线单测每个用例白等 1 秒 × 几百次）。间隔秒数也取
    ``CssnAdapter.PAUSE_S`` —— 那是"对 cssn 的礼貌速率"的唯一所有者，别在这里
    再写一个数字。``pause_s`` 显式给了就用给的（补全任务要能调快/调慢）。
    """
    if pause_s is not None:
        return max(0.0, float(pause_s))
    from src.core.update.channels.base import CurlCffiTransport, HttpxTransport
    from src.core.update.channels.cssn import CssnAdapter
    if isinstance(transport, (CurlCffiTransport, HttpxTransport)):
        return float(CssnAdapter.PAUSE_S)
    return 0.0


def _pace(transport: Any, pause_s: float | None) -> None:
    """按上面的规则睡一次（唯一的 sleep 出口）。"""
    import time
    delay = _should_pace(transport, pause_s)
    if delay > 0:
        time.sleep(delay)


# ─────────────────────────── ② 网页抓取（HTML） ───────────────────────────
#
# ⚠ 块边界的**唯一所有者**是下面两条正则 + ``_parse_html_items`` 的切分方式。
#   旧实现按 ``a301``（标题）切块 ⇒ 永远挑不中（实测取证见模块头第 3 条）。
#   这里的锚点是 ``class="ph_list_title"``（**标准号**）：实测条目顺序是
#   **号在前、标题与 CCS 在后**，所以 [号_i, 号_{i+1}) 这一段正好装 i 号的 CCS 与标题。

_HTML_NO = re.compile(r'class="ph_list_title">([^<]+)</p>')
_HTML_TITLE = re.compile(r'ph_img_contenta301">([^<]+)</strong>')
_HTML_CCS = re.compile(r'【CCS分类】</strong>([^<]*)</li>')


def _parse_html_items(html: str) -> list[dict[str, str]]:
    """HTML 列表页 → ``[{"a100", "a298", "ccs"}]``（按 ``ph_list_title`` 的标准号切块）。

    一段 = 从一个标准号到下一个标准号之前，含**这一条自己的**标题与 ``【CCS分类】``。
    ``ccs`` 可能是空串（页面里那一条没给分类号）。

    ⚠ 键名**刻意用 JSON 接口的字段名**（``a100``=标准号、``a298``=名称）：这样挑选行
    可以走**同一份** ``CssnAdapter._pick``（CSSN 搜索语义的唯一所有者）——
    另一套键名等于逼着这里再写一份挑选逻辑，两份迟早漂移。
    """
    anchors = list(_HTML_NO.finditer(html or ""))
    items: list[dict[str, str]] = []
    for i, m in enumerate(anchors):
        end = anchors[i + 1].start() if i + 1 < len(anchors) else len(html)
        chunk = html[m.start():end]
        t = _HTML_TITLE.search(chunk)
        c = _HTML_CCS.search(chunk)
        items.append({"a100": m.group(1).strip(),
                      "a298": t.group(1).strip() if t else "",
                      "ccs": c.group(1).strip() if c else ""})
    return items


def _layer_web_scrape(standard_no: str, transport: Any,
                      attempts: list[dict], pause_s: float | None = None
                      ) -> tuple[dict | None, str]:
    """② 网页抓取：同样多形式依次试，按**归一号精确挑选**条目。"""
    facts = _LayerFacts()
    for form, kw in keyword_forms(standard_no):
        try:
            status, body = transport.fetch(_CSSN_LIST, params={"keyword": kw},
                                           headers={"User-Agent": _UA}, timeout=25)
        except Exception as e:  # noqa: BLE001
            attempts.append({"layer": SOURCE_WEB_SCRAPE, "keyword_form": form,
                             "keyword": kw, "result": "network_error",
                             "detail": f"{type(e).__name__}: {e}"})
            _pace(transport, pause_s)
            continue
        _pace(transport, pause_s)
        facts.saw_response = True
        html = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
        if looks_like_captcha(html):
            attempts.append({"layer": SOURCE_WEB_SCRAPE, "keyword_form": form,
                             "keyword": kw, "result": "captcha",
                             "detail": "站点要求人机验证（未硬闯）"})
            continue
        items = _parse_html_items(html)
        if not items:
            attempts.append({"layer": SOURCE_WEB_SCRAPE, "keyword_form": form,
                             "keyword": kw, "result": "unparsable",
                             "detail": f"页面上找不到条目（http={status}，"
                                       f"HTML 结构可能变了）"})
            continue
        facts.saw_parseable = True
        row, mode = _pick_row(items, standard_no)
        if row is None:
            attempts.append({"layer": SOURCE_WEB_SCRAPE, "keyword_form": form,
                             "keyword": kw, "result": "no_match",
                             "detail": f"页面 {len(items)} 条，无归一号相等的条目"})
            continue
        matched = str(row.get("a100") or "").strip()
        raw_ccs = str(row.get("ccs") or "").strip()
        if not raw_ccs:
            facts.no_ccs_seen = True
            attempts.append({"layer": SOURCE_WEB_SCRAPE, "keyword_form": form,
                             "keyword": kw, "result": "no_ccs_field",
                             "detail": f"命中 {matched or '?'}（{mode}）但该条无【CCS分类】"})
            continue
        code, sub = _split_ccs(raw_ccs)
        attempts.append({"layer": SOURCE_WEB_SCRAPE, "keyword_form": form,
                         "keyword": kw, "result": "hit", "detail": f"{matched} ({mode})"})
        return _lookup_dict(code, sub, source=SOURCE_WEB_SCRAPE,
                            keyword_form=form, matched_no=matched), OUTCOME_FOUND
    return None, facts.verdict()


# ─────────────────────────── ③ 本地兜底 ───────────────────────────


def _layer_local_table(standard_no: str, attempts: list[dict]) -> dict | None:
    """③a 人工核实表（``LOCAL_CCS``）。键按**存储形**折（与 ``ccs_to_tag`` 同一口径）。"""
    from src.core.text_utils import store_standard_no
    key = store_standard_no(standard_no)
    hit = LOCAL_CCS.get(key)
    if hit is None:
        attempts.append({"layer": SOURCE_LOCAL_TABLE, "keyword_form": None,
                         "keyword": key, "result": "no_match",
                         "detail": f"人工核实表里没有 {key}"})
        return None
    _code, sub = hit
    code, name = _split_ccs(sub)
    attempts.append({"layer": SOURCE_LOCAL_TABLE, "keyword_form": None,
                     "keyword": key, "result": "hit", "detail": sub})
    return _lookup_dict(code, name, source=SOURCE_LOCAL_TABLE, matched_no=key)


def _layer_seed_file(standard_no: str, attempts: list[dict],
                     seed_path: str | Path | None = None) -> dict | None:
    """③b 种子文件（``KS_CCS_SEED_FILE``；命中即零网络）。"""
    key = _seed_key(standard_no)
    seed = _load_ccs_seed(seed_path)
    hit = seed.get(key)
    if not hit or not hit.get("code"):
        attempts.append({"layer": SOURCE_SEED_FILE, "keyword_form": None,
                         "keyword": key,
                         "result": "unavailable" if not seed else "no_match",
                         "detail": ("没有配置种子文件（KS_CCS_SEED_FILE 未设置）"
                                    if not seed else f"种子里没有 {key}")})
        return None
    code = str(hit["code"])
    attempts.append({"layer": SOURCE_SEED_FILE, "keyword_form": None,
                     "keyword": key, "result": "hit", "detail": str(hit.get("sub") or "")})
    return _lookup_dict(code, str(hit.get("sub") or ""), source=SOURCE_SEED_FILE,
                        matched_no=key)


# ─────────────────────────── 链的编排 ───────────────────────────


def resolve_ccs(standard_no: str, standard_name: str = "", *,
                transport: Any = None, use_network: bool = True,
                seed_path: str | Path | None = None,
                pause_s: float | None = None) -> dict[str, Any]:
    """**三层有序链**查 CCS，返回统一结果字典（**永远带 outcome 与逐层尝试记录**）。

    参数
    ----
    transport : 注入的传输（契约同 ``channels.base`` 的 ``fetch(url, **kw) ->
        (status, body)``）。省略则用 ``default_transport()``（curl_cffi 优先、httpx 兜底）。
        **测试一律注入**，本函数因此可离线测。
    use_network : ``False`` ⇒ 只走第③层（本地表 + 种子），零网络。补全任务里给
        "离线重跑"用。
    seed_path : 显式种子文件路径（省略走 ``KS_CCS_SEED_FILE``）。
    pause_s : 两次请求之间的礼貌间隔；省略 ⇒ 真实 transport 用
        ``CssnAdapter.PAUSE_S``、注入的 transport 用 0（见 ``_should_pace``）。

    返回值（命中）
    --------------
    ``{code, major, sub, source, source_label, keyword_form, keyword_form_label,
    matched_no, outcome='found', attempts}``

    返回值（未命中）
    ----------------
    ``{code: None, found: False, outcome, reason, attempts, ...}`` ——
    ``outcome`` 四枚举见模块头，**"发不出去"永远不会被说成"官方查无"**。
    """
    attempts: list[dict] = []
    if not (standard_no or "").strip():
        # 没有号就无从查：这不是"网络失败"，也不是"官方查无"，如实说"没有号"
        return empty_lookup(OUTCOME_NOT_FOUND, attempts,
                            reason="没有标准号，无从查询分类号")
    # ① 官方接口 → ② 网页抓取（各层给一个结论，最后合成一个如实的总结论）
    verdicts: list[str] = []
    if use_network:
        tr = transport if transport is not None else _default_transport()
        for layer in (_layer_official_api, _layer_web_scrape):
            got, verdict = layer(standard_no, tr, attempts, pause_s)
            if got is not None:
                got["attempts"] = attempts
                got["found"] = True
                return got
            verdicts.append(verdict)
    worst = _combine_verdicts(verdicts) if verdicts else OUTCOME_NOT_FOUND
    # ③ 本地兜底：**永远试**（哪怕网络全炸，本地能命中就是命中）
    got = _layer_local_table(standard_no, attempts)
    if got is None:
        got = _layer_seed_file(standard_no, attempts, seed_path)
    if got is not None:
        got["attempts"] = attempts
        got["found"] = True
        return got
    reason = _reason_text(worst, attempts)
    return empty_lookup(worst, attempts, reason=reason)


def _default_transport() -> Any:
    """默认传输 = 渠道层的唯一所有者（curl_cffi 优先、httpx 兜底且带自检）。

    ⚠ **绝不在本模块里 new httpx.Client**：本机 ``NO_PROXY`` 含 ``[::1]`` 时
    httpx 构造即抛 ``InvalidURL: Invalid port``（模块头第 1 条真毛病），
    而渠道层已经有 ``httpx_usable()`` 那条自检与"两个栈都不可用"的 ERROR 日志。
    """
    from src.core.update.channels.base import default_transport
    return default_transport()


def _reason_text(worst: str, attempts: list[dict]) -> str:
    """给界面/审计用的一句人话（说清"为什么没有这一篇的分类号"）。

    ⚠ 措辞与 ``OUTCOME_LABELS`` 同一个口径：**不许**把"发不出去"说成"官方查无"。
    """
    net = [a for a in attempts if a.get("layer") in (SOURCE_OFFICIAL_API, SOURCE_WEB_SCRAPE)]
    if worst == OUTCOME_NETWORK_FAILED:
        errs = [str(a.get("detail")) for a in net
                if a.get("result") in ("network_error", "captcha")]
        return ("查询失败：两个站点一个都没答上（网络不通或被拦）" +
                (f"；首个原因：{errs[0]}" if errs else ""))
    if worst == OUTCOME_PARSE_FAILED:
        no_ccs = [a for a in net if a.get("result") == "no_ccs_field"]
        if no_ccs:
            return ("站点上有这个标准号，但**没有给分类号**"
                    f"（{no_ccs[0].get('detail')}）")
        return "解析失败：站点答了，但读不出条目（页面结构可能变了）"
    return "查无：答话的站点里都没有这个标准号"


def fetch_ccs(standard_no: str, standard_name: str = "", *,
              transport: Any = None, use_network: bool = True,
              seed_path: str | Path | None = None,
              pause_s: float | None = None) -> dict[str, Any] | None:
    """按标准号查询 CCS。**命中**返回 ``{code, major, sub, source, …}``，未命中返回 None。

    ⚠ 与重做前的**唯一**行为差别：命中的可能性大了（三层链 + 多形式），
    返回形状**只增不改**（旧字段照旧）。要"为什么没中"请用 :func:`resolve_ccs`
    —— 那一个**永远**返回带 ``outcome`` 的结构，本函数按旧契约继续给 ``None``。
    """
    got = resolve_ccs(standard_no, standard_name, transport=transport,
                      use_network=use_network, seed_path=seed_path, pause_s=pause_s)
    return got if got.get("code") else None


def ccs_to_tag(ccs: dict | None, standard_no: str) -> str | None:
    """CCS 结果 → domain_tags 条目（"CCS:P16 工程防火"）。未命中回退本地表。

    ⚠ 查本地表前先折**存储形**（§11.0 R6c-3f；独立复核 b36 实测点名的一处）：
    调用方给的是**折前**的号（`pipeline.py`），而本地表的键是半角写法
    ⇒ 全角入参（`GB／T …`）在这里**静默查不到**、直接丢掉 CCS 标签。
    """
    if ccs and ccs.get("code"):
        sub = ccs.get("sub") or ""
        return f"CCS:{ccs['code']}" + (f" {sub}" if sub else "")
    from src.core.text_utils import store_standard_no
    key = store_standard_no(standard_no)
    if key in LOCAL_CCS:
        code, sub = LOCAL_CCS[key]
        # sub 已含 code（如 "B09 农业、林业综合"），直接返回
        return f"CCS:{sub}" if sub else f"CCS:{code}"
    return None
