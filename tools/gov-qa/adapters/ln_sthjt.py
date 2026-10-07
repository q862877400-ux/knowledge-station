"""适配器：**辽宁省生态环境厅 · 历史咨询服务**（问答内联在列表页）。

## 站点形态（2026-10-07 实探，证据 recon/ln-lsxfw-notes.txt / ln-lsxfw-raw.html）
 · 列表页 `https://sthj.ln.gov.cn/sthj/zmhd/zxly/lszxfw/index.shtml`，
   **问答直接内联**（无明细页）：每个条目是一个 `<div class="hf_search_box">` 块：
   ```
   box1: 标题： / 发表时间：YYYY-MM-DD / <div class="right">标题文本</div>
         内容： / <div class="right">问题正文</div>
   box2: 回复： / <div class="right">答复正文</div>
   ```
 · 翻页为 JS：`queryClick('/eportal/ui?currentPage=N&moduleId=f3e565ad2f1648218bac992faf7ac04e&pageId=c441c2c3cafe47478cffbb9828914f88')`
   —— 直接 GET 该 URL 即可取到第 N 页（共 3 页，实测）。
"""
from __future__ import annotations

import re
import time

SITE = {
    "key": "ln-st",
    "name": "辽宁省生态环境厅·历史咨询服务",
    "kind": "static",
    "level": "province",
    "entry": "https://sthj.ln.gov.cn/sthj/zmhd/zxly/lszxfw/index.shtml",
    "status": "ok",
    "note": "问答内联列表（无明细页）；翻页走 /eportal/ui?currentPage=N&moduleId=…&pageId=…",
}

BASE = "https://sthj.ln.gov.cn"
LIST_URL = BASE + "/sthj/zmhd/zxly/lszxfw/index.shtml"
PAGE_URL = (BASE + "/eportal/ui?currentPage={n}"
            "&moduleId=f3e565ad2f1648218bac992faf7ac04e"
            "&pageId=c441c2c3cafe47478cffbb9828914f88")
PAUSE = 1.2

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
BLOCK_RE = re.compile(r'<div class="hf_search_box">(.*?)(?=<div class="hf_search_box">|</form>|$)',
                      re.S)
TITLE_RE = re.compile(r'<div class="left">标题：</div>.*?<div class="right">(.*?)</div>', re.S)
DATE_RE = re.compile(r'<span>发表时间：</span>\s*([0-9]{4}-[0-9]{2}-[0-9]{2})')
Q_RE = re.compile(r'<div class="left">内容：</div>\s*<div class="right">(.*?)</div>', re.S)
A_RE = re.compile(r'<div class="left">回复：</div>\s*<div class="right">(.*?)</div>', re.S)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _parse_page(html: str) -> list[dict]:
    out = []
    for blk in BLOCK_RE.findall(html):
        q = Q_RE.search(blk)
        a = A_RE.search(blk)
        if not q or not a:
            continue
        question = _text(q.group(1))
        answer = _text(a.group(1))
        if len(question) < 4 or len(answer) < 10:
            continue
        tm = TITLE_RE.search(blk)
        dm = DATE_RE.search(blk)
        out.append({"title": _text(tm.group(1)) if tm else "",
                    "question": question, "answer": answer,
                    "asked_at": dm.group(1) if dm else None})
    return out


def harvest(fetch, *, limit: int | None = None, max_pages: int = 10) -> list[dict]:
    """逐页取（首页用静态地址，其余页用 eportal 分页地址），按 标题+问题 去重。"""
    out: list[dict] = []
    seen: set[str] = set()
    for n in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        url = LIST_URL if n == 1 else PAGE_URL.format(n=n)
        r = fetch(url)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {n} 页 HTTP {getattr(r, 'status_code', '?')}（停）")
            break
        items = _parse_page(r.text or "")
        fresh = [it for it in items if (it["title"], it["question"]) not in seen]
        print(f"    [{SITE['key']}] 第 {n} 页：条目 {len(items)}，新增 {len(fresh)}")
        if not fresh:
            break
        for it in fresh:
            seen.add((it["title"], it["question"]))
            uid = str(abs(hash((it["title"], it["question"]))) % (10 ** 12))
            out.append({
                "source": SITE["key"],
                "id": uid,
                "url": url,
                "question": it["question"],
                "answer": it["answer"],
                "asked_at": it["asked_at"],
                "answered_at": None,
                "dept": "辽宁省生态环境厅",
                "channel": "政民互动·历史咨询服务",
                "extra": {"title": it["title"], "page": n,
                          "answer_kind": "办理答复（咨询服务，多为指引性）"},
            })
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
