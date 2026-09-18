"""ndls适配器（2026-08 实测，巡检时效）。

国家数字标准馆·中国标准化研究院（ndls.cnis.ac.cn，跨门类状态权威，2026-08 实测）：
- 搜索（标准号→id）：POST https://ndls.cnis.ac.cn/api/standard/list
  请求 JSON 与站点前端 getSearchData(paramsType=1) 同款（page/size/keyword + 空过滤字段）；
  应答 {code:0, data:{results:[{yf001(id), a100(标准号), a000(状态), a298(名称),
  a101(发布日期), a205(实施日期), ...}]}}。
- 详情：GET https://ndls.cnis.ac.cn/api/standard/detail/<id>
  应答 {code:0, data:{a000(状态), a100(标准号), a101(发布日期), a205(实施日期),
  a206(废止日期), a461list(代替标准), a462list(被代替标准), a298(名称), ...}}；
  详情页 https://ndls.cnis.ac.cn/standard/detail/<id> 直接呈现 废止日期/代替关系
  （AQ 3028-2008 实测 a000=作废、a206=2024-07-01；GB 18218-2018 实测 a000=现行、a206=null）。

状态词表（ndls 专属，2026-08 聚合实测）：现行/未生效/被代替/作废/废止/废止转行标/已修订/
历史/正在起草/正在征求意见/正在审查/正在批准/暂不实施。映射取确定性白名单：
现行→effective、未生效→upcoming、被代替→superseded、作废/废止/废止转行标→withdrawn、
已修订→superseded；其余（历史/起草态/暂不实施等）→None 并告警，不猜测（INS-B-05）。

Jiasule WAF（观察模式）：浏览器 UA + 会话 cookie jar（默认 transport 即 Session 维持）
+ 调用间限速（PAUSE_S=1.0s，仅真实 transport 生效，mock 不睡眠保测试速度）。

mock 应答契约（离线表驱动，两段 respond 依次弹出）：
- ① 搜索：{"http":200,"body":{"code":0,"data":{"results":[
  {"yf001":"<id>","a100":"GB 18218-2018","a000":"现行","a298":"名称",
   "a101":"2018-11-19","a205":"2019-03-01"}]}}}
- ② 详情：{"http":200,"body":{"code":0,"data":{"a100":...,"a000":...,"a101":...,
  "a205":...,"a206":...,"a461list":[...],"a462list":[...]}}}
"""
from __future__ import annotations

import re
import time
from time import perf_counter
from typing import Any
from urllib.parse import quote

from src.core.update.channels.base import (
    ChannelAdapter,
    ChannelResult,
    CurlCffiTransport,
    HttpxTransport,
    derive_change_type,
    looks_like_captcha,
    map_state_text,
    norm_no,
    query_no,
    strip_year,
    upd_log,
)

#: ndls 专属状态词表 → legal_status（确定性白名单；未知串告警不猜测）
NDLS_STATE_MAP = {
    "现行": "effective",
    "未生效": "upcoming",
    "被代替": "superseded",
    "作废": "withdrawn",       # ndls 对「废止」的常用表述（AQ 3028-2008 实测）
    "废止": "withdrawn",
    "废止转行标": "withdrawn",   # 标准本身已废止（转入行业标准体系）
    "已修订": "superseded",      # 已修订 = 新版代替旧版
}

#: 浏览器 UA（Jiasule WAF 观察模式放行浏览器指纹；2026-08 实测）
_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


