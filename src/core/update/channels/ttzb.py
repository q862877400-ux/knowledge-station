"""ttbz适配器（2026-08 实测，巡检时效）。

全国团体标准信息平台（www.ttbz.org.cn）——团体标准（T/）状态权威渠道。

探明结论（2026-08-24 实测）：
- 检索接口：POST https://www.ttbz.org.cn/cms-proxy/ms/portal/standardInfo/
  getPortalStandardList，表单 pageNo/pageSize/searchKey（生产页 ``API_PREFIX``
  = ``/cms-proxy``；本机 8080 时为空串）。``searchKey`` 是模糊 contains
  （``data.total`` 封顶 100），必须客户端按归一号精确挑选；服务端已把标准号
  长横 U+2014 与 "-" 归一等价（T/ZSA 328-2026 可命中 T/ZSA 328—2026 且排首位）。
- 详情页：GET https://www.ttbz.org.cn/standardDetail/<standardUniqueId>.html
  （伪静态路由，缺 ``.html`` 后缀返回 404 {"msg":"资源不存在"}）。静态页约
  227KB，含三处关键结构：
  * JSON-LD(TechArticle)：``identifier``=标准号、``datePublished``=发布日期、
    ``dateModified``=文件公布日期、``author.name``=所属团体；
  * ``<script type="application/json" id="portal-standard-detail-json">``：
    standardStatusName / publishDate / implementDate / filePublishDate /
    abolishDate / organName / isSale 等结构化字段；
  * 状态行 ``<span class="el-tag ...">现行</span>``（全页唯一 el-tag）。
  标准状态字典仅 现行(1)/废止(2)；页面 JS 时间线另有 废止→ABOLISH 映射。
- 废止标准不进入常规检索：getDisabledStandardList 是不接受过滤的废止列表且
  standardUniqueId 恒 null，无法按号定位详情 → 废止在 ttzb 层按查无处理，
  交降级链（official_gb→web→govcn）兜底。
- 全文 isSale:1 可出售（登录+付费）；本渠道只做元数据状态，不做全文。

解析要点：JSON-LD 只取 ``@type=TechArticle`` 的块（页面另有 BreadcrumbList 与
含尾逗号的非标准 JSON 块，解析失败跳过）；状态优先级 状态行 → portal blob →
检索行 standardStatusName；``legal_status`` 经 base.map_state_text 映射
（现行→effective / 废止→withdrawn），未知串告警不猜测。``effective_date`` 取
JSON-LD ``datePublished``（发布日期，与 official_gb 渠道 dates[0] 口径一致）。
详情页失败降级检索行（同平台官方字段），evidence_url 仍指向详情页。

mock 应答契约（离线表驱动，两段应答按 seq 弹出）：
1. 检索：{"result":true,"code":200,"data":{"total":N,"rows":[
   {"standardUniqueId","standardNo","standardTitleCn","standardStatusName",
    "publishDate","implementDate","filePublishDate","abolishDate","organName"}]}}
2. 详情：HTML 字符串，含 ``<script type="application/ld+json">``（TechArticle）与
   状态行 ``<span class="el-tag...">现行</span>``。
"""
from __future__ import annotations

import json
import re
from time import perf_counter
from typing import Any

from src.core.update.channels.base import (
    ChannelAdapter,
    ChannelResult,
    UpdateError,
    derive_change_type,
    looks_like_captcha,
    map_state_text,
    norm_no,
    query_no,
    upd_log,
)

#: 检索接口（生产 API_PREFIX=/cms-proxy，2026-08 实测）
SEARCH_URL = ("https://www.ttbz.org.cn/cms-proxy/ms/portal/standardInfo/"
              "getPortalStandardList")
#: 详情页伪静态路由（缺 .html 后缀 404）
DETAIL_URL = "https://www.ttbz.org.cn/standardDetail/{sid}.html"

_JSON_LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
_PORTAL_RE = re.compile(
    r'<script type="application/json" id="portal-standard-detail-json">(.*?)</script>',
    re.S)
#: 状态行：详情页全页唯一 el-tag span
_STATUS_LINE_RE = re.compile(
    r'<span class="el-tag[^"]*">\s*(现行|即将实施|被代替|废止)\s*</span>')
