"""适配器：**应急管理部**「互动答复」列表（静态列表页）。

## 站点事实（2026-10-07 实测）
 · 列表页是**静态 HTML**，翻页靠 `index_N.shtml`：
   `https://www.mem.gov.cn/hd/gzly/hdhdly/`、`index_1.shtml`、`index_2.shtml`……
 · 明细页路径形态固定：`../lyhf/YYMMDD/tYYYYMMDD_NNNNN.shtml`
 · 明细页里**提问与答复在同一页**，本适配器用「正文整段」当答复，
   提问取 `<title>`/首个小标题。

## 已知边界
 · 这是**静态爬**：页数一多就慢。**若能找到它的列表接口，优先换成接口**（见 SITE-REGISTRY.md）。
 · 该站**没发现 WAS5 接口**（试过 `/was5/web/search`，返回 711 字节空页；但那是因为没带 channelid，
   **不能据此判定它没有**——见 README 的"一条作废的测试"）。
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

# ⚠ 本机控制台是 GBK，日志里的 emoji/箭头（⚠ ⇒ 等）用裸 `print` 会
#   `UnicodeEncodeError` **把整个采集带崩**（实测 2026-10-10）⇒ 走 `safe_print`。
try:
    from common import safe_print
except ImportError:                                          # 适配器被单独 import 时
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
    from common import safe_print


SITE = {
    "key": "mem",
    "name": "应急管理部",
    "kind": "static",
    "level": "national",
    "entry": "https://www.mem.gov.cn/hd/gzly/hdhdly/",
    "status": "ok",
    "note": "静态列表页 index_N.shtml；明细页 ../lyhf/YYMMDD/t*.shtml",
}

LIST_URLS = [
    "https://www.mem.gov.cn/hd/gzly/hdhdly/",
] + [f"https://www.mem.gov.cn/hd/gzly/hdhdly/index_{i}.shtml" for i in range(1, 10)]
#: ⚠ **实测：4 个列表页只覆盖 24 条；完整列表约 10 页（早前试采 10 页得 66 条）**。
#: 上面默认取到 `index_9`（10 页）。页数不够就往上加 —— 该站的翻页是**纯静态**，
#: 没有"总页数"接口可查，只能试着取；取到空页自然停（下面会把 0 条的页跳过）。
BASE = "https://www.mem.gov.cn/hd/gzly/hdhdly/"

#: 明细页链接（相对路径）
ENTRY_RE = re.compile(r"\.\./lyhf/\d{6}/t\d{8}_\d+\.shtml")
#: 明细页正文里的分隔标记（2026-10-07 实测定稿，见 recon/mem-detail-sample.html）
#: 页面结构：… 咨询: <问题> 咨询时间: <日期> 回复: <答复> 回复单位: <单位> 回复时间: <日期> …
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", re.S | re.I)
ASK_RE = re.compile(r"咨询[:：]\s*(.*?)\s*咨询时间", re.S)
ANS_RE = re.compile(r"回复[:：]\s*(.*?)\s*回复单位", re.S)
DEPT_RE = re.compile(r"回复单位[:：]\s*(.*?)\s*回复时间", re.S)
AT_RE = re.compile(r"咨询时间[:：]\s*([\d\-./年月日]+)")
RT_RE = re.compile(r"回复时间[:：]\s*([\d\-./年月日]+)")


def _text(html: str) -> str:
    """去脚本/样式/注释后再去标签 —— 不复用旧版整页兜底（那会把 JS 当答复，已踩坑）。"""
    t = SCRIPT_RE.sub(" ", html or "")
    t = TAG_RE.sub(" ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", t).strip()


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一格式返回该站问答。`fetch(url)` 返回带 `.text` 的响应对象。"""
    seen: set[str] = set()
    urls: list[str] = []
    for u in LIST_URLS:
        r = fetch(u)
        if getattr(r, "status_code", 0) != 200:
            safe_print(f"    [{SITE['key']}] 列表 {u} -> HTTP {getattr(r, 'status_code', '?')}（跳过）")
            continue
        for rel in ENTRY_RE.findall(r.text):
            full = urljoin(BASE, rel)
            if full not in seen:
                seen.add(full)
                urls.append(full)
    print(f"    [{SITE['key']}] 列表里共 {len(urls)} 条明细")
    if limit:
        urls = urls[:limit]

    out: list[dict] = []
    for i, u in enumerate(urls, 1):
        try:
            r = fetch(u)
            if getattr(r, "status_code", 0) != 200:
                continue
            html = r.text
            body = _text(html)
            m = TITLE_RE.search(html)
            title = _text(m.group(1)) if m else ""
            # 按页内分隔标记抽「咨询/回复」（2026-10-07 定稿；旧版整页兜底会抓进 JS）
            ma = ASK_RE.search(body)
            mr = ANS_RE.search(body)
            question = _text(ma.group(1)) if ma else ""
            answer = _text(mr.group(1)) if mr else ""
            if not answer:
                # 抽不到答复的（页面结构变了）**不收**，别把页面壳当答复
                print(f"    [{SITE['key']}] {i} 未抽到「回复:」段，跳过 {u[-40:]}")
                continue
            md = DEPT_RE.search(body)
            mt = RT_RE.search(body)
            mt_ask = AT_RE.search(body)
            out.append({
                "source": SITE["key"],
                "id": u.rsplit("/", 1)[-1] or u,
                "url": u,
                "question": question or title,
                "answer": answer,
                "asked_at": mt_ask.group(1) if mt_ask else None,
                "answered_at": mt.group(1) if mt else None,
                "dept": _text(md.group(1)) if md else None,
                "channel": "互动答复",
                "extra": {"path": u, "title": title},
            })
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] {i} {u} 失败：{type(e).__name__}")
        if i % 10 == 0:
            print(f"    [{SITE['key']}] …{i}/{len(urls)}")
    return out
