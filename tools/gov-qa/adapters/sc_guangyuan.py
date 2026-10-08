"""适配器：**广元市·市长信箱·信件公开（Spring Boot + layui table JSON）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe42.txt 及本轮追加）
 · ★ 广元主站 `www.cngy.gov.cn` 被**瑞数 WAF** 拦（https=412 / http=405，页面 title「加载中」）。
   **突破口：市长信箱跑在另一个端口 `qgj.cngy.gov.cn:9050`，不设 WAF。**
     入口 `http://qgj.cngy.gov.cn:9050/ldxx/szxx/index`（信件公开列表在 `/ldxx/szxx/s/public`）。
 · 列表 API（layui table，POST + CSRF）：
     `POST http://qgj.cngy.gov.cn:9050/ldxx/szxx/publish/data`
       headers: `X-XSRF-TOKEN: <token>`（token 内嵌在 `/ldxx/szxx/s/public` 页面里，
                                          与首次 GET 下发的 `XSRF-TOKEN` Cookie 一致）
       data: `{page: N, limit: 10}`
     → `{"code":0,"count":438,"msg":"success","data":[{"id","xfjbm"(信访编码),
         "tsbt"(标题),"gksj"(公开时间),"xfrq"(写信时间),"tsnr","hfnr",…}]}`
 · 详情（**服务端渲染 HTML**）：`GET /ldxx/szxx/publish/<id>`
     · 信件基本信息表：`<td>标题</td><td colspan=3>标题</td>`
                       `<td>写信时间</td><td>2026-09-10</td><td>公开时间</td><td>2026-10-08</td>`
     · 问题 = `<td colspan="4" class="detail-text"><pre …>来信正文</pre></td>`
     · 答复 = 「信件的处理结果」卡片 → `<td class="detail-text">答复正文</td>`
       （个别信件答复以 .docx 附件形式给出，此时该单元格就是附件名）
 · 样例：id `7fe4bcc2…`「建议新建过街人行天桥」→ 多部门现场踏勘答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-guangyuan",
    "name": "广元市·市长信箱·信件公开",
    "kind": "api",
    "level": "city",
    "entry": "http://qgj.cngy.gov.cn:9050/ldxx/szxx/index",
    "status": "ok",
    "note": "★ 主站 www.cngy.gov.cn 被瑞数拦；市长信箱在 qgj.cngy.gov.cn:9050。列表 POST /ldxx/szxx/publish/data（X-XSRF-TOKEN，count=438）+ 详情 GET /ldxx/szxx/publish/<id>",
}

BASE = "http://qgj.cngy.gov.cn:9050"
PUBLIC_URL = BASE + "/ldxx/szxx/s/public"
DATA_URL = BASE + "/ldxx/szxx/publish/data"
VIEW_TPL = BASE + "/ldxx/szxx/publish/{id}"
PAUSE = 1.0
PAGE_SIZE = 10

_TAG = re.compile(r"<[^>]+>")
_TOKEN_RE = re.compile(r"X-XSRF-TOKEN':\s*'([^']+)'")
_TITLE_RE = re.compile(r"<td>\s*标题\s*</td>\s*<td[^>]*>(.*?)</td>", re.S)
_ASKED_RE = re.compile(r"<td>\s*写信时间\s*</td>\s*<td[^>]*>(.*?)</td>", re.S)
_PUB_RE = re.compile(r"<td>\s*公开时间\s*</td>\s*<td[^>]*>(.*?)</td>", re.S)
_Q_RE = re.compile(r'<td colspan="4" class="detail-text">\s*<pre[^>]*>(.*?)</pre>', re.S)
_A_RE = re.compile(r"信件的处理结果.*?<td[^>]*class=\"detail-text\"[^>]*>(.*?)</td>", re.S)


def _clean(s) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", str(s))
    s = re.sub(r"(?i)</p>", "\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    s = s.replace("\u2002", " ").replace("\u2003", " ").replace("\u00a0", " ")
    return re.sub(r"[ \t]+\n", "\n", s).strip()


def _decode(r) -> str:
    try:
        return r.content.decode("utf-8")
    except Exception:                                                       # noqa: BLE001
        return r.text


def _token(fetch) -> str:
    """取 CSRF token（内嵌在 /ldxx/szxx/s/public 页面；同时下发 XSRF-TOKEN Cookie）。"""
    try:
        r = fetch(PUBLIC_URL, headers={"Referer": SITE["entry"]})
    except Exception as e:                                                  # noqa: BLE001
        print(f"    [{SITE['key']}] 取 token 异常：{type(e).__name__}")
        return ""
    m = _TOKEN_RE.search(_decode(r))
    return m.group(1) if m else ""


def harvest(fetch, *, limit: int | None = None, max_pages: int = 200) -> list[dict]:
    """翻页取列表（layui POST）→ 逐条详情（服务端渲染 HTML）解析问答。"""
    out: list[dict] = []
    seen: set[str] = set()
    tok = _token(fetch)
    if not tok:
        print(f"    [{SITE['key']}] 未取到 X-XSRF-TOKEN（停）")
        return out
    total_pages = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            return out
        if total_pages is not None and page > total_pages:
            break
        try:
            r = fetch.post(DATA_URL, data={"page": page, "limit": PAGE_SIZE},
                           headers={"X-XSRF-TOKEN": tok, "Referer": PUBLIC_URL})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页：{type(e).__name__}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {page} 页 HTTP {getattr(r, 'status_code', '?')}（停）")
            break
        try:
            j = r.json()
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页非 JSON：{type(e).__name__}（停）")
            break
        rows = j.get("data") or []
        if total_pages is None:
            cnt = int(j.get("count") or 0)
            total_pages = (cnt + PAGE_SIZE - 1) // PAGE_SIZE or None
            print(f"    [{SITE['key']}] 共 {cnt} 条 / {total_pages} 页")
        if not rows:
            break
        new = 0
        for it in rows:
            if limit and len(out) >= limit:
                return out
            sid = str(it.get("id"))
            if sid in seen:
                continue
            seen.add(sid)
            new += 1
            try:
                vr = fetch(VIEW_TPL.format(id=sid), headers={"Referer": PUBLIC_URL})
                vh = _decode(vr)
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid[:8]}：{type(e).__name__}（跳过）")
                continue
            mq = _Q_RE.search(vh)
            ma = _A_RE.search(vh)
            question = _clean(mq.group(1)) if mq else ""
            answer = _clean(ma.group(1)) if ma else ""
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = _clean(_TITLE_RE.search(vh).group(1)) if _TITLE_RE.search(vh) else _clean(it.get("tsbt"))
            if title and question and not question.startswith(title):
                question = f"{title}\n{question}"
            elif not question:
                question = title
            asked = _clean(_ASKED_RE.search(vh).group(1)) if _ASKED_RE.search(vh) else ""
            pub = _clean(_PUB_RE.search(vh).group(1)) if _PUB_RE.search(vh) else ""
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": VIEW_TPL.format(id=sid),
                "question": question,
                "answer": answer,
                "asked_at": (asked or _clean(it.get("xfrq")) or None),
                "answered_at": (pub or _clean(it.get("gksj")) or None),
                "dept": None,
                "channel": "市长信箱·信件公开",
                "extra": {
                    "title": title,
                    "serial": it.get("xfjbm"),
                    "published_at": pub,
                    "platform": "广元 市长信箱（qgj.cngy.gov.cn:9050，layui table + 服务端渲染详情）",
                },
            })
            time.sleep(PAUSE)
        if new == 0:
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
