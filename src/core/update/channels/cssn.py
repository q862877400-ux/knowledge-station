# -*- coding: utf-8 -*-
"""cssn适配器（2026-08-27 实测定型，全覆盖状态权威）。

中国标准服务网 www.cssn.net.cn（与 spc.org.cn 中国标准出版社同源，site_code=SPCELEC）：
- GET https://www.cssn.net.cn/api/standards/list?keyword=<标准号>
  返回 JSON：{count, results:[{yf001(id), a000(状态), a100(标准号), a298(名称),
  a301, a302(英文名), a101(发布日期), publicyear, a205(实施日期), a825(CCS),
  a825name, a826(ICS), a826name, country_name, formats(价格/格式), code_type, ...}]}
- 覆盖：全门类国标（食品安全 GB 5009/2760、工程建设 GB 5xxxx、强制 GB/推荐 GB/T/
  指导性 GB/Z）——openstd/std.samr 不收录的都在（2026-08-27 实测 GB 5009.247-2025、
  GB 14048.1-2012、GB 11859.1-1989、GB 12695-2016 全部命中并带 状态/发布/实施日期）。
- keyword 是全文模糊检索但**精确匹配优先排序**：带空格完整号（'GB 5009.247-2025'）
  精确行排第 1；含点/常见数字的号噪声大（'2025'/'2012' 年份词会捞出一堆 AQ/JJF/DB），
  须用 pick_row_by_norm 精确挑选；若精确行被挤出前 20，回退用数字核心号再查一次。曾
  miss 的坑是传无空格全大写 'GB5009.247-2025'（拆词成 2025）→ 正确用带空格完整号。
- 无 Jiasule 验证码（curl_cffi chrome 指纹实测均 200 JSON），可替代 ndls 做 n 轮补查。

状态词表（实测采样 现行/被代替/作废/未生效；未知串告警不猜测——INS-B-05）：
现行→effective、未生效→upcoming、被代替→superseded、作废/废止→withdrawn。

mock 应答契约（离线表驱动，同 04a §0）：
``{"http":200,"body":{"count":2,"results":[
  {"yf001":"<id>","a000":"现行","a100":"GB 30871-2022","a298":"名称",
   "a101":"2022-03-15","a205":"2022-10-01","a825":"C65","a826":"13.100"},
  {"yf001":"<id>","a000":"被代替","a100":"GB 30871-2014","a298":"名称",
   "a101":"2014-07-24","a205":"2015-06-01"}]}}``
"""
from __future__ import annotations

import re
import time
import urllib.parse
from time import perf_counter
from typing import Any

from src.core.update.channels.base import (
    ChannelAdapter,
    ChannelResult,
    CurlCffiTransport,
    HttpxTransport,
    derive_change_type,
    looks_like_captcha,
    norm_no,
    query_no,
    upd_log,
)

#: cssn 专属状态词表 → legal_status（确定性白名单；未知串告警不猜测）
CSSN_STATE_MAP = {
    "现行": "effective",
    "未生效": "upcoming",
    "被代替": "superseded",
    "作废": "withdrawn",       # cssn 实测（GB/T 12245-2006 旧版 → 作废）
    "废止": "withdrawn",
    "废止转行标": "withdrawn",   # 实测标准本身已废止（转入行业标准体系）
}

#: 标准号拆分：去掉 GB/GBT/GBZ 前缀 + 年份，得数字主体（跨前缀同主体匹配用）
_CORE_RE = re.compile(r"^(?:GB[ZT]?)?(\d+(?:\.\d+)*)(?:-(\d{4}))?$")

#: 浏览器 UA（无验证码仍带浏览器指纹保平安；2026-08-27 实测）
_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