class NdlsAdapter(ChannelAdapter):
    """ndls：标准号级状态探测（确定性、离线可测、异常归一）。"""

    name = "ndls"
    BASE = "https://ndls.cnis.ac.cn"
    SEARCH_URL = f"{BASE}/api/standard/list"
    DETAIL_URL = f"{BASE}/api/standard/detail/{{did}}"
    EVIDENCE_URL = f"{BASE}/standard/detail/{{did}}"
    #: Jiasule WAF 观察模式：真实网络调用间限速（mock 不睡眠）
    PAUSE_S = 1.0

    def probe(self, standard_no: str, standard_name: str = "",
              *, detail: bool = True) -> ChannelResult:
        """探测单号状态。detail=False（体检模式）跳过详情请求，
        状态/日期直接取搜索行 a000/a101/a205，请求减半、风控更少；
        缺废止日期/代替关系（_from_row note="row_only"）。默认 detail=True 行为不变。
        """
        t0 = perf_counter()

        # 1) 按标准号搜索 → id（POST JSON，站点前端同款请求体）
        # ⚠ **请求体里的关键词也要用 `query_no`**（§11.0 R6c-2b 补，独立复核 b31 抓到的反例）：
        #   上一轮只改了 Referer，请求体仍带原始全角 `／`——"送出去的请求里没有全角"这条声明
        #   因此对 ndls **不成立**（而它是 routing 会把 AQ/GB 送过去的可达渠道）。
        #   站点两种写法都收（复核实测 3 号×2 写法全 found=True），所以这不是"修好才能用"，
        #   而是**口径一致**：查询值一律用规范形，别留下"有的渠道折了、有的没折"的缝。
        status, body = self._fetch(
            self.SEARCH_URL,
            method="post",
            json=self._search_body(query_no(standard_no)),
            # ⚠ Referer 里的关键词必须**转义成 ASCII**（§11.0 R6c-2a，独立复核 b30 定位）：
            #   真库 92% 的标准号含全角斜杠 `／`，而 HTTP 头按 latin-1 编码 ⇒ 带着原始号拼 Referer
            #   会在**请求发出之前**抛 `UnicodeEncodeError`：这条渠道对那 92% 的号**根本发不出请求**，
            #   现场却只表现为"每个号都失败"（与"站点查不到"完全不同的原因）。
            #   同仓已有正确写法可参照：`hbba.py:89` 用 `quote(key)`。
            headers=self._headers(f"standard/index?keyword={quote(standard_no, safe='')}"),
        )
        if looks_like_captcha(body):
            return self._log_probe(t0, standard_no, ChannelResult(
                channel=self.name, found=False, captcha=True,
                raw={"http": status, "body": body}))
        row, note = self._pick_search_row(body, standard_no)
        if row is None:
            return self._miss(t0, standard_no, status,
                              note=note or "search_hits=0")
        did = str(row.get("yf001") or "").strip()
        if not did:
            return self._miss(t0, standard_no, status, note="search_row_no_id")
        if not detail:
            # 体检模式：不发详情请求，状态用搜索行（a000 已含状态）
            upd_log(self.trace_id, f"channel.{self.name}", "INFO",
                    "probe_row_only", standard_no=standard_no,
                    note="detail_skipped_by_check_mode")
            return self._log_probe(t0, standard_no,
                                   self._from_row(status, row, note="row_only"))

        # 2) 详情（含废止日期/代替关系）——限速后再发
        self._pace()
        status2, detail = self._fetch(
            self.DETAIL_URL.format(did=did),
            headers=self._headers(f"standard/detail/{did}"),
        )
        data = self._detail_data(detail)
        if data is None:
            # 详情不可用：降级用搜索行状态（a000 已含状态），诚实注明 detail_unavailable
            upd_log(self.trace_id, f"channel.{self.name}", "WARN",
                    "detail_unavailable_fallback_search_row",
                    standard_no=standard_no, http=status2)
            return self._log_probe(t0, standard_no,
                                   self._from_row(status2, row,
                                                  note="detail_unavailable"))
        return self._log_probe(t0, standard_no,
                               self._from_detail(status2, data, did, standard_no))

    # ---------------------------------------------------------- 请求构造
    @staticmethod
    def _headers(ref: str) -> dict:
        return {
            "User-Agent": _BROWSER_UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": f"{NdlsAdapter.BASE}/{ref}",
            "Origin": NdlsAdapter.BASE,
            "X-Requested-With": "XMLHttpRequest",
        }

    @staticmethod
    def _search_body(keyword: str, page: int = 1, size: int = 10) -> dict:
        """与站点前端 getSearchData(paramsType=1) 同款 JSON 体（2026-08 实测）。"""
        return {
            "page": page, "size": size,
            "post_ics_level1": "", "post_ccs_level1": "", "post_publicyear": "",
            "post_a104": "", "post_country_name": "", "post_a000": "",
            "keyword": keyword, "orderby": "",
            "publicyear": "", "a825": "", "a826": "", "country_name": "",
            "a104": "", "sub_type": "", "code_type": "", "owner": "",
            "ccs_level1": "", "ccs_level2": "", "ccs_level3": "",
            "ics_level1": "", "ics_level2": "", "ics_level3": "",
            "a000": "", "yearfrom": "", "yearto": "", "a209": "", "draftman": "",
        }

    def _pace(self) -> None:
        """真实网络调用间限速（Jiasule WAF 观察模式）；mock 传输不睡眠保测试速度。"""
        if isinstance(self.transport, (CurlCffiTransport, HttpxTransport)):
            time.sleep(self.PAUSE_S)

    # ---------------------------------------------------------- 解析
    @staticmethod
    def _dash_norm(no: str) -> str:
        """标准号匹配归一：长横/短横统一为连字符后再 norm_no（站点数据含 en-dash）。"""
        return norm_no(re.sub(r"[–—]", "-", no or ""))

    @staticmethod
    def _state_of(a000: str | None) -> tuple[str | None, bool]:
        """ndls 状态串 → legal_status；未知非空串返回 (None, True) 表示需告警。"""
        text = (a000 or "").strip()
        if not text:
            return None, False
        mapped = NDLS_STATE_MAP.get(text) or map_state_text(text)
        return mapped, mapped is None

    def _pick_search_row(self, body: Any,
                         standard_no: str) -> tuple[dict | None, str | None]:
        """搜索结果行挑选：code==0 且 results 非空；精确归一号优先，否则同主体取号最大。

        返回 (row, note)：row=None 时 note 说明未命中原因（确定性、不抛异常）。
        """
        if not isinstance(body, dict):
            return None, f"unexpected_body:{type(body).__name__}"
        if body.get("code") != 0:
            msg = str(body.get("message") or "unknown")
            return None, f"api_code_{body.get('code')}:{msg}"
        results = (body.get("data") or {}).get("results") or []
        if not results:
            return None, "search_hits=0"
        target = self._dash_norm(standard_no)
        for r in results:
            if isinstance(r, dict) and \
                    self._dash_norm(str(r.get("a100") or "")) == target:
                return r, None
        core = strip_year(target)
        cands = [r for r in results
                 if isinstance(r, dict) and
                 strip_year(self._dash_norm(str(r.get("a100") or ""))) == core]
        if not cands:
            return None, f"no_row_for_{standard_no}"
        return max(cands, key=lambda r: self._dash_norm(str(r.get("a100") or ""))), None

    @staticmethod
    def _detail_data(body: Any) -> dict | None:
        """详情 JSON → data 字典；code!=0 / 非 JSON / data 非对象 → None（调用方降级）。"""
        if not isinstance(body, dict) or body.get("code") != 0:
            return None
        data = body.get("data")
        return data if isinstance(data, dict) else None

    def _from_row(self, http: int, row: dict, note: str) -> ChannelResult:
        """搜索行降级结果（详情不可用时）：状态/日期取自列表行，缺废止日期/代替关系。"""
        a000 = str(row.get("a000") or "").strip()
        legal, unknown = self._state_of(a000)
        if unknown:
            upd_log(self.trace_id, f"channel.{self.name}", "WARN",
                    "illegal_state_text", standard_no=row.get("a100"), state=a000)
        version = str(row.get("a100") or "").strip() or None
        impl = str(row.get("a205") or "").strip() or None
        pub = str(row.get("a101") or "").strip() or None
        return ChannelResult(
            channel=self.name, found=True,
            change_type=derive_change_type(str(row.get("a100") or ""), version, legal),
            legal_status=legal, latest_version=version,
            # ⚠ 实施槽**只放实施日期**（§11.0 R6c-3f，复核 b36 的 A-观察）：
            #   原来写 `impl or pub`——实施缺失时把**发布日期**顶上，与 ttzb 那处错标同形。
            #   发布日期现在有自己的槽（published_date），不必再来顶实施槽。
            effective_date=impl,
            # 发布日期单独落槽（§11.0 R6c-3e）：a101 本来就被解析出来了，
            # 以前只有 effective_date 一个槽 ⇒ "发布"这一类拿不到它（复核 b35 的结论之一）。
            published_date=pub,
            evidence_url=None,  # 无详情页（id 在 row 里但详情不可达）→ 不给证据链接
            raw={"http": http, "note": note, "status_text": a000,
                 "search_row": {k: row.get(k) for k in
                                ("yf001", "a100", "a000", "a298", "a101", "a205")}},
        )

    def _from_detail(self, http: int, data: dict, did: str,
                     standard_no: str) -> ChannelResult:
        a000 = str(data.get("a000") or "").strip()
        legal, unknown = self._state_of(a000)
        if unknown:
            upd_log(self.trace_id, f"channel.{self.name}", "WARN",
                    "illegal_state_text", standard_no=data.get("a100"), state=a000)
        pub = str(data.get("a101") or "").strip() or None   # 发布日期
        impl = str(data.get("a205") or "").strip() or None  # 实施日期
        wd = str(data.get("a206") or "").strip() or None    # 废止日期
        a100 = str(data.get("a100") or "").strip() or None
        version = self._newer_version(data, standard_no) or a100
        # 废止标准以废止日期为关键日期；否则实施日期；**都没有就不填**
        # （§11.0 R6c-3f：不再拿发布日期顶实施槽——它有 published_date 自己的位置）
        eff: str | None
        if legal == "withdrawn" and wd:
            eff = wd
        elif impl:
            eff = impl
        else:
            eff = None
        raw = {
            "http": http, "id": did, "status_text": a000,
            "issue_date": pub, "impl_date": impl, "withdrawn_date": wd,
            # 代替关系按站点标签原样透传（a461=代替标准，a462=被代替标准）
            "a461list": data.get("a461list") or [],
            "a462list": data.get("a462list") or [],
            "name": data.get("a298"),
        }
        return ChannelResult(
            channel=self.name, found=True,
            change_type=derive_change_type(standard_no, version, legal),
            legal_status=legal, latest_version=version,
            effective_date=eff,
            published_date=pub,
            evidence_url=self.EVIDENCE_URL.format(did=did),
            raw=raw,
        )

    @staticmethod
    def _newer_version(data: dict, standard_no: str) -> str | None:
        """代替关系中找比请求号更新的同主体标准号（确定性；无则 None）。

        仅取同主体（去年代）且年代大于请求号的条目，取年代最大者；
        GB 18218-2018 的代替关系是旧版 2009 → 返回 None，交由 derive_change_type
        判 no_change；AQ 3028-2008 无新版 → None + withdrawn 由状态词表决定。
        """
        target_core = strip_year(norm_no(standard_no))
        m = re.search(r"(\d{4})$", norm_no(standard_no))
        if not m:
            return None
        target_year = int(m.group(1))
        cands: list[tuple[int, str]] = []
        for key in ("a461list", "a462list"):
            for item in data.get(key) or []:
                no = str(item or "").strip()
                n = norm_no(no)
                if strip_year(n) == target_core:
                    mm = re.search(r"(\d{4})$", n)
                    if mm and int(mm.group(1)) > target_year:
                        cands.append((int(mm.group(1)), no))
        if not cands:
            return None
        _, best = max(cands)
        return best
