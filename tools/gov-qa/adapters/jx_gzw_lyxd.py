"""适配器：**江西省国资委 · 留言选登**（数融站群 webSiteCode=jxsgzw, channelCode=lyxd）。

## 怎么找到的（2026-10-09 实测，证据 recon/jx-dept-probe.json + jx-dept-sample.txt）
江西省级部门站是**数融站群 CMS**（与 `jx-zf` 同一套引擎）。`recon/jx-config.js` 的
`aggregationWebsiteCod` 列了 35 个省直部门站点代号 ⇒ 拿 24 个通用栏目代号逐个试
`POST /queryList`，**35 个站里只有 16 个有 total>0**，且其中绝大多数**不是问答**：

| 栏目 | 实为 | 判定 |
|---|---|---|
| `hydt`（省自然资源厅 631 / 省卫健委 394）| 政策解读/新闻稿 | ✗ 不是问答 |
| `yjzj`（省农业农村厅 106 / 省人社厅 59）| 规范性文件「征求意见」公告 | ✗ 不是问答 |
| `zxft`（省公安厅 46 / 省住建厅 44 / 省市监局 43）| 访谈/新闻发布会实录（**记者**提问+官方回答）| ✗ 非公众问答 |
| `sjxx`（省审计厅 20）| 审计工作报告 | ✗ 不是问答 |
| `hdjl`/`ldxx`（省财政厅/省工信厅，各 1）| 来信来访联系方式 / 领导简历 | ✗ 不是问答 |
| **`lyxd`（省国资委 15）** | **留言选登（真公众问答）** | ✓ **本适配器** |

⚠ 结论：**「数融站群 × 部门站」这条线只有 1 个站可采**。省直部门大多把公众问答
收在自己的**信箱系统**（`/api/mail/list`，需各站自己的 `userIdObj`）而非 `queryList`；
本次未打通，见 recon 里的负面结论。

## 正文形态（`_text()` 后）
```
姓名： 马 *  提问时间： 2026年9月29日  标题： 咨询国资国企在线监管系统建设情况
内容： 尊敬的领导您好，……  答复部门： 江西省国资委  答复时间： 2026年10月9日
回复： 您好，……
```
⇒ 按**标签**切分（标签固定：姓名/提问时间/标题/内容/答复部门/答复时间/回复）。
"""
from __future__ import annotations

import html
import json
import re
import time

SITE = {
    "key": "jx-gzw-lyxd",
    "name": "江西省国资委·留言选登",
    "kind": "api",
    "level": "province",
    "entry": "http://gzw.jiangxi.gov.cn/",
    "status": "ok",
    "note": "数融站群 queryList（webSiteCode=jxsgzw, channelCode=lyxd）；35 部门站中唯一真问答栏目",
}

HOST = "https://www.jiangxi.gov.cn"
LIST_URL = HOST + "/queryList"
WEB_SITE = "jxsgzw"
CHANNEL = "lyxd"
PAGE_SIZE = 20
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")
#: 日期里混着 HTML 留下的空格（「202 6 年 9 月 29 日」）⇒ 归一化
DATE_NORM = re.compile(r"\s*([年月日])\s*")


def _text(h: str | None) -> str:
    # 先去标签、再还原实体（顺序见 jx_zf._text 的说明）
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", h or ""))).strip()


def _date(s: str | None) -> str | None:
    if not s:
        return None
    s = DATE_NORM.sub(r"\1", re.sub(r"(?<=\d)\s+(?=\d)", "", s.strip()))
    return s or None


def _grab(pat: str, text: str) -> str | None:
    m = re.search(pat, text, re.S)
    return m.group(1).strip() if m else None


def _one(source: dict) -> dict | None:
    c = source.get("content")
    body = _text(c.get("content") if isinstance(c, dict) else c)
    if not body:
        return None
    title = _grab(r"标题\s*[：:]\s*(.*?)\s*内容\s*[：:]", body) or _text(source.get("title"))
    question = _grab(r"内容\s*[：:]\s*(.*?)\s*答复部门\s*[：:]", body)
    dept = _grab(r"答复部门\s*[：:]\s*(.*?)\s*答复时间\s*[：:]", body)
    answered = _grab(r"答复时间\s*[：:]\s*(.*?)\s*回复\s*[：:]", body)
    answer = _grab(r"回复\s*[：:]\s*(.*)$", body)
    asked = _grab(r"提问时间\s*[：:]\s*(.*?)\s*标题\s*[：:]", body)
    if not answer:
        return None
    if not question:
        question = title
    if not question or len(question) < 4 or len(answer) < 10:
        return None
    urls = source.get("urls")
    try:
        url = (json.loads(urls) or {}).get("pc") if urls else None
    except Exception:                                                   # noqa: BLE001
        url = None
    if url and url.startswith("/"):
        url = HOST + url
    return {
        "source": SITE["key"],
        "id": str(source.get("id")),
        "url": url or SITE["entry"],
        "question": question[:400],
        "answer": answer,
        "asked_at": _date(asked) or source.get("pubDate"),
        "answered_at": _date(answered),
        "dept": dept,
        "channel": "留言选登",
        "extra": {
            "title": title,
            "channel_code": source.get("channelCode"),
            "website_code": source.get("websiteCode"),
            "answer_kind": "办理答复（留言选登，带姓名脱敏/提问时间/答复部门/答复时间）",
        },
    }


def harvest(fetch, *, limit: int | None = None, max_pages: int = 20) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            return out[:limit]
        data = {"current": page, "pageSize": PAGE_SIZE,
                "channelCode": [CHANNEL], "webSiteCode": [WEB_SITE]}
        r = fetch.post(LIST_URL, data=data)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            res = (r.json().get("data") or {}).get("results") or []
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        if not res:
            break
        fresh = 0
        for it in res:
            src = it.get("source") or {}
            sid = str(src.get("id"))
            if sid in seen:
                continue
            seen.add(sid)
            rec = _one(src)
            if rec:
                out.append(rec)
                fresh += 1
            if limit and len(out) >= limit:
                return out[:limit]
        print(f"    [{SITE['key']}] 第 {page} 页：{len(res)} 条，新增 {fresh}")
        if len(res) < PAGE_SIZE:
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
