"""适配器：**浙江省 · 民呼我为统一平台「办理公开」**（zxts.zjzwfw.gov.cn）。

## 形态判断（2026-10-08 实探，证据 recon/sh-zj-hunt.txt 【浙江】）
浙江省政府门户 `www.zj.gov.cn` 无互动栏目；互动统一收敛到
**浙江省民呼我为统一平台** `https://zxts.zjzwfw.gov.cn/zwmhww/`（Vue SPA，SiteName=「浙江省民呼我为统一平台」）。
各厅局站（如 `sthjt.zj.gov.cn`）的「我要咨询/领导信箱/办理公开」也全部指向它
（带 `areacode=330000`、`orgId=…`）。SPA 的接口藏在打包 JS 里。

## 接口（实测 200）
 · 列表（来件选登）：`POST {BASE}/zlh/zsapi/xfpt/OTMelbwjyz/OTMjkerj`
     body(JSON)：`{"code":"330000","bt":"","bldw":"","pageNum":<n>,"pageSize":<m>}`（pageSize 上限实测 100）
     → `data:{currentPage,pageSize,totalItem,list:[{bt(标题),djsj(登记时间),bldw(答复单位),
        blsj(答复时间),storeid,xfmd(诉求目的),xfjclzt(办理状态),...}]}`；实测 **totalItem=49218**。
 · 明细：`GET {BASE}/zlh/zsapi/xfpt/OTMelbwjyz/OTMrwgaxid?storeId=<storeid>`（⚠ 参数名 `storeId`，驼峰）
     → `data:{bt(标题),nr(问题正文),dfyj(答复意见=答复),dfdw(答复单位),fysj(反映时间),
        dfsj(答复时间),sjly(数据来源),storeid}`。

## ★ 字体反爬（关键坑）
列表/明细里的文字字段被包成 `#<fontId>otltag<混淆串>#FontTag`；浏览器加载
`{BASE}/zlh/zsapi/ttf/<fontId>.woff` 自定义字体把混淆字渲染回真字。
**破解**：该 woff 的 **glyph 名就是真字的 Unicode**（`uni6C42`→「求」、`uni6E29`→「温」；
ASCII 用单字母名），故 `cmap[混淆码位] → glyph 名 → 真字` 一一映射，无需 OCR。
每响应一个 fontId（不同响应映射不同，实测两两 0 重叠）⇒ **按 fontId 下字体、缓存、逐字段解码**。
（实测解码：`茙菞茥菜荆茛莵菛莛莈莙菙莇菋莂莐药莯？` → `温医附一院强制检测登革热并自费合理吗？`）
偶有响应返回明文（无 otltag），解码函数对明文原样返回。

## 依赖
字体解析用 `fontTools`（本仓 venv 已随 matplotlib 装入）。
"""
from __future__ import annotations

import io
import json
import re
import time
from pathlib import Path

SITE = {
    "key": "zj-mhww",
    "name": "浙江省·民呼我为统一平台·办理公开",
    "kind": "api",
    "level": "province",
    "entry": "https://zxts.zjzwfw.gov.cn/zwmhww/#/home/index/public",
    "status": "ok",
    "note": "POST OTMrwgaxid?… 列表 + GET ?storeId= 明细；文字 woff 字体混淆，按 glyph 名解码；"
            "totalItem=49218；**可反复跑**（开跑跳过已落盘 id，limit=本轮新增）",
}

BASE = "https://zxts.zjzwfw.gov.cn"
LIST_URL = BASE + "/zlh/zsapi/xfpt/OTMelbwjyz/OTMjkerj"
DETAIL_URL = BASE + "/zlh/zsapi/xfpt/OTMelbwjyz/OTMrwgaxid"
FONT_URL = BASE + "/zlh/zsapi/ttf/{}.woff"
AREA = "330000"
PAGE_SIZE = 100
PAUSE = 1.5
HEADERS = {
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": BASE + "/zwmhww/",
    "Origin": BASE,
}

_FONT_CACHE: dict[str, dict[str, str]] = {}
_FID_RE = re.compile(r"#([A-Za-z0-9_]+)otltag")
_TAG_RE = re.compile(r"#[A-Za-z0-9_]*?otltag")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _existing_ids() -> set[str]:
    """读本适配器**自己已落盘**的 `data/zj-mhww-*.jsonl`，取出已有 storeid。

    ⚠ 为什么适配器要读自己的产物：列表接口**只按页码翻**，没有「从某条之后续采」的游标。
    若每轮都从第 1 页跑，`harvest.py` 的按 id 去重会把新数据全挡掉 ⇒ **第二轮起恒 0 新增**，
    浙江就永远卡在首批那几百条。预载已有 id 后，已知条目的明细请求被跳过，
    配额全部花在真正的新数据上 ⇒ 反复跑即可逐轮推进（实测第 2 轮仍有新增）。
    """
    ids: set[str] = set()
    try:
        for p in DATA_DIR.glob(f"{SITE['key']}-*.jsonl"):
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    sid = str(json.loads(line).get("id") or "").strip()
                    if sid:
                        ids.add(sid)
    except Exception:                                                   # noqa: BLE001
        pass
    return ids


