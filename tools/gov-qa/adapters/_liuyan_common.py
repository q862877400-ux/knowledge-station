"""人民网「领导留言板」（liuyan.people.com.cn）· 共用采集基座。

## 来源与出处（**必读**）
 · 这是**媒体平台**（人民网运营），不是政府官网；答复是各部委/地方办理单位的「办理答复」，
   与官网站方编辑的正式答复**权威形态不同**，下游使用时要区分标注。
 · 思路借鉴 [Fissify/Message-Board-for-Leaders](https://github.com/Fissify/Message-Board-for-Leaders)
   （其 README 自述数据归人民网所有、仅限学术非商业；本基座**未复制其代码**，
   只沿用它的字段口径：留言对象/标题/时间/内容/答复内容/答复时间）。
 · 其中央部委板块**不抓答复**；本基座把答复补上了（详情接口 `dataType==9` 条目）。
 · ⚠ 采集的语料用于内部评测/研究，对外使用时注明来源人民网领导留言板。

## 接口（2026-10-07 从 app.*.js 逆向 + 抓包双验证）
```
POST https://liuyan.people.com.cn/v1/threads/list/bw        # 部委版块流（bw=部委）
     body = {"appCode":"PC42ce3bfa4980a9","token":"","signature":"<md5>",
             "param":"{\\"showUnAnswer\\":0,\\"lastItem\\":\\"\\",\\"position\\":1,
                       \\"rows\\":20,\\"orderType\\":2}"}
POST https://liuyan.people.com.cn/v1/threads/content        # 详情（含答复）
     body = {...同上封套, "param":"{\\"tid\\":25595113}"}
```
**参数语义（实测，见 recon/liuyan-*.txt 证据）**：
 · `showUnAnswer` 是**过滤器**不是"包含"：`0` ⇒ 只回**已办理**（有答复）；`1` ⇒ 只回**待回复**。
 · `typeId` 是**留言分类**（求助/咨询…），不是回复状态 —— 不要传，传了会漏类别。
 · **不带 `fid`** = 全站部委流（行内自带 `forumName` 部委归属）。
   ⚠ 按 fid 过滤部委版块多数只有"提交入口"性质的待回复件
   （如生态环境部 fid=5062 全部 22 条皆待回复，环保类实际由地方办理）——
   **别按 fid 采，采全站流**。
 · 地方版块是同构的 `/v1/threads/list/df`（50/50 已办理实测可用）——后续扩地方从这里走。
 · 翻页：拿响应 `lastItem` 作光标传回，`position` 递增；`hasData` 为 0/空即停。

**签名算法**（两组真实抓包样本逐字节验证一致）：
```
secret16   = md5(appCode)[:16]                       # 未登录时 token 为空 ⇒ secret 就是它
signature  = md5(路径 + paramJSON + secret16)         # 路径带前导斜杠、不含查询串
```
未登录（token=""）即可读列表与详情；登录 token 属用户隐私，本基座**不取不存**。

## 响应结构（实测）
 · 列表 `resultData.data[]`：`tid / forumName(留言对象=部委+领导) / subject(标题) /
   content(留言全文) / typeName(分类) / stateInfo(已办理…) / createDateline(unix)`。
 · 详情 `resultData.contentList[]`：`[0]` = 留言本体（含 `cUrl` 公开链接），
   `dataType==9` 的条目 = **官方答复**（`content` + `dateline`）；`dataType==4` 是办理说明/追评，
   不当答复用。

## 礼貌抓取
详情接口对 UA 有要求（过短的 UA 会拿到非 JSON），且每请求间隔 ≥1.5s；单线程。
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime

BASE = "https://liuyan.people.com.cn"
APPCODE = "PC42ce3bfa4980a9"          # 页面内联 SITE_CONFIG 公开常量，非凭据
SECRET16 = hashlib.md5(APPCODE.encode()).hexdigest()[:16]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
PAUSE = 2.5                     # 403 限流实测在案（SITE-REGISTRY 未决问题①）：≥2.5s
LIST_ROWS = 20

TAG_RE = re.compile(r"<[^>]+>")

#: 统一字段之外的原始键进 extra（挑长期有价值的；全量原始行在接口里可重取）
#: pForumNames = 行政层级归属（如 ["河北省","衡水市"]）—— 地方版块省市县归属全靠它
EXTRA_KEYS = ("typeName", "domainName", "domainId", "fid", "forumPathName",
              "pForumNames", "pforumNames")


def _md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def _envelope(path: str, param_obj: dict) -> str:
    """按逆向出的算法构造请求封套（返回 JSON 字符串）。"""
    p = json.dumps(param_obj, separators=(",", ":"), ensure_ascii=False)
    body = {"appCode": APPCODE, "token": "",
            "signature": _md5(path + p + SECRET16), "param": p}
    return json.dumps(body, ensure_ascii=False)


def _headers(referer: str) -> dict:
    return {"User-Agent": UA, "Content-Type": "application/json",
            "Origin": BASE, "Referer": referer}


def _clean(text: str) -> str:
    """留言/答复正文以纯文本为主；万一含 HTML 标签，去标签保文字（不摘要）。"""
    t = text or ""
    if "<" in t and ">" in t:
        t = TAG_RE.sub(" ", t)
    return re.sub(r"[ \t]+", " ", t).strip()


def _ts(unix) -> str | None:
    if not unix:
        return None
    return datetime.fromtimestamp(int(unix)).strftime("%Y-%m-%d %H:%M:%S")


def harvest_liuyan(fetch, *, SITE: dict, stream: str = "bw",
                   limit: int | None = None, pause: float = PAUSE,
                   rows_per_page: int = LIST_ROWS) -> list[dict]:
    """抓部委版块（`stream="bw"`）的**已办理**留言 + 官方答复。

    ⚠ `fetch` 是 harvest.py 注入的 `_Fetcher`：本站接口是 POST，
    用 `fetch.post(url, content=…, headers=…)`。
    只收详情里确有 `dataType==9` 答复的条目（列表状态只是初筛）。
    """
    out: list[dict] = []
    list_path = f"/v1/threads/list/{stream}"
    last_item, position, fetched, scanned = "", 1, 0, 0
    while True:
        param = {"showUnAnswer": 0, "lastItem": last_item, "position": position,
                 "rows": rows_per_page, "orderType": 2}
        r = fetch.post(BASE + list_path, content=_envelope(list_path, param),
                       headers=_headers(f"{BASE}/index"))
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {position} 批 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            j = r.json()
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表非 JSON（{type(e).__name__}，停）")
            break
        rd = (j.get("resultData") or {}) if isinstance(j, dict) else {}
        items = rd.get("data") or []
        if not items:
            break
        for it in items:
            scanned += 1
            if (it.get("stateInfo") or "") not in ("已办理", "办理中"):
                continue                         # 待回复的没有 gold（初筛，详情再验）
            tid = it.get("tid")
            time.sleep(pause)
            dpath = "/v1/threads/content"
            dr = fetch.post(BASE + dpath, content=_envelope(dpath, {"tid": tid}),
                            headers=_headers(f"{BASE}/threads/content?tid={tid}"))
            if getattr(dr, "status_code", 0) != 200:
                continue
            try:
                dj = dr.json()
            except Exception:                                               # noqa: BLE001
                continue
            cl = ((dj.get("resultData") or {}).get("contentList")) or []
            head = cl[0] if cl else {}
            replies = [x for x in cl[1:] if x.get("dataType") == 9]
            if not replies:
                continue                         # 详情里也没有答复 ⇒ 不收
            answer = "\n".join(_clean(x.get("content") or "")
                               for x in replies).strip()
            if not answer:
                continue
            subject = _clean(it.get("subject") or "")
            body = _clean(it.get("content") or "")
            question = subject if not body else f"{subject}\n{body}"
            out.append({
                "source": SITE["key"],
                "id": str(tid),
                "url": head.get("cUrl") or f"{BASE}/threads/content?tid={tid}",
                "question": question,
                "answer": answer,
                "asked_at": _ts(it.get("createDateline")),
                "answered_at": _ts(replies[0].get("dateline")),
                "dept": _clean(head.get("forumName") or it.get("forumName") or ""),
                "channel": it.get("typeName"),
                "extra": {k: it.get(k) for k in EXTRA_KEYS
                          if it.get(k) is not None},
            })
            fetched += 1
            if limit and fetched >= limit:
                return out
        last_item = rd.get("lastItem") or ""
        if not last_item or rd.get("hasData") in (0, None):
            break
        position += 1
        time.sleep(pause)
    print(f"    [{SITE['key']}] 流 {stream}：扫过 {scanned} 条，"
          f"收 {fetched} 条带官方答复")
    return out