#: raw 收录子集（不落全文/大字段，保持确定性小载荷）
#: ⚠ `implementDate` 是 §11.0 R6c-3e 补进来的：**它在真实响应里一直有**（复核 b34 实测
#: T/CECS 2350-2026 的 `implementDate=2026-12-01`），旧代码只读 `datePublished` 就填
#: `effective_date` ⇒ 发布被当实施，差 6 个月。
_JSON_LD_KEYS = ("@type", "identifier", "headline", "datePublished", "implementDate",
                 "dateModified", "author")
_PORTAL_KEYS = ("id", "standardUniqueId", "standardNo", "standardTitleCn",
                "organName", "standardStatus", "standardStatusName", "status",
                "statusName", "isSale", "isOpen", "publishDate", "implementDate",
                "filePublishDate", "abolishDate")
_ROW_KEYS = ("standardNo", "standardTitleCn", "standardStatusName", "statusName",
             "publishDate", "implementDate", "filePublishDate", "abolishDate",
             "organName", "isSale", "isOpen")


def _pick_dates(json_ld: dict, portal: dict, row: dict) -> tuple[str | None, str | None]:
    """三级回退取（**实施日期, 发布日期**）——两个日期两个槽（§11.0 R6c-3e）。

    为什么必须有这两个槽：本适配器原来把 `datePublished`（发布）直接填进 `effective_date`
    （实施），实测量级差 6 个月。**只有发布、没有实施时，`effective_date` 返回 `None`**：
    宁可让"实施"空着，也不要拿发布日期顶上——那正是这次要修的形态。
    """
    def _s(v: object) -> str | None:
        t = str(v).strip() if v is not None else ""
        return t or None

    pub = _s(json_ld.get("datePublished") or portal.get("publishDate")
             or row.get("publishDate"))
    impl = _s(json_ld.get("implementDate") or portal.get("implementDate")
              or row.get("implementDate"))
    return impl, pub


def _canon(no: str | None) -> str:
    """归一号 + 破折号归一：平台用长横 U+2014，用户常写 -，两者等价比较。"""
    return norm_no(no).replace("\u2014", "-")


def _core(no_norm: str) -> str:
    """去年代（兼容 - 与 —）：TZSA328-2026 → TZSA328，供同主体候选比较。"""
    return re.sub(r"[—-]?\d{4}$", "", no_norm)