class CssnAdapter(ChannelAdapter):
    """cssn：标准号级状态探测（全覆盖、无验证码、确定性、离线可测、异常归一）。"""

    name = "cssn"
    SEARCH_URL = "https://www.cssn.net.cn/api/standards/list"
    INDEX = "https://www.cssn.net.cn/cssn/index"
    #: 无 Jiasule，但保持调用间限速（政府/商业站点礼貌速率；mock 不睡眠保测试速度）
    PAUSE_S = 1.0

    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        t0 = perf_counter()
        # keyword 保留标准空格（cssn 按空格分词，带空格完整号精确行排第 1）
        keyword, row, note = self._search_row(standard_no)
        if row is None:
            return self._miss(t0, standard_no, 200, note=note or "no_match")
        return self._log_probe(t0, standard_no,
                               self._from_row(200, row,
                                              standard_no, mode=note or "primary"))

    # ---------------------------------------------------------- 搜索
    def _search_row(self, standard_no: str) -> tuple[str, dict | None, str | None]:
        """带空格完整号单次搜索（契约：每渠道恰一次请求）；返回 (keyword, row, mode)。

        cssn 精确匹配优先排序，带空格完整号（'GB 5009.247-2025'）精确行排第 1，
        无需二次回退；含点/常见数字的噪声交给 _pick 跨前缀精确挑选。
        """
        keyword = query_no(standard_no).strip()   # 全角斜杠换半角（§11.0 R6c-2b）
        row, mode = self._hit(keyword, standard_no)
        return keyword, row, mode or "no_match"

    def _hit(self, keyword: str, standard_no: str) -> tuple[dict | None, str | None]:
        """单次搜索后精确挑选匹配行（禁验证码硬闯；非 dict 响应直接 miss）。"""
        try:
            status, body = self._fetch(
                self.SEARCH_URL,
                params={"keyword": keyword},
                headers={"User-Agent": _BROWSER_UA,
                         "Referer": self.INDEX,
                         "Accept": "application/json"},
            )
        except Exception as e:  # noqa: BLE001 —— 归一为未命中（交上层降级链）
            upd_log(self.trace_id, f"channel.{self.name}", "WARN", "fetch_error",
                    standard_no=standard_no, error=f"{type(e).__name__}: {e}")
            return None, None
        # 调用间礼貌限速（模拟人类节奏；仅真实 transport 睡眠，mock 不睡保测试速度）
        self._pace()
        if looks_like_captcha(body):
            return None, None   # 外层 _search_row 无法透传 captcha 标记 → 走 miss 且 WARN
        if not isinstance(body, dict) or body.get("code") not in (0, None):
            return None, None
        results = body.get("results") or []
        if isinstance(results, list):
            return self._pick(results, standard_no)
        return None, None

    def _pace(self) -> None:
        """调用间限速（Jiasule/商业站礼貌速率）；mock transport 不睡眠保测试速度。"""
        if isinstance(self.transport, (CurlCffiTransport, HttpxTransport)):
            time.sleep(self.PAUSE_S)

    @staticmethod
    def _split(norm: str) -> tuple[str, int | None]:
        """归一号 → (数字主体, 年份)；无法解析返回 ('', None)。"""
        m = _CORE_RE.match(norm)
        if not m:
            return norm, None
        year = int(m.group(2)) if m.group(2) else None
        return m.group(1), year

    @staticmethod
    def _pick(rows: list[Any], standard_no: str) -> tuple[dict | None, str | None]:
        """跨前缀同主体挑选（GB/GB/T/GB/Z 视为同一标准的不同属性/版本）。

        强制 GB 转推荐后库内为 GB/T 版（如 GB 14048.1-2012 → GB/T 14048.1-2012），
        pick_row_by_norm 因前缀不同把 GB/GB/T 当不同主体而误取旧版/miss；这里只比
        数字主体（14048.1）**优先取同年份版**（[被代替] 才是 2012 版的真实状态），
        同年份缺失才退回年代最大者。返回 (row, mode)：exact|cross_prefix_same_year
        |cross_prefix_latest|None。

        ⚠ **2026-09-22 改成 staticmethod**（只是去掉那个没被用到的 ``self``，语义一字未动）：
        CCS 补全链（``knowledge/ccs_fetcher``）要拿**同一份**挑选逻辑去挑
        ``/api/cssn/list`` 的 HTML 条目 —— 那边不该为了调一个函数去 new 一个适配器
        实例（会顺带 new 一个 HTTP 会话）。CSSN 的"怎么算挑中了"只有这一份所有者，
        复制一份到 ccs_fetcher 迟早跟这里漂移。
        """
        target = norm_no(standard_no)
        for r in rows:
            if norm_no(str(r.get("a100") or "")) == target:
                return r, "exact"
        tcore, tyear = CssnAdapter._split(target)
        if not tcore:
            return None, None
        cands: list[tuple[int, dict]] = []
        for r in rows:
            n = norm_no(str(r.get("a100") or ""))
            core, year = CssnAdapter._split(n)
            if core == tcore and year is not None:
                cands.append((year, r))
        if not cands:
            return None, None
        # 同年份版优先（即该标准号那一版自身的状态）；无则取年代最大者参考
        same = [r for (y, r) in cands if y == tyear]
        if same:
            return same[0], "cross_prefix_same_year"
        _, best = max(cands, key=lambda x: x[0])
        return best, "cross_prefix_latest"

    # ---------------------------------------------------------- 解析
    @staticmethod
    def _state_of(a000: str | None) -> tuple[str | None, bool]:
        """cssn 状态串 → legal_status；未知非空串返回 (None, True) 表示需告警。"""
        text = (a000 or "").strip()
        if not text:
            return None, False
        mapped = CSSN_STATE_MAP.get(text)
        return mapped, mapped is None

    def _from_row(self, http: int, row: dict, standard_no: str,
                  mode: str) -> ChannelResult:
        a000 = str(row.get("a000") or "").strip()
        legal, unknown = self._state_of(a000)
        if unknown:
            upd_log(self.trace_id, f"channel.{self.name}", "WARN", "illegal_state_text",
                    standard_no=row.get("a100") or standard_no, state=a000)
        pub = str(row.get("a101") or "").strip() or None    # 发布日期
        impl = str(row.get("a205") or "").strip() or None   # 实施日期
        a100 = str(row.get("a100") or "").strip() or None
        version = a100 or None
        # 废止/被代替以自身发布/实施日期为关键日期（cssn 无废止日期列）
        # §11.0 R6c-3f（复核 b36 的 A-观察）：实施槽只放实施日期；发布日期有自己的槽
        eff = impl
        return ChannelResult(
            channel=self.name, found=True,
            change_type=derive_change_type(standard_no, version, legal),
            legal_status=legal, latest_version=version,
            effective_date=eff,
            published_date=pub,   # §11.0 R6c-3e：a101 发布日期单独落槽（以前只在 raw 里）
            evidence_url=(self.INDEX + "/list?keyword=" + urllib.parse.quote(standard_no)),
            raw={"http": http, "mode": mode, "status_text": a000,
                 "row": row,    # cssn 完整原始行（a000/a100/a101/a205/a825/a825name/a826/a826name/a104/formats/... 全保留）
                 "id": row.get("yf001"), "ccs_code": row.get("a825"), "ccs": row.get("a825name"),
                 "ics": row.get("a826name"),
                 "issue_date": pub, "impl_date": impl},   # 发布/实施日期（a101/a205）
        )
