"""公告发现（announcement discovery，2026-09，KS×DSH 决策 19 延伸）：自定义公告源
定期"看新公告"流程——与查号巡检（inspector，单元=标准号）是**两条独立流程**：
本模块单元=源 URL（用户在设置栏目配置），引擎逐源抓列表页 → 零 LLM 启发式解析
→ 与已见公告去重（announcement_observed 表，契约增量见 pipeline/03「公告发现」节）
→ 新公告轻通知（host 纵览行 + 最近列表；决策 5 默默执行）。

设计要点（verify_rollout 三路择优 0.512 + 用户拍板）：
- 触发：host 巡检 finalizeBatch 后自动（force=false，含时间闸 min_interval_hours
  默认 6h 防频繁）+ 独立按钮（force=true）。
- 执行：fire-and-forget daemon 线程（与 /update/check 同构）；409 双闸
  （进程内 _announce_runs + scan_state.status）；僵尸扫描自愈（DB running 而进程
  内无登记 → 直接开新扫，扫描幂等且便宜）。
- 存储：源清单 app_config 键 ``announce.sources``（配置语义，仿 subscriptions）；
  已见公告 announcement_observed（32 号表）；扫描快照 app_config 键
  ``announce.scan_state``（只留最近一次，明细历史走 event_log/P1 Excel）。
- 首扫基线语义：源第一次扫描把全部条目记 baseline（first_scan_done=false），
  不计"新"——避免加源当天被几十条"新"刷屏；PUT 改 URL 重置基线。
- SSRF：仅 http/https；**默认禁内网**（用户拍板严格版，无豁免开关）——loopback /
  RFC1918 / 链路本地(含云元数据) / 0.0.0.0 / IPv6 本地 / .local 一律 422 拒绝，
  主机字面量与 DNS 解析结果都查。
- 预算：单页 15s/2MB、每页条目上限 50、源间 1s 礼貌间隔、
  **源数量不设上限**（2026-10-08 删 `SOURCES_MAX`）、
  全程软上限 5 分钟（超时剩余源标 skipped_timeout；可用 app_config
  ``announce.scan_soft_cap_s`` 覆盖）。
- 失败诚实：WAF/验证码、JS 渲染壳、解析 0 条、超时——每源 status=failed+reason
  直达 UI，绝不静默假装"0 新公告"。
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from src.core.storage.sqlite_db import get_db_connection, write_transaction
from src.core.update.channels.base import (
    UPD_ANNOUNCE_SCAN_ALREADY_RUNNING,
    UPD_ANNOUNCE_SOURCE_NOT_FOUND,
    UPD_ILLEGAL_SOURCE_PAYLOAD,
    UpdateError,
    default_transport,
    looks_like_captcha,
    upd_log,
)
from src.core.update.channels.govcn_announce import _STD_TOKEN_RE
from ulid import ULID

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from src.core.exports.xlsx_common import xlsx_header_style as _xlsx_header_style

from src.core.exports.report_export import _exports_dir, _safe_name

# ---------------------------------------------------------------- 常量（预算，P0 不开放配置）
SOURCES_KEY = "announce.sources"
STATE_KEY = "announce.scan_state"
# ⚠ 2026-10-08 业主拍板：**取消源数量上限**（原 `SOURCES_MAX = 50` 已删）。
#   理由：要覆盖「法律法规 / 国标 / 行标 / 团标 / 地标」全量官方入口，50 条根本不够
#   （实测有效入口已 100+）。源数量不再设闸；真正的成本闸是**扫描全程软上限**
#   `SCAN_SOFT_CAP_S`（超时的源如实标 `skipped_timeout`，绝不假装扫过）。
ITEMS_PER_PAGE_MAX = 50             # 每页条目上限（防导航页误判）
PAGE_TIMEOUT_S = 15.0               # 单页超时（比渠道探测 30s 收紧一倍）
PAGE_BYTES_MAX = 2 * 1024 * 1024    # 单页字节上限（截断标记）
SOURCE_GAP_S = 1.0                  # **同一主机**内的源间礼貌间隔（并行后不再跨主机等）
#: 不同主机之间的并发数（2026-11-02）。同一主机永远串行。
SCAN_CONCURRENCY_DEFAULT = 8
SCAN_SOFT_CAP_S = 300               # 扫描全程软上限（超时剩余源标 skipped_timeout）
MIN_INTERVAL_HOURS_DEFAULT = 6.0    # force=false 时间闸（app_config announce.min_interval_hours 可覆盖）
# ── 翻页（2026-09-24，业主报"应该入库的没入库"引出；见开发史 §10.189）──────────────
#: 单源最多翻几页。改前**只取第 1 页**（每页 20 条）⇒ 业主看的那个列表 857 条 / 58 页，
#: 我们永远只看见 20 条 —— 这就是"大量应该入库的放过了"的直接原因。50 页 × 20 条 = 1000 条，
#: 盖得住部委站的常见列表；真要更深的回溯再调这个数（或走 §10.189 的入库通道做全量回填）。
PAGES_PER_SOURCE_MAX = 50
#: 逐页礼貌间隔（同一站连翻 50 页不留间隔不礼貌，也容易被 WAF 记上）。
PAGE_GAP_S = 0.4
#: 单源翻页的总时间预算；超了就停在拿到的页数并如实标 truncated（不给单源拖垮整轮扫描）。
SOURCE_TIME_BUDGET_S = 90.0
#: 连续这么多页**一条"没见过"的都没有** ⇒ 判定已追上历史，提前停（第 2 次起扫描就便宜了）。
STOP_AFTER_BARREN_PAGES = 3

_SCAN_LOCK = threading.Lock()
_announce_runs: set[str] = set()    # 进程内在跑扫描（与 scan_state.status 构成双闸）

_NOISE_RE = re.compile(
    r"下一页|上一页|首页|末页|更多|返回|关闭|登录|注册|English|无障碍|浏览次数|"
    r"首页|尾页|跳转|收起|展开|全文|下载|阅读|次浏览|版权所有|备案号|"
    r"京公网安备|ICP备|网站地图|联系我们|意见反馈|站内搜索|"
    r"政务服务投诉|社会救援服务|科普场馆")
#: JS 拼接/模板代码片段特征（document.write 产出的 <a> 内层文本是源码不是标题）
_JS_NOISE_RE = re.compile(r"[{}]|\";\s*$|function\s*\(|document\.|else\s+if|\+\s*i\s*\+")
#: 标题尾部日期时间戳剥离（"…通知 2022-01-17 17:33" → "…通知"）
_TAIL_STAMP_RE = re.compile(
    r"\s*\d{4}[-./年]\d{1,2}[-./月]\d{1,2}日?(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?\s*$")
_TRACKING_PARAM_RE = re.compile(r"(?i)^(utm_\w+|spm|from|share_token|fr|vd|scene)$")
_DATE_RE = re.compile(r"(\d{4})[年./\-](\d{1,2})[月./\-](\d{1,2})日?")
_A_TAG_RE = re.compile(r"<a\b[^>]*href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
                       re.IGNORECASE | re.DOTALL)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_STATIC_EXT_RE = re.compile(r"(?i)\.(css|js|png|jpe?g|gif|svg|ico|woff2?)($|\?)")
_SCHEME_BAD_RE = re.compile(r"(?i)^(javascript:|mailto:|tel:|#)")


# ---------------------------------------------------------------- URL 归一化与 SSRF
def normalize_url(url: str) -> str:
    """URL 归一化：scheme/host 小写、去默认端口、path 去尾斜杠（根保留）、
    剔除追踪参数并按 key 排序重组 query、丢 fragment。"""
    parts = urlsplit((url or "").strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    if port is not None and not (scheme == "http" and port == 80) \
            and not (scheme == "https" and port == 443):
        netloc = f"{host}:{port}"
    else:
        netloc = host
    if parts.username:
        netloc = f"{parts.username}@{netloc}"
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    query_pairs = [p for p in parts.query.split("&") if p]
    kept = []
    for pair in query_pairs:
        key = pair.split("=", 1)[0]
        if _TRACKING_PARAM_RE.match(key):
            continue
        kept.append(pair)
    kept.sort()
    return urlunsplit((scheme, netloc, path, "&".join(kept), ""))


def url_hash(url: str) -> str:
    """归一化 URL 的 SHA-256 小写 hex（去重键）。"""
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def _host_is_private(host: str) -> bool:
    """主机名是否指向内网/保留地址：字面量 IP 直接判；域名逐解析结果判。"""
    host = (host or "").strip().lower()
    if not host:
        return True
    if host == "localhost" or host.endswith(".local") or host.endswith(".internal"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return not ip.is_global
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return True  # 解析失败按不可信处理（宁可错拒，绝不替用户探测）
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if not ip.is_global:
            return True
    return False


def is_private_url(url: str) -> bool:
    """SSRF 检查：仅 http/https；默认禁内网（用户拍板严格版，无豁免）。
    主机字面量与 DNS 解析结果都查（known limitation：resolve-then-fetch 的
    rebinding TOCTOU 窗口不设防——引擎仅本机回环监听、URL 为用户手工录入，
    P0 接受；未来若开放远程写 API 需补连接时复检）。"""
    parts = urlsplit((url or "").strip())
    if parts.scheme.lower() not in ("http", "https"):
        return True
    if not parts.hostname:
        return True
    return _host_is_private(parts.hostname)


# ---------------------------------------------------------------- 源 CRUD（app_config 配置语义）
def _read_json_key(key: str, default: Any) -> Any:
    row = get_db_connection().execute(
        "SELECT config_value FROM app_config WHERE config_key=?", (key,)).fetchone()
    if not row:
        return default
    try:
        value = json.loads(row["config_value"])
    except (TypeError, ValueError):
        return default
    return value if value is not None else default


def _write_json_key(key: str, value: Any) -> None:
    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO app_config(config_key, config_value, updated_at) VALUES(?,?,datetime('now')) "
            "ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value, "
            "updated_at=datetime('now')",
            (key, json.dumps(value, ensure_ascii=False)))


def get_sources() -> list[dict]:
    sources = _read_json_key(SOURCES_KEY, [])
    return [s for s in sources if isinstance(s, dict) and isinstance(s.get("id"), str)]


def _validate_source_payload(name: Any, url: Any) -> tuple[str, str]:
    """新增/编辑源的字段校验：必填、scheme、SSRF（默认禁内网）→ 非法抛 UPD-3008。"""
    name_s = str(name or "").strip()
    url_s = str(url or "").strip()
    if not name_s or not url_s:
        raise UpdateError("name 与 url 必填", code=UPD_ILLEGAL_SOURCE_PAYLOAD)
    if len(name_s) > 60 or len(url_s) > 500:
        raise UpdateError("name/url 超长（60/500）", code=UPD_ILLEGAL_SOURCE_PAYLOAD)
    if is_private_url(url_s):
        raise UpdateError("仅支持公网 http/https 地址（内网/非 http(s) 已拒绝）",
                          code=UPD_ILLEGAL_SOURCE_PAYLOAD)
    return name_s, url_s


def add_source(name: str, url: str, note: str = "") -> dict:
    name_s, url_s = _validate_source_payload(name, url)
    with _SCAN_LOCK:
        sources = get_sources()
        # 2026-10-08：**源数量不设上限**（原 SOURCES_MAX 闸已删）。仍拦重复 URL。
        if any(normalize_url(s.get("url", "")) == normalize_url(url_s) for s in sources):
            raise UpdateError("该 URL 已存在（归一化后重复）", code=UPD_ILLEGAL_SOURCE_PAYLOAD)
        src = {"id": f"src_{ULID()}", "name": name_s, "url": url_s, "enabled": True,
               "note": str(note or "").strip()[:200], "first_scan_done": False,
               "added_at": datetime.now().isoformat(timespec="seconds")}
        sources.append(src)
        _write_json_key(SOURCES_KEY, sources)
    upd_log(str(src["id"]), "announce", "INFO", "source_added", url=url_s)
    return src


def update_source(source_id: str, patch: dict) -> dict:
    """部分更新：name/enabled/note 可改；url 改动 → 重置 first_scan_done（换页=重新基线）。"""
    with _SCAN_LOCK:
        sources = get_sources()
        target = next((s for s in sources if s.get("id") == source_id), None)
        if target is None:
            raise UpdateError(f"公告源不存在: {source_id}", code=UPD_ANNOUNCE_SOURCE_NOT_FOUND)
        rebaselined = False
        if "url" in patch and str(patch["url"]).strip() != target.get("url", ""):
            _, url_s = _validate_source_payload(target.get("name"), patch["url"])
            target["url"] = url_s
            if target.get("first_scan_done"):
                target["first_scan_done"] = False
                rebaselined = True
        if "name" in patch:
            name_s = str(patch["name"] or "").strip()
            if not name_s or len(name_s) > 60:
                raise UpdateError("name 必填且 ≤60 字", code=UPD_ILLEGAL_SOURCE_PAYLOAD)
            target["name"] = name_s
        if "note" in patch:
            target["note"] = str(patch["note"] or "").strip()[:200]
        if "enabled" in patch:
            target["enabled"] = bool(patch["enabled"])
        _write_json_key(SOURCES_KEY, sources)
    upd_log(source_id, "announce", "INFO", "source_updated", rebaselined=rebaselined)
    return {**target, "rebaselined": rebaselined}


def remove_source(source_id: str) -> list[dict]:
    """删源：announcement_observed 记录保留（历史公告留档，source_name 快照可读）。"""
    with _SCAN_LOCK:
        sources = get_sources()
        left = [s for s in sources if s.get("id") != source_id]
        if len(left) == len(sources):
            raise UpdateError(f"公告源不存在: {source_id}", code=UPD_ANNOUNCE_SOURCE_NOT_FOUND)
        _write_json_key(SOURCES_KEY, left)
    upd_log(source_id, "announce", "INFO", "source_removed")
    return left


# ---------------------------------------------------------------- 列表页解析（零 LLM 启发式）
def _parse_date(text: str) -> str | None:
    """列表条目日期解析：取**最后一个**合理年份（1990-2100）的匹配——公告日期
    惯于缀尾；标准号（GB 1234.5-2020）形似日期的段会被合法域过滤。非法留空。"""
    out: str | None = None
    for m in _DATE_RE.finditer(text or ""):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not 1990 <= y <= 2100:
            continue
        try:
            out = datetime(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return out


#: **文章页**判据（2026-09-24 加，真机跑出来的）：政府站的列表页右/左栏会挂一堆
#: **栏目导航链接**（`/gk/tzgg/yjglbgg/`、`/fw/dzzz/`、`/gk/sgcc/`…），旧解析把它们当成了公告：
#: 真机实测 558 条"已发现"里有 **22 条**是导航（**22/22 都以 `/` 结尾**、且全都没有发布日期）。
#: 所以判据就取那一条：**路径以 `/` 结尾 = 目录/栏目，不是文章**。
#:
#: ⚠ **刻意没加更严的那条**（"必须有 `.html/.shtml` 后缀或 `t20260923_717384` 这种文章名"）：
#:   加上它当场打红 7 条既有用例（fixture 里的文章 URL 是 `https://gov.cn/news/a1` 这种
#:   **无后缀**形态）—— 那是"把真公告也一起吃掉"的典型信号。业主要的正是"别再放过"，
#:   所以这里只收**证据齐**的那一条（22/22 命中），余下的等有真机反例再说。
_ARTICLE_EXT_RE = re.compile(r"\.(?:s?html?|jsp|asp|aspx|php)(?:$|[?#])", re.I)
_ARTICLE_STAMP_RE = re.compile(r"/t20\d{6}_\d+\.", re.I)


def looks_like_article(url: str) -> bool:
    """这个 URL 像**文章页**（而不是栏目目录/导航）吗？见上面那段说明（只否掉目录型）。"""
    path = urlsplit(url).path or ""
    return not path.endswith("/")


def parse_list_page(html: str, page_url: str) -> tuple[list[dict], dict]:
    """通用列表页启发式解析：候选 <a> 抽取 → 噪音/静态资源/栏目导航过滤 → 绝对化 →
    日期/标准号识别。返回 (items, diag)；items 上限 50/页（truncated 标记）。
    解析不出条目不抛错——由调用方按 diag 判 reason（parse_empty/js_shell_suspected）。"""
    items: list[dict] = []
    seen_urls: set[str] = set()
    nav_skipped = 0
    truncated = False
    for m in _A_TAG_RE.finditer(html or ""):
        href = (m.group(1) or "").strip()
        text = _TAG_STRIP_RE.sub("", m.group(2) or "").strip()
        if len(text) < 6:
            continue
        if _SCHEME_BAD_RE.match(href):
            continue
        # JS 拼接/模板片段（document.write 产出的 <a> 内层是源码）→ 滤
        if _JS_NOISE_RE.search(text):
            continue
        url = urljoin(page_url, href)
        if _STATIC_EXT_RE.search(url):
            continue
        # 栏目导航（目录型 URL）不是公告 —— 见 `looks_like_article` 的说明
        if not looks_like_article(url):
            nav_skipped += 1
            continue
        if _NOISE_RE.search(text):
            continue
        key = normalize_url(url)
        if key in seen_urls:
            continue
        seen_urls.add(key)
        item = {"title": _TAIL_STAMP_RE.sub("", text)[:200], "url": url,
                "published_date": _parse_date(text),
                "standard_no": (lambda mm: mm.group(0).strip() if mm else None)(
                    _STD_TOKEN_RE.search(text))}
        items.append(item)
        if len(items) >= ITEMS_PER_PAGE_MAX:
            truncated = True
            break
    # JS 渲染壳启发：页面不小但几乎没有文本链接 → 疑似 JS 渲染（调用方判 failed）
    diag = {"parsed": len(items), "truncated": truncated, "nav_skipped": nav_skipped,
            "js_shell_suspected": len(items) == 0 and len(html or "") > 40_000
            and len(_A_TAG_RE.findall(html or "")) < 5}
    return items, diag


# ---------------------------------------------------------------- 扫描编排
def _get_state() -> dict:
    state = _read_json_key(STATE_KEY, {})
    return state if isinstance(state, dict) else {}


def _set_state(state: dict) -> None:
    _write_json_key(STATE_KEY, state)


def _min_interval_hours() -> float:
    raw = _read_json_key("announce.min_interval_hours", MIN_INTERVAL_HOURS_DEFAULT)
    try:
        v = float(raw)
        return v if v >= 0 else MIN_INTERVAL_HOURS_DEFAULT
    except (TypeError, ValueError):
        return MIN_INTERVAL_HOURS_DEFAULT


def _scan_soft_cap_s() -> float:
    """扫描全程软上限（秒）。默认 `SCAN_SOFT_CAP_S`(300)；
    2026-10-08 起源数量不设上限 ⇒ 这里可用 app_config ``announce.scan_soft_cap_s`` 覆盖
    （源多了要相应放宽，否则后半截源会被如实标成 skipped_timeout 而扫不到）。"""
    raw = _read_json_key("announce.scan_soft_cap_s", SCAN_SOFT_CAP_S)
    try:
        v = float(raw)
        return v if v > 0 else float(SCAN_SOFT_CAP_S)
    except (TypeError, ValueError):
        return float(SCAN_SOFT_CAP_S)


def _scan_concurrency() -> int:
    """**不同主机之间**的并发数。默认 `SCAN_CONCURRENCY_DEFAULT`(8)。

    2026-11-02 加：原来整轮扫描是一个 `for` 循环，110 个源排在 76 个不同主机上
    却**一个接一个**跑（实测串行 ~10 分钟）。不同主机互不相干，可以同时抓；
    只有**同一主机**才需要串行 + 礼貌间隔。

    可用 app_config ``announce.scan_concurrency`` 覆盖；**同一主机永远串行**
    （见 `_scan_guarded` 的 per-host 锁），所以并发数调大不会把某一个站点打爆。
    """
    raw = _read_json_key("announce.scan_concurrency", SCAN_CONCURRENCY_DEFAULT)
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return SCAN_CONCURRENCY_DEFAULT
    return v if v > 0 else SCAN_CONCURRENCY_DEFAULT


def _host_lock(host: str, locks: dict[str, threading.Lock],
               guard: threading.Lock) -> threading.Lock:
    """取（或建）某个主机的锁。同名主机共用一个锁 ⇒ **同主机请求永远串行**。"""
    with guard:
        lock = locks.get(host)
        if lock is None:
            lock = threading.Lock()
            locks[host] = lock
        return lock


def _scan_guarded(transport: Any, src: dict, scan_id: str, t0: float,
                  soft_cap: float, host_locks: dict[str, threading.Lock],
                  locks_guard: threading.Lock) -> dict:
    """并行扫描的工作单元：软上限检查 → 按主机加锁 → 真正扫一个源。

    为什么按主机加锁而不是简单限并发：
      · 110 个源里有 23 个主机挂了 2~5 个渠道（如 `std.samr.gov.cn` 5 个、
        `www.mem.gov.cn` 4 个）。同一主机并发请求 = 自己把自己打成 WAF 目标。
      · 不同主机并发才是我们要的那部分收益。
    """
    if time.monotonic() - t0 > soft_cap:
        return {"id": src.get("id"), "name": src.get("name", ""),
                "status": "failed", "reason": "skipped_timeout",
                "items": 0, "new_items": 0, "baseline_items": 0}
    host = urlsplit(str(src.get("url") or "")).netloc
    with _host_lock(host, host_locks, locks_guard):
        result = _scan_one_source(transport, src, scan_id)
        # 礼貌间隔只针对真实抓取（测试注入 transport 时跳过，别拖慢用例）。
        # 并行化后这条**只在同一主机内**生效 —— 不同主机之间不再互相等。
        if transport is None and SOURCE_GAP_S > 0:
            time.sleep(SOURCE_GAP_S)
    return result


def get_scan_state() -> dict:
    """最近一次扫描快照（从未扫过 → status=never，恒可读）。"""
    state = _get_state()
    return state if state else {"status": "never"}


def request_scan(force: bool, trigger: str, transport: Any = None) -> dict:
    """扫描入口（端点调用）：时间闸 + 409 双闸 + 僵尸自愈 → 起 daemon 线程。
    transport 仅测试注入用（默认 default_transport 真实抓取）。"""
    with _SCAN_LOCK:
        state = _get_state()
        running = state.get("status") == "running"
        in_process = bool(_announce_runs)
        if running and not in_process:
            # 僵尸扫描（引擎曾死）：扫描幂等且便宜 → 记审计直接开新扫。
            upd_log("announce", "announce", "WARN", "scan_stale_recovered",
                    prev_scan_id=state.get("scan_id"))
            running = False
        if running or in_process:
            raise UpdateError("已有公告扫描在运行中", code=UPD_ANNOUNCE_SCAN_ALREADY_RUNNING)
        if not force:
            last_fin = state.get("finished_at")
            if state.get("status") == "done" and last_fin:
                try:
                    age_h = (datetime.utcnow() - datetime.fromisoformat(
                        str(last_fin).replace("Z", "+00:00").replace(" ", "T"))
                        ).total_seconds() / 3600.0
                except ValueError:
                    age_h = float("inf")
                if age_h < _min_interval_hours():
                    return {"scan_id": state.get("scan_id"), "status": "skipped",
                            "last": state}
        scan_id = f"asc_{ULID()}"
        enabled = [s for s in get_sources() if s.get("enabled") is not False]
        new_state: dict[str, Any] = {
            "scan_id": scan_id, "status": "running", "trigger": trigger,
            "started_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": None, "sources_total": len(enabled), "sources_done": 0,
            "items_seen": 0, "new_count": 0, "baseline_count": 0,
            "per_source": [], "recent": [],
        }
        _set_state(new_state)
        _announce_runs.add(scan_id)
    threading.Thread(target=_run_scan_thread, args=(scan_id, trigger, transport),
                     name=f"ks-announce-{scan_id}", daemon=True).start()
    return {"scan_id": scan_id, "status": "started"}


def _run_scan_thread(scan_id: str, trigger: str, transport: Any = None) -> None:
    try:
        run_announce_scan(scan_id, trigger, transport=transport)
    except Exception as exc:  # noqa: BLE001 — 后台线程必须吞异常存活
        upd_log(scan_id, "announce", "WARN", "scan_thread_error", error=str(exc))
        try:
            state = _get_state()
            if state.get("scan_id") == scan_id and state.get("status") == "running":
                state["status"] = "failed"
                state["finished_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                state["error"] = str(exc)[:300]
                _set_state(state)
        except Exception:  # noqa: BLE001
            pass
    finally:
        with _SCAN_LOCK:
            _announce_runs.discard(scan_id)


def _mark_first_scan_done(source_id: str | None) -> None:
    """把某个源标记为「首扫已做」。**只由扫描主线程调用**。

    为什么单独抽出来（2026-11-02 并行化）：原先是工作线程里
    `get_sources() → 改 → _write_json_key()` 的**读改写**，两个源同时首扫时
    后写的会把先写的覆盖掉（丢一个 `first_scan_done`，下一轮那个源又当首扫
    重算一遍基线）。现在只在主线程串行调用，读改写之间不再有并发。

    失败也不抛：最坏后果是该源下轮把已见条目当"已见"而非基线（无害）。
    """
    if not source_id:
        return
    try:
        sources = get_sources()
        changed = False
        for s in sources:
            if s.get("id") == source_id and s.get("first_scan_done") is not True:
                s["first_scan_done"] = True
                changed = True
        if changed:
            _write_json_key(SOURCES_KEY, sources)
    except Exception:                       # noqa: BLE001 — 见 docstring：无害
        pass


def run_announce_scan(scan_id: str, trigger: str, transport: Any = None) -> dict:
    """扫描全部公告源：fetch → parse → 去重落库（每源一个短事务）→ 状态逐源写回。

    **2026-11-02 起并行**（原来是一个 `for` 循环串行跑，110 个源实测约 10 分钟）：
      · **不同主机**同时抓（并发数 `announce.scan_concurrency`，默认 8）；
      · **同一主机**仍然串行 + 礼貌间隔 `SOURCE_GAP_S`（该主机挂了多个渠道时不许并发）；
      · 状态写回与 `first_scan_done` 标记**只在主线程做**（都是读改写，多线程会互相覆盖）。

    `transport` 仅测试注入用。返回最终 state（与 `get_scan_state()` 同形）。
    """
    t0 = time.monotonic()
    soft_cap = _scan_soft_cap_s()
    sources = [s for s in get_sources() if s.get("enabled") is not False]
    concurrency = _scan_concurrency()
    upd_log(scan_id, "announce", "INFO", "scan_started", trigger=trigger,
            sources=len(sources), soft_cap_s=soft_cap, concurrency=concurrency)
    transport = transport if transport is not None else default_transport()
    state = _get_state()
    #: 按**原始顺序**占位收集：per_source 的顺序必须跟源顺序一致（界面与测试都按它读），
    #: 不能让并行完成的先后把顺序打乱。
    slots: list[dict | None] = [None] * len(sources)
    total_seen = 0
    total_new = 0
    total_baseline = 0
    recent: list[dict] = []
    host_locks: dict[str, threading.Lock] = {}
    locks_guard = threading.Lock()

    def completed() -> list[dict]:
        return [r for r in slots if r is not None]

    with ThreadPoolExecutor(max_workers=max(1, min(concurrency, len(sources) or 1)),
                            thread_name_prefix="ks-announce-src") as pool:
        futures = {pool.submit(_scan_guarded, transport, src, scan_id, t0,
                               soft_cap, host_locks, locks_guard): idx
                   for idx, src in enumerate(sources)}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                result = fut.result()
            except Exception as exc:              # noqa: BLE001 — 单源崩了不拖垮整轮
                src = sources[idx]
                result = {"id": src.get("id"), "name": src.get("name", ""),
                          "status": "failed",
                          "reason": f"worker_error: {type(exc).__name__}: {str(exc)[:100]}",
                          "items": 0, "new_items": 0, "baseline_items": 0}
                upd_log(scan_id, "announce", "WARN", "source_failed",
                        source=src.get("name"), reason=result["reason"])
            slots[idx] = result
            total_seen += result.get("items", 0)
            total_new += result.get("new_items", 0)
            total_baseline += result.get("baseline_items", 0)
            recent.extend(result.pop("_recent", []) or [])
            # 首扫基线标记：**只有主线程读改写**（并行后必须收在这里，否则丢更新）
            if result.pop("_mark_first_scan", False):
                _mark_first_scan_done(result.get("id"))
            # 状态逐源写回（界面 1s 轮询可见）
            state = _get_state()
            if state.get("scan_id") != scan_id:
                return state  # 已被新扫描接管（理论上不可能——409 闸在）
            done = completed()
            state["per_source"] = done
            state["sources_done"] = len([p for p in done
                                         if p.get("status") != "skipped_timeout"])
            state["items_seen"] = total_seen
            state["new_count"] = total_new
            state["baseline_count"] = total_baseline
            _set_state(state)

    per_source = completed()
    recent.sort(key=lambda r: r.get("first_seen") or "", reverse=True)
    state = _get_state()
    if state.get("scan_id") == scan_id:
        state.update({
            "status": "done",
            "finished_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "per_source": per_source,
            "sources_done": len([p for p in per_source if p.get("status") != "skipped_timeout"]),
            "items_seen": total_seen, "new_count": total_new,
            "baseline_count": total_baseline,
            "recent": recent[:5],
        })
        _set_state(state)
        upd_log(scan_id, "announce", "INFO", "scan_finished",
                items=total_seen, new_items=total_new,
                duration_ms=int((time.monotonic() - t0) * 1000))
    return state


#: 真 `<a>` 翻页：href 像"第 N 页"（`index_2.shtml` / `?page=2` / `list_2.html`）
_PAGER_HREF_RE = re.compile(r"(?i)(^|/)(index|list|page|p)[_-]?\d+\.s?html?$|[?&]page=\d+")
#: JS 拼的翻页（部委站最常见）：原始 HTML 里没有真 `<a>`，只有 `index_" + i + ".shtml`
_PAGER_JS_HINT_RE = re.compile(r"index_(\d+)\.s?html", re.I)
_PAGER_JS_COUNT_RE = re.compile(r"countPage\s*=\s*(\d+)", re.I)
_PAGER_NEXT_TEXT_RE = re.compile(r"^\s*(下一页|下页|next|more|更多|»)\s*$", re.I)


def discover_next_pages(html: str, page_url: str,
                        max_pages: int = PAGES_PER_SOURCE_MAX) -> list[str]:
    """从**当前这一页**找出后续页 URL（不含当前页；最多 `max_pages` 个）。

    两种形态都实测过（开发史 §10.189）：
    ① **真 `<a>` 翻页链**：href 像 `index_2.shtml` / `?page=2`，或锚文本是"下一页"。只收**同目录同站**，
       且排除明显是条目的外链（跨目录/跨站一律不收）。
    ② **JS 拼的翻页**（应急管理部等部委站）：`document.write("<a href=\\"index_"+i+".shtml\\">")`
       + `var countPage = 25` ⇒ 原始 HTML 里**没有真 `<a>`**，只能按 `index_N.shtml` 的规律推。
       实测该站：第 1 页 = 栏目页本身、第 2 页 = `index_1.shtml`（`?page=2` 会被忽略）。

    ⚠ 这个函数只**提候选**，不保证每一页真有内容：后续页 404/空由调用方如实记账（不许当整源失败）。
    """
    out: list[str] = []
    seen: set[str] = {normalize_url(page_url)}
    base_dir = page_url.rsplit("/", 1)[0] + "/"

    def _push(u: str) -> None:
        key = normalize_url(u)
        if key in seen or len(out) >= max_pages:
            return
        if urlsplit(u).netloc != urlsplit(page_url).netloc:
            return
        seen.add(key)
        out.append(u)

    for m in _A_TAG_RE.finditer(html or ""):
        href = (m.group(1) or "").strip()
        text = _TAG_STRIP_RE.sub("", m.group(2) or "").strip()
        if not href or _SCHEME_BAD_RE.match(href):
            continue
        if _STATIC_EXT_RE.search(href):
            continue
        if not (_PAGER_NEXT_TEXT_RE.match(text) or _PAGER_HREF_RE.search(href)):
            continue
        u = urljoin(page_url, href)
        # 只收同目录：跨目录的多半是"另一块栏目"，收了会把预算烧在无关页上
        if not u.startswith(base_dir):
            continue
        _push(u)

    # ② JS 拼的翻页：按 index_N.shtml 规律推（N 从 1 开始 = 第 2 页）
    hints = [int(n) for n in _PAGER_JS_HINT_RE.findall(html or "")]
    cm = _PAGER_JS_COUNT_RE.search(html or "")
    count = None
    if cm is not None:
        try:
            count = int(cm.group(1))
        except ValueError:
            count = None
    if hints or count is not None:
        top = max([*hints, (count - 1) if count else 0] or [0])
        for n in range(1, min(top, max_pages) + 1):
            _push(f"{base_dir}index_{n}.shtml")
    return out


def _unseen_count(source_id: str, items: list[dict]) -> int:
    """这一页的条目里，有多少条**还没见过**（用于"连续几页没新东西就提前停"）。

    只读；一条都查不到时返回 0（宁可多翻一页，也不因为查询异常提前停）。
    """
    if not items:
        return 0
    hashes = [url_hash(it["url"]) for it in items if it.get("url")]
    if not hashes:
        return 0
    marks = ",".join("?" for _ in hashes)
    try:
        row = get_db_connection().execute(
            f"SELECT COUNT(*) AS c FROM announcement_observed"
            f" WHERE source_id=? AND url_hash IN ({marks})",
            [source_id, *hashes]).fetchone()
        return max(0, len(hashes) - int(row["c"]))
    except Exception:  # noqa: BLE001 — 查询失败不影响扫描本身
        return len(hashes)


def _scan_one_source(transport: Any, src: dict, scan_id: str) -> dict:
    """单源扫描：抓取（预算内，**逐页**）→ 解析 → 去重落库。失败诚实归因，绝不假装成功。

    ⚠ **2026-09-24 起会翻页**（改前只取第 1 页）：部委列表一页 20 条、而"新公告"常在第 2..N 页
    ⇒ 只取第 1 页等于放过绝大多数。翻页的三种停法都**如实记账**：页码预算 / 单源时间预算 /
    连续 `STOP_AFTER_BARREN_PAGES` 页一条没见过的都没有（追上历史）。后续页失败**不**把整源判失败
    （留下的页照样算，另记 `page_errors`）。
    """
    result = {"id": src["id"], "name": src.get("name", ""), "status": "ok",
              "http": None, "items": 0, "new_items": 0, "baseline_items": 0,
              "reason": None, "truncated": False, "pages": 0, "_recent": []}
    src_url = src.get("url", "")
    t0 = time.monotonic()
    try:
        status, body = transport.fetch(src_url, timeout=PAGE_TIMEOUT_S)
        result["http"] = status
        html = body if isinstance(body, str) else (
            json.dumps(body, ensure_ascii=False) if body is not None else "")
        if status != 200:
            result["status"] = "failed"
            result["reason"] = f"http_{status}"
            return result
        if looks_like_captcha(html) or status in (403, 429):
            result["status"] = "failed"
            result["reason"] = "waf_captcha"
            return result
        if len(html.encode("utf-8", "ignore")) > PAGE_BYTES_MAX:
            html = html[:PAGE_BYTES_MAX]
            result["truncated"] = True
        items, diag = parse_list_page(html, src_url)
        result["items"] = len(items)
        result["truncated"] = bool(result["truncated"] or diag.get("truncated"))
        if not items:
            result["status"] = "failed"
            result["reason"] = ("js_shell_suspected" if diag.get("js_shell_suspected")
                                else "parse_empty")
            return result

        # ── 逐页翻（2026-09-24）：第 1 页解析**出东西**才谈翻页；一条都没解析出来时翻页没意义 ──
        result["pages"] = 1
        known = {normalize_url(it["url"]) for it in items}
        barren = 0
        for next_url in discover_next_pages(html, src_url):
            if result["pages"] >= PAGES_PER_SOURCE_MAX:
                result["truncated"] = True          # 页码预算用尽（如实标）
                break
            if time.monotonic() - t0 > SOURCE_TIME_BUDGET_S:
                result["truncated"] = True          # 时间预算用尽（如实标）
                break
            time.sleep(PAGE_GAP_S)
            try:
                st2, body2 = transport.fetch(next_url, timeout=PAGE_TIMEOUT_S)
            except Exception:  # noqa: BLE001 — 后续页取不到不拖垮整源
                result["page_errors"] = int(result.get("page_errors") or 0) + 1
                continue
            result["pages"] += 1
            if st2 != 200 or not isinstance(body2, str):
                result["page_errors"] = int(result.get("page_errors") or 0) + 1
                continue
            more, _more_diag = parse_list_page(body2, next_url)
            fresh = [it for it in more if normalize_url(it["url"]) not in known]
            for it in fresh:
                known.add(normalize_url(it["url"]))
            items.extend(fresh)
            if _unseen_count(src["id"], fresh) == 0:
                barren += 1
                if barren >= STOP_AFTER_BARREN_PAGES:
                    break                            # 追上历史了（第 2 次起扫描就便宜）
            else:
                barren = 0
        result["items"] = len(items)

        first_scan = src.get("first_scan_done") is not True
        new_items: list[dict] = []
        with write_transaction() as txn:
            for it in items:
                h = url_hash(it["url"])
                row = txn.execute(
                    "SELECT observed_id FROM announcement_observed"
                    " WHERE source_id=? AND url_hash=?", (src["id"], h)).fetchone()
                if row is not None:
                    txn.execute(
                        "UPDATE announcement_observed SET last_seen=datetime('now')"
                        " WHERE observed_id=?", (row["observed_id"],))
                    continue
                observed_id = f"ann_{ULID()}"
                txn.execute(
                    "INSERT INTO announcement_observed(observed_id, source_id,"
                    " source_name, title, url, url_hash, standard_no, published_date,"
                    " scan_id) VALUES (?,?,?,?,?,?,?,?,?)",
                    (observed_id, src["id"], src.get("name", ""), it["title"],
                     it["url"], h, it.get("standard_no"), it.get("published_date"),
                     scan_id))
                if first_scan:
                    result["baseline_items"] += 1
                else:
                    result["new_items"] += 1
                    new_items.append({"title": it["title"], "url": it["url"],
                                      "published_date": it.get("published_date"),
                                      "source_name": src.get("name", ""),
                                      "first_seen": datetime.utcnow().strftime(
                                          "%Y-%m-%d %H:%M:%S")})
        if first_scan:
            # 首扫基线标记**交给扫描主循环**（2026-11-02 并行化）：
            # 这里原来是 `get_sources() → 改 → _write_json_key()` 的**读改写**，
            # 多线程下两个源同时首扫会互相覆盖（丢一次标记）。
            # 改成把意图带回主循环，由单线程统一写。
            result["_mark_first_scan"] = True
        result["_recent"] = new_items
        upd_log(scan_id, "announce", "INFO", "source_scanned",
                source=src.get("name"), items=result["items"],
                new_items=result["new_items"], baseline=result["baseline_items"],
                duration_ms=int((time.monotonic() - t0) * 1000))
        return result
    except UpdateError as exc:
        result["status"] = "failed"
        result["reason"] = getattr(exc, "code", "UPD-5000")
        upd_log(scan_id, "announce", "WARN", "source_failed",
                source=src.get("name"), reason=result["reason"])
        return result
    except Exception as exc:  # noqa: BLE001 — 单源失败不拖垮整轮扫描
        result["status"] = "failed"
        result["reason"] = f"unreachable: {str(exc)[:120]}"
        upd_log(scan_id, "announce", "WARN", "source_failed",
                source=src.get("name"), reason=result["reason"])
        return result


# ---------------------------------------------------------------- 已见公告查询
def list_items(limit: int = 20, source_id: str | None = None) -> dict:
    """已见公告查询（host 最近列表/历史展示用）：
    **按公告发布日期 DESC**（用户直觉"最新的公告"），无日期排最后，
    同日再按 first_seen/插入序。注意不能按 first_seen 排——那是"我们何时
    见到它"，单页扫描按 HTML 顺序插入（政府列表页从新到旧），同秒
    observed_id DESC 会把页面上最旧的排到最前（真机回归已验证）。"""
    n = max(1, min(int(limit or 20), 200))
    sql = ("SELECT observed_id, source_id, source_name, title, url, standard_no,"
           " published_date, first_seen, last_seen, scan_id"
           " FROM announcement_observed")
    args: list[Any] = []
    if source_id:
        sql += " WHERE source_id=?"
        args.append(source_id)
    sql += (" ORDER BY CASE WHEN published_date IS NULL THEN 1 ELSE 0 END,"
            " published_date DESC, first_seen DESC, observed_id DESC LIMIT ?")
    args.append(n)
    rows = get_db_connection().execute(sql, args).fetchall()
    total = get_db_connection().execute(
        "SELECT COUNT(*) AS c FROM announcement_observed"
        + (" WHERE source_id=?" if source_id else ""), args[:1] if source_id else []
    ).fetchone()["c"]
    return {"items": [dict(r) for r in rows], "total": total}


# ---------------------------------------------------------------- Excel 导出（P1）
_ANN_HEADERS = ["来源源", "标题", "标准号（识别）", "发布日期", "首次发现",
                "最近发现", "链接", "首次扫描"]
_ANN_SOURCE_HEADERS = ["源名称", "URL", "状态", "条目", "新条目", "基线收录", "失败原因"]




def export_announce_xlsx() -> Path:
    """《公告发现》Excel 到 exports 目录：Sheet1 最近扫描（源状态逐源）+
    Sheet2 公告明细全量（发布日期 DESC，与 list_items 同口径）。
    空库同样出文件；纯只读聚合，零库写入。"""
    state = get_scan_state()
    wb = Workbook()

    # ---- Sheet1 最近扫描 ----
    ws = wb.active
    ws.title = "最近扫描"
    ws.cell(row=1, column=1, value="公告发现 · 最近一次扫描").font = Font(size=14, bold=True)
    if state.get("status") in ("done", "failed", "running"):
        ws.cell(row=3, column=1, value="扫描编号").font = Font(bold=True)
        ws.cell(row=3, column=2, value=state.get("scan_id") or "-")
        ws.cell(row=4, column=1, value="状态/触发").font = Font(bold=True)
        ws.cell(row=4, column=2, value=f"{state.get('status')}｜{state.get('trigger') or '-'}")
        ws.cell(row=5, column=1, value="起止").font = Font(bold=True)
        ws.cell(row=5, column=2, value=f"{state.get('started_at') or '-'} → {state.get('finished_at') or '-'}")
        ws.cell(row=6, column=1, value="汇总").font = Font(bold=True)
        ws.cell(row=6, column=2, value=f"条目 {state.get('items_seen', 0)}｜新 {state.get('new_count', 0)}"
                                       f"｜基线 {state.get('baseline_count', 0)}")
        r0 = 8
        ws.cell(row=r0, column=1, value="逐源状态").font = Font(bold=True)
        _xlsx_header_style(ws, r0 + 1, len(_ANN_SOURCE_HEADERS))
        for c, h in enumerate(_ANN_SOURCE_HEADERS, start=1):
            ws.cell(row=r0 + 1, column=c, value=h)
        for i, p in enumerate(state.get("per_source") or []):
            src_url = next((s.get("url", "") for s in get_sources()
                            if s.get("id") == p.get("id")), "")
            ws.cell(row=r0 + 2 + i, column=1, value=p.get("name") or "-")
            ws.cell(row=r0 + 2 + i, column=2, value=src_url)
            ws.cell(row=r0 + 2 + i, column=3, value=p.get("status") or "-")
            ws.cell(row=r0 + 2 + i, column=4, value=p.get("items", 0))
            ws.cell(row=r0 + 2 + i, column=5, value=p.get("new_items", 0))
            ws.cell(row=r0 + 2 + i, column=6, value=p.get("baseline_items", 0))
            ws.cell(row=r0 + 2 + i, column=7, value=p.get("reason") or "")
    else:
        ws.cell(row=3, column=1, value=f"状态：{state.get('status', 'never')}（尚未完成过扫描）")
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 48

    # ---- Sheet2 公告明细全量（发布日期 DESC；无日期排最后——list_items 同口径） ----
    wd = wb.create_sheet("公告明细")
    wd.append(_ANN_HEADERS)
    all_rows = get_db_connection().execute(
        "SELECT source_name, title, standard_no, published_date, first_seen,"
        " last_seen, url, scan_id FROM announcement_observed"
        " ORDER BY CASE WHEN published_date IS NULL THEN 1 ELSE 0 END,"
        " published_date DESC, first_seen DESC, observed_id DESC").fetchall()
    for r in all_rows:
        wd.append([r["source_name"] or "-", r["title"] or "-", r["standard_no"] or "",
                   r["published_date"] or "", r["first_seen"] or "", r["last_seen"] or "",
                   r["url"] or "-", r["scan_id"] or "-"])
    if wd.max_row > 1:
        _xlsx_header_style(wd, 1, len(_ANN_HEADERS))
        wd.freeze_panes = "A2"
        wd.auto_filter.ref = f"A1:{get_column_letter(len(_ANN_HEADERS))}{wd.max_row}"
    widths = [18, 50, 18, 12, 18, 18, 52, 22]
    for i, w in enumerate(widths, start=1):
        wd.column_dimensions[get_column_letter(i)].width = w

    out = (_exports_dir() /
           f"公告发现_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
    wb.save(str(out))
    upd_log(state.get("scan_id") or "announce", "announce", "INFO",
            "announce_exported", rows=len(all_rows))
    return out