class TtzbAdapter(ChannelAdapter):
    """ttbz：标准号级状态探测（确定性、离线可测、异常归一）。"""

    name = "ttbz"

    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        t0 = perf_counter()
        # ⚠ 查询用 `query_no`（全角斜杠换半角，§11.0 R6c-2b）
        status, body = self._fetch(
            SEARCH_URL, method="post",
            data={"pageNo": 1, "pageSize": 20,
                  "searchKey": query_no(standard_no).strip()})

        # 验证码特征优先判定：半自动降级标记，绝不当 miss 处理（F-11）
        if looks_like_captcha(body):
            return self._log_probe(t0, standard_no, ChannelResult(
                channel=self.name, found=False, captcha=True,
                raw={"http": status, "body": body}))

        rows = self._rows_of(body)
        row = self._pick_row(rows, standard_no)
        if row is None:
            return self._miss(t0, standard_no, status,
                              note=f"no_match rows={len(rows)}")
        return self._resolve_detail(t0, standard_no, row, status)

    # -------------------------------------------------------------- 检索层
    def _rows_of(self, body: Any) -> list[Any]:
        """检索应答 → 行表；非 JSON / result=False / 异常形态一律空表（诚实 miss）。"""
        if isinstance(body, dict) and body.get("result") is not False:
            data = body.get("data") or {}
            rows = data.get("rows") if isinstance(data, dict) else None
            if isinstance(rows, list):
                return rows
        return []

    def _pick_row(self, rows: list[Any], standard_no: str) -> dict | None:
        """行挑选：精确归一号匹配优先；否则同主体（去年代）取号最大者，保证确定性。"""
        target = _canon(standard_no)
        for r in rows:
            if isinstance(r, dict) and _canon(str(r.get("standardNo") or "")) == target:
                return r
        core = _core(target)
        cands = [r for r in rows
                 if isinstance(r, dict)
                 and _core(_canon(str(r.get("standardNo") or ""))) == core]
        if not cands:
            return None
        return max(cands, key=lambda r: _canon(str(r.get("standardNo") or "")))

    # -------------------------------------------------------------- 详情层
    def _resolve_detail(self, t0: float, standard_no: str, row: dict,
                        search_status: int) -> ChannelResult:
        sid = str(row.get("standardUniqueId") or "").strip()
        evidence = DETAIL_URL.format(sid=sid) if sid else None
        detail_status: int | None = None
        json_ld: dict[str, Any] = {}
        portal: dict[str, Any] = {}
        status_line: str | None = None
        if sid:
            try:
                detail_status, dbody = self._fetch(evidence or "")
            except UpdateError as exc:  # 详情失败降级检索行（同平台官方字段）
                upd_log(self.trace_id, f"channel.{self.name}", "WARN",
                        "detail_fetch_failed_fallback_row",
                        standard_no=standard_no,
                        error=f"{type(exc).__name__}: {exc}")
                detail_status = None
            else:
                if isinstance(dbody, str):
                    json_ld = self._extract_json_ld(dbody)
                    portal = self._extract_portal(dbody)
                    status_line = self._extract_status_line(dbody)

        latest = str(json_ld.get("identifier") or portal.get("standardNo")
                     or row.get("standardNo") or "").strip()
        raw_state = str(status_line or portal.get("standardStatusName")
                        or row.get("standardStatusName") or "").strip()
        legal_status = map_state_text(raw_state)
        if raw_state and legal_status is None:
            # INS-B-05/D-06：非法状态串降级为告警，不猜测不写脏值
            upd_log(self.trace_id, f"channel.{self.name}", "WARN",
                    "illegal_state_text", standard_no=standard_no,
                    state=raw_state)
        # ⚠ 两个日期两个槽（§11.0 R6c-3e）。**旧写法把"发布"塞进了 `effective_date`**——
        #   独立复核 b34 真网络实测：`T/CECS 2350-2026` 发布 `2026-06-12`、实施 `2026-12-01`，
        #   **差了 6 个月**，而真实响应里本来就有 `implementDate`（本文件的 `_PORTAL_KEYS`/`_ROW_KEYS`
        #   里都登记着它，只是从没被读过）。这是与 `official_gb` 同一类的 P1 错标。
        impl_date, pub_date = _pick_dates(json_ld, portal, row)

        result = ChannelResult(
            channel=self.name,
            found=True,
            change_type=derive_change_type(_canon(standard_no), _canon(latest),
                                           legal_status),
            legal_status=legal_status,
            latest_version=latest or None,
            effective_date=impl_date,
            published_date=pub_date,
            evidence_url=evidence,
            raw=self._raw_of(search_status, detail_status, row, json_ld,
                             portal, status_line),
        )
        return self._log_probe(t0, standard_no, result)

    def _raw_of(self, search_status: int, detail_status: int | None,
                row: dict, json_ld: dict, portal: dict,
                status_line: str | None) -> dict[str, Any]:
        raw: dict[str, Any] = {
            "http": {"search": search_status, "detail": detail_status},
            "row": {k: row.get(k) for k in _ROW_KEYS},
        }
        if json_ld:
            raw["json_ld"] = {k: json_ld.get(k) for k in _JSON_LD_KEYS}
        if portal:
            raw["portal"] = {k: portal.get(k) for k in _PORTAL_KEYS}
        if status_line:
            raw["status_line"] = status_line
        if not (json_ld or portal or status_line):
            # 详情页无可用信号（超时/非 200/缺 JSON-LD 等）→ 降级检索行，显式标注
            raw["note"] = "detail_fallback:row"
        return raw

    # -------------------------------------------------------------- HTML 解析
    def _extract_json_ld(self, body: str) -> dict[str, Any]:
        """取 @type=TechArticle 的 JSON-LD 块；其他块（BreadcrumbList/尾逗号坏 JSON）跳过。"""
        for m in _JSON_LD_RE.finditer(body):
            try:
                obj = json.loads(m.group(1))
            except Exception:  # noqa: BLE001 —— 页面含非标准 JSON 块，跳过
                continue
            if isinstance(obj, dict) and obj.get("@type") == "TechArticle":
                return obj
        return {}

    def _extract_portal(self, body: str) -> dict[str, Any]:
        """portal-standard-detail-json 结构化字段（含 standardStatusName/各日期）。"""
        m = _PORTAL_RE.search(body)
        if not m:
            return {}
        try:
            obj = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            return {}
        return obj if isinstance(obj, dict) else {}

    def _extract_status_line(self, body: str) -> str | None:
        """状态行（全页唯一 el-tag span）：现行/即将实施/被代替/废止。"""
        m = _STATUS_LINE_RE.search(body)
        return m.group(1).strip() if m else None
