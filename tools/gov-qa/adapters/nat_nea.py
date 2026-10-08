"""适配器：**国家能源局·留言选登**（新华「Xhwpage」伪数据源 + 服务端渲染明细页）。

## 站点事实（2026-10-09 实测，证据 recon/nat-nea-*）
 · 入口 `https://www.nea.gov.cn/hudong/liuyan.htm`（互动 → 留言选登）。
 · 列表页是空壳，数据由新华 `Xhwpage` 组件从**伪数据源 JSON** 拉取（免登录）：
   `GET http://www.nea.gov.cn/hudong/ds_24f63667cf564f6ba14c152e90a7ca10.json`
   → `{"categoryDisplayName":"留言选登","datasource":[{title, publishUrl, publishTime, …}]}`
   ⚠ 数据源 id `24f63667…` 是从 liuyan.htm 里 `data="datasource:<id>"` 读出来的；换栏目要换 id。
   ⚠ 一次返回全部（实测 **145 条**），无需翻页。
 · 明细（**服务端渲染 HTML**，问答原文在此）：
   `GET http://www.nea.gov.cn/<publishUrl 去掉 ../>`（publishUrl 形如 `../20260930/<hash>/c.html`）
   页内 `<span id="detailContent">` 段：`咨询时间：` + 提问正文 + `答复时间：` + `<单位>答复：` + 答复正文。
 · 实测答复点名《文件》（例：《危险性较大的分部分项工程安全管理规定》住建部 37 号令）⇒ 优质考卷料。
"""
from __future__ import annotations

import re
import time
from urllib.parse import urljoin

SITE = {
    "key": "nat-nea",
    "name": "国家能源局·留言选登",
    "kind": "api",
    "level": "national",
    "entry": "https://www.nea.gov.cn/hudong/liuyan.htm",
    "status": "ok",
    "note": "新华 Xhwpage 伪数据源 ds_24f63667….json（145 条）+ 明细页 detailContent",
}

BASE = "http://www.nea.gov.cn"
LIST_PAGE = "http://www.nea.gov.cn/hudong/liuyan.htm"
DS_JSON = "http://www.nea.gov.cn/hudong/ds_24f63667cf564f6ba14c152e90a7ca10.json"
PAUSE = 1.2

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", re.S | re.I)
DETAIL_RE = re.compile(r'<span[^>]*id="detailContent"[^>]*>(.*?)</span>', re.S | re.I)
ASK_T_RE = re.compile(r"咨询时间[:：]\s*</strong>\s*([\d.]+)", re.I)
ANS_T_RE = re.compile(r"答复时间[:：]\s*</strong>\s*([\d.]+)", re.I)
DEPT_RE = re.compile(r"([^<>]{1,20}?)答复[:：]\s*</p>", re.I)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)


def _text(html: str | None) -> str:
    if not html:
        return ""
    t = SCRIPT_RE.sub(" ", html)
    t = TAG_RE.sub(" ", t)
    t = t.replace("&nbsp;", " ").replace("&emsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", t).strip()


def _parse_detail(html: str) -> dict:
    m = DETAIL_RE.search(html)
    inner = m.group(1) if m else html
    # 用 <p> 切段，逐段判读
    segs = [_text(x) for x in re.split(r"</?p[^>]*>", inner, flags=re.I)]
    segs = [s for s in segs if s]
    q_parts: list[str] = []
    a_parts: list[str] = []
    asked = answered = None
    dept = None
    mode = "q"
    for s in segs:
        if "咨询时间" in s:
            mt = re.search(r"([\d.]{4,})", s)
            asked = mt.group(1) if mt else None
            mode = "q"
            continue
        if "答复时间" in s:
            mt = re.search(r"([\d.]{4,})", s)
            answered = mt.group(1) if mt else None
            continue
        # 答复标记可能**自成一段**（`安全司答复：`）也可能**与答复正文同段**
        # （`安全司答复：对于…`）⇒ 用 search 切分，别要求整段以「答复：」结尾（踩过）。
        ma = re.search(r"^(.{0,20}?)答复[:：]\s*(.*)$", s)
        if ma:
            dept = ma.group(1).strip() or dept
            mode = "a"
            rest = ma.group(2).strip()
            if rest:
                a_parts.append(rest)
            continue
        if mode == "q":
            q_parts.append(s)
        else:
            a_parts.append(s)
    mt = TITLE_RE.search(html)
    return {
        "title": _text(mt.group(1)) if mt else "",
        "question": re.sub(r"^咨询问题[:：]?\s*", "", " ".join(q_parts).strip()),
        "answer": " ".join(a_parts).strip(),
        "asked_at": asked,
        "answered_at": answered,
        "dept": dept,
    }


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """取国家能源局留言选登（问题 + 答复原文）。"""
    r = fetch(DS_JSON, headers={"Referer": LIST_PAGE})
    if getattr(r, "status_code", 0) != 200:
        print(f"    [{SITE['key']}] 数据源 HTTP {getattr(r, 'status_code', '?')}（停）")
        return []
    try:
        items = r.json().get("datasource") or []
    except Exception as e:                                                  # noqa: BLE001
        print(f"    [{SITE['key']}] 数据源非 JSON（{type(e).__name__}，停）")
        return []
    print(f"    [{SITE['key']}] 数据源 {len(items)} 条")
    out: list[dict] = []
    for it in items:
        if limit and len(out) >= limit:
            break
        pu = it.get("publishUrl") or ""
        if not pu:
            continue
        url = urljoin(LIST_PAGE, pu)
        time.sleep(PAUSE)
        d = fetch(url, headers={"Referer": LIST_PAGE})
        if getattr(d, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 明细 {url[-40:]} HTTP {d.status_code}（跳过）")
            continue
        info = _parse_detail(d.text or "")
        if len(info["answer"] or "") < 10:
            print(f"    [{SITE['key']}] {url[-40:]} 未取到答复正文（跳过）")
            continue
        out.append({
            "source": SITE["key"],
            "id": str(it.get("contentId") or pu),
            "url": url,
            "question": info["question"] or _text(it.get("title")),
            "answer": info["answer"],
            "asked_at": info["asked_at"],
            "answered_at": info["answered_at"],
            "dept": info["dept"],
            "channel": "留言选登",
            "extra": {"title": _text(it.get("title")), "publish_time": it.get("publishTime"),
                      "platform": "nea-xhwpage"},
        })
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