def _glyph_char(gn: str) -> str | None:
    """glyph 名 → 真字。用 fontTools 的 AGL 反查，覆盖 `uniXXXX`（汉字）、
    单字母（ASCII）、以及 `zero/one/…/nine`、`bracketleft` 等标准名（日期/编号用得到）。"""
    try:
        from fontTools.agl import toUnicode
        u = toUnicode(gn)
    except Exception:                                                   # noqa: BLE001
        u = ""
    if u:
        return u
    if gn.startswith("uni") and len(gn) >= 7:
        try:
            return chr(int(gn[3:7], 16))
        except ValueError:
            return None
    return gn if len(gn) == 1 else None


def _font_map(fetch, fid: str) -> dict[str, str]:
    if fid in _FONT_CACHE:
        return _FONT_CACHE[fid]
    from fontTools.ttLib import TTFont
    r = fetch(FONT_URL.format(fid), headers=HEADERS)
    mp: dict[str, str] = {}
    if getattr(r, "status_code", 0) == 200 and r.content:
        f = TTFont(io.BytesIO(r.content))
        for cp, gn in f.getBestCmap().items():
            real = _glyph_char(gn)
            if real:
                mp[chr(cp)] = real
    _FONT_CACHE[fid] = mp
    return mp


def _decode(fetch, txt: str | None) -> str:
    """解 `#<fid>otltag…<text>#FontTag`；无标记（明文）原样返回。"""
    if not txt:
        return ""
    m = _FID_RE.search(txt)
    if not m:
        return txt
    mp = _font_map(fetch, m.group(1))
    body = _TAG_RE.sub("", txt).replace("#FontTag", "")
    return "".join(mp.get(ch, ch) for ch in body)


def harvest(fetch, *, limit: int | None = None, max_records: int = 500,
            page_size: int = PAGE_SIZE) -> list[dict]:
    """翻页取「来件选登」，逐条取明细拿问题+答复（明细文字需按 woff 字体解码）。

    **可反复跑、逐轮推进**：开跑先读 `data/zj-mhww-*.jsonl` 已有 id 并跳过，
    所以 `limit` 指的是**本轮新增条数**，不是列表总位次。

    ⚠ 每条记录 = 1 次明细 + 偶发 1 次字体下载 ⇒ 全量 4.9 万条代价很大；
      `limit` 给了就按 `limit` 收，没给则用 `max_records`（默认 500）兜底。
    """
    out: list[dict] = []
    seen: set[str] = _existing_ids()
    known = len(seen)
    cap = limit if limit else max_records
    if known:
        print(f"    [{SITE['key']}] 已落盘 {known} 条，本轮跳过其明细，目标新增 {cap} 条")
    total = None
    page = 1
    while True:
        if len(out) >= cap:
            break
        try:
            r = fetch.post(LIST_URL, json={"code": AREA, "bt": "", "bldw": "",
                                           "pageNum": page, "pageSize": page_size},
                           headers=HEADERS)
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        data = (r.json() or {}).get("data") or {}
        rows = data.get("list") or []
        if total is None:
            total = data.get("totalItem")
            print(f"    [{SITE['key']}] 办理公开总数 totalItem={total}")
        if not rows:
            break
        fresh = 0
        for it in rows:
            if len(out) >= cap:
                break
            sid = str(it.get("storeid") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            time.sleep(PAUSE)
            try:
                dr = fetch(DETAIL_URL, params={"storeId": sid}, headers=HEADERS)
                dd = (dr.json() or {}).get("data") or {}
            except Exception as e:                                      # noqa: BLE001
                print(f"    [{SITE['key']}] 明细 {sid}：{type(e).__name__}（跳过）")
                continue
            question = _decode(fetch, dd.get("nr")) or _decode(fetch, dd.get("bt"))
            answer = _decode(fetch, dd.get("dfyj"))
            if len(answer) < 10 or len(question) < 4:
                continue
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": f"{SITE['entry'].split('#')[0]}#/home/index/search-detail?storeId={sid}",
                "question": question[:400],
                "answer": answer,
                "asked_at": _decode(fetch, dd.get("fysj")) or None,
                "answered_at": _decode(fetch, dd.get("dfsj")) or None,
                "dept": _decode(fetch, dd.get("dfdw")) or None,
                "channel": "民呼我为·办理公开",
                "extra": {
                    "title": _decode(fetch, dd.get("bt")),
                    "storeid": sid,
                    "xfmd": it.get("xfmd"),
                    "sjly": _decode(fetch, dd.get("sjly")),
                    "answer_kind": "办理答复（民呼我为办结件公示）",
                },
            })
            fresh += 1
        print(f"    [{SITE['key']}] 列表第 {page} 页：{len(rows)} 条，新增 {fresh}")
        if total and page * page_size >= int(total):
            break
        page += 1
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
