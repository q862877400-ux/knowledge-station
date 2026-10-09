"""适配器：**广西壮族自治区·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 新增。

## 为什么会有这个适配器
`adapters/gx_mailbox.py` 只接了 **siteId=3**（138 条），因为 2026-10-08 那次只从
门户 `api_mailbox.js` 里读到一个 `getMailboxList(3, 133, ...)`。
2026-10-09 用 `recon/igi-siteid-scan.py` 扫 siteId=1..300（空 appId）实测命中
**208 个 siteId / 34,938 条**（siteId=206 → 5184、156 → 2861、4 → 1742 …）。

## 关键事实
1. **`appId` 是过滤条件，不是站点标识**（与山西同理）：空 `appId` 才拿到该 siteId 全量。
2. **地域字段是真实的**：实测 `gx-mailbox`（siteId=3）138 条里有 **47 种**
   `PROVINCE/CITY/AREA` 组合（如「广西壮族自治区/南宁市/青秀区」「/桂林市/临桂县」）
   ⇒ **广西是继湖北/宁夏之后又一条能扩「县」的通道**，故**不剥离**地域（与山西不同）。
   ⚠ 旧信（约 1/3）地域为空，靠 `coverage-matrix.py` 的 `PROVINCE_PREFIX` 的 `gx-` 归省。
3. 须带 `Referer: http://www.gxzf.gov.cn/hdjl/mailbox/index.shtml`；http 可达（https 证书不匹配）。

## siteId=3 不在本适配器内
siteId=3 已由 `gx-mailbox` 落了 138 条（source=`gx-mailbox`）。这里再采会因 source 不同
而**产生重复 id** ⇒ 交给 `gx-mailbox` 自己续采。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "gx-igi",
    "name": "广西壮族自治区·政民互动信箱（IGI）",
    "kind": "api",
    "level": "province",
    "entry": "http://www.gxzf.gov.cn/hdjl/mailbox/index.shtml",
    "status": "ok",
    "note": "IGI 多 siteId（空 appId 取全量）；**带真实省/市/区三级归属**；须带 Referer；http 可达",
}

BASE = "http://www.gxzf.gov.cn/IGI"
REFERER = "http://www.gxzf.gov.cn/hdjl/mailbox/index.shtml"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 207 个 siteId（`recon/igi-siteid-guangxi.json`，2026-10-09 扫 1..300 空 appId），
#: 按 totalResults 降序，合计 **34,800** 条。**不含 siteId=3**（由 gx-mailbox 负责）。
#: 降序排列：长任务先跑大块（`igi-chunked.py` 逐 siteId 落盘，中断只损失当前一块）。
SITE_IDS = (
    "206 156 4 145 199 217 218 200 202 198 152 155 7 8 6 204 24 237 233 11 227 15 "
    "130 215 12 146 40 209 27 29 13 226 96 203 9 278 125 171 289 220 22 30 23 250 "
    "189 71 68 127 216 78 97 32 253 39 74 33 123 128 207 14 221 126 246 38 219 98 "
    "28 37 159 194 224 195 196 5 25 201 31 244 129 182 69 256 238 245 211 234 62 "
    "255 294 297 41 59 118 192 109 292 212 230 115 116 124 205 222 229 165 76 10 "
    "80 170 258 154 181 235 271 44 100 48 114 225 43 213 232 274 282 99 120 108 16 "
    "75 276 72 288 295 107 210 153 173 101 102 103 106 104 208 280 281 293 162 187 "
    "42 105 275 26 117 179 228 262 296 61 269 298 35 46 110 164 172 259 268 176 263 "
    "270 51 58 151 186 190 277 257 291 45 79 183 240 247 267 60 157 236 252 111 132 "
    "135 160 161 167 174 112 119 141 166 177 185 188 191 193 272 273 300"
).split()


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历广西各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。

    ⚠ 广西全量约 3.5 万条（枚举值）⇒ 用 `harvest.py` 一次跑完不现实；
    长任务请用分片增量驱动 `recon/igi-chunked.py`（逐 siteId 落盘）。
    """
    out: list[dict] = []
    seen = existing_ids(SITE["key"]) | existing_ids("gx-mailbox")
    if seen:
        print(f"    [{SITE['key']}] 已落盘 {len(seen)} 条，本轮跳过其明细")
    for sid in SITE_IDS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        sub_site["key"] = f"{SITE['key']}-{sid}"
        rows = harvest_igi(fetch, SITE=sub_site, base=BASE, site_id=sid, app_id=APP_ID,
                           group_id=GROUP_ID, referer=REFERER,
                           limit=(limit - len(out)) if limit else None,
                           max_pages=300, skip_ids=seen)
        out.extend(rows)
    return out
