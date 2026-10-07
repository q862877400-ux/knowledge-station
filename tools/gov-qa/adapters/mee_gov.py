"""适配器：**生态环境部**「常见问题 / 留言选登」（WAS5 检索接口）。

## ★ 这是目前最省事的一个站 —— 直接拿 JSON，一次 100 条
接口不在页面里，是**从页面内联 JS 挖出来的**（`.ajaxCjwtList` 那段）：
```
GET https://www.mee.gov.cn/was5/web/search
     ?channelid=232534&orderby=-DOCRELTIME&keyword=&page=1&perpage=100
```
响应（**结构化 JSON，不需要解析 HTML**）：
```json
{"code":0,"recordCount":158,"pageSize":100,"currentPage":1,
 "items":[{"hfdw":"办公厅","doctitle":"…提问…","doccontent":"…答复…",
           "lxrq":"2025.10.24 08:05:00","hfrq":"2025.10.27 11:04:00",
           "docpuburl":"http://www.mee.gov.cn/hdjl/lyxd/202601/t20260116_1140853.shtml",
           "recid":"1791251"}]}
```

## 频道号（**实测**，2026-10-07）
| channelid | 栏目 | recordCount | 备注 |
|---|---|---|---|
| **232534** | **常见问题** | **158** | ★ 主力，一次能取 100 条 |
| 223015 | 留言选登 | **5** | 很少；`perpage` 放大与翻页都无效（p2 返回 0 条） |

## 给接手的人：**省市站大概是同一套**
WAS5 是政府站常见的检索中间件。**省/市的生态环境厅、应急管理厅站上先试这个路径**：
`GET https://<域名>/was5/web/search?channelid=<频道号>&perpage=100&page=N`
**难点不是接口，是找到那个 `channelid`** —— 方法见 `SITE-REGISTRY.md` 的"怎么找 channelid"。
⚠ **不带 `channelid` 时，连本站也返回 711 字节空页** —— 别据此判定"这个站没有 WAS5"。
"""
from __future__ import annotations

import time

SITE = {
    "key": "mee",
    "name": "生态环境部",
    "kind": "api",
    "level": "national",
    "entry": "https://www.mee.gov.cn/hdjl/",
    "status": "ok",
    "note": "WAS5 检索接口 /was5/web/search；常见问题 channelid=232534（158 条）",
}

API = "https://www.mee.gov.cn/was5/web/search"
REFERER = "https://www.mee.gov.cn/hdjl/"
#: (频道号, 栏目名) —— 加频道就在这里加一行
CHANNELS = [("232534", "常见问题"), ("223015", "留言选登")]
PERPAGE = 100
PAUSE = 3.0            # 接口很轻，但保持礼貌


def _looks_like_question(answer: str, question: str | None) -> bool:
    """判断 `answer` 是否其实是问题原文（该接口个别条目的字段装错）。

    判据：以提问腔开头（问：/请问/我想咨询/尊敬的领导），或与标题前 20 字重合。
    """
    a = (answer or "").strip()
    if a.startswith(("问：", "问:", "请问", "我想咨询", "咨询：")):
        return True
    q = (question or "").strip()
    return bool(q) and len(q) >= 20 and a[:20] == q[:20]


def harvest(fetch, *, limit: int | None = None, channels=None) -> list[dict]:
    """按统一格式返回该站问答。

    ⚠ `fetch` 必须能带 `params=` 与 `headers=`（httpx.Client.get 的签名）。
    """
    out: list[dict] = []
    for ch, ch_name in (channels or CHANNELS):
        page, total = 1, None
        while True:
            r = fetch(API, params={"channelid": ch, "orderby": "-DOCRELTIME",
                                   "keyword": "", "page": str(page),
                                   "perpage": str(PERPAGE)},
                      headers={"Referer": REFERER})
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] {ch_name} 第 {page} 页 HTTP {r.status_code}（停）")
                break
            try:
                j = r.json()
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] {ch_name} 第 {page} 页不是 JSON（{type(e).__name__}）停")
                break
            items = j.get("items") or []
            if total is None:
                total = j.get("recordCount")
                print(f"    [{SITE['key']}] {ch_name}（channelid={ch}）recordCount={total}")
            for it in items:
                q = it.get("doctitle")
                a = it.get("doccontent")
                # ⚠ 2026-10-07 加守卫：该接口个别条目的 `doccontent` 装的是**问题原文**
                #   （实测「关于伪造机动车检验报告情节严重判定咨询」的答复字段以"问："开头）。
                #   这类条目**丢弃**，别把问题当答复写进语料。
                if not a or _looks_like_question(a, q):
                    print(f"    [{SITE['key']}] 丢弃疑似「问题当答复」条目："
                          f"{(q or '')[:30]}")
                    continue
                out.append({
                    "source": SITE["key"],
                    "id": str(it.get("recid") or it.get("docpuburl") or ""),
                    "url": it.get("docpuburl"),
                    "question": q,
                    "answer": a,
                    "asked_at": it.get("lxrq"),
                    "answered_at": it.get("hfrq"),
                    "dept": it.get("hfdw"),
                    "channel": ch_name,
                    # 站点特有字段原样留着（接口以后可能加字段，别丢）
                    "extra": {k: v for k, v in it.items()
                              if k not in ("doctitle", "doccontent", "docpuburl",
                                           "lxrq", "hfrq", "hfdw", "recid")},
                })
            if limit and len(out) >= limit:
                return out[:limit]
            if len(items) < PERPAGE:
                break
            page += 1
            time.sleep(PAUSE)
    return out
