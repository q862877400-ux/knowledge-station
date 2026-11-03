"""适配器：**菏泽市·政民互动·咨询选登（山东一体化 CMS，hdjl-service 接口）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city3-菏泽-list.html、sd-city3-hz-lyxq.html）
 · 门户 `www.heze.gov.cn` 政民互动 `http://www.heze.gov.cn/zmhd/`，咨询选登
   `http://www.heze.gov.cn/zmhd/hdlist/`。
 · 列表（Vue + axios）：`POST {host}/hdjl-service/sysweb/listweb/{page}/{size}`，
   body `{exDwIds, startTime, cityLevelDisplay, dq:"0530", statue, title, decribe}`
   （`exDwIds`/`cityLevelDisplay` 从页面 Vue data 抠出）。
   · ⚠ 与 **潍坊**（`/xxgk/hdjl-service/…`）**同族**，但潍坊返回 `{"code":401}`（需登录/
     加密），菏泽**无鉴权**、直接 200；故菏泽可采、潍坊暂缓。
 · 详情：`GET {host}/hdjl-service/sysweb/find/{id}` → `data[0]`：
   `decribe`=问题、`reply`=答复(HTML)、`replytime`=答复时间、`createTime`=提问时间、
   `dept`=部门、`title`、`name`=提问人。
 · 实测 **total=613**（size=1 时 totalPage 亦 613）；`startTime` 取 2015/2020/2024 或省略
   均为 613 ⇒ 该数值即全量公开集。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sd-heze",
    "name": "菏泽市·政民互动·咨询选登（山东一体化CMS）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.heze.gov.cn/zmhd/hdlist/",
    "status": "ok",
    "note": "POST /hdjl-service/sysweb/listweb（无鉴权）；详情 /sysweb/find/{id}；total=613",
}

HOST = "http://www.heze.gov.cn"
LIST_API = HOST + "/hdjl-service/sysweb/listweb/{page}/{size}"
DETAIL_API = HOST + "/hdjl-service/sysweb/find/{mid}"
REFERER = HOST + "/zmhd/hdlist/"
BODY_BASE = {
    "exDwIds": ("2c908088819842f70181ad76957900f7,"
                "2c908088819842f701819a3dc2600062"),
    "startTime": "2024-01-01",
    "cityLevelDisplay": "1",
    "dq": "0530",
    "statue": "",
    "title": "",
    "decribe": "",
}
PER_PAGE = 20
PAUSE = 1.2
TAG_RE = re.compile(r"<[^>]+>")


def clean(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", _html.unescape(TAG_RE.sub(" ", s))).strip()


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采菏泽咨询选登（列表 + 逐条 find 取答复）。"""
    out: list[dict] = []
    page = 1
    total = None
    while True:
        if limit and len(out) >= limit:
            break
        if total is not None and (page - 1) * PER_PAGE >= total:
            break
        try:
            r = fetch.post(LIST_API.format(page=page, size=PER_PAGE), json=BODY_BASE,
                           headers={"Referer": REFERER,
                                    "Content-Type": "application/json;charset=utf-8"})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页请求失败 {type(e).__name__}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            data = (r.json() or {}).get("data") or {}
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        if total is None:
            total = int(data.get("total") or 0)
            print(f"    [{SITE['key']}] total={total}")
        rows = data.get("dataList") or []
        if not rows:
            break
        got = 0
        for it in rows:
            if limit and len(out) >= limit:
                break
            mid = str(it.get("id") or "")
            if not mid:
                continue
            time.sleep(PAUSE)
            d = fetch(DETAIL_API.format(mid=mid),
                      headers={"Referer": REFERER})
            if getattr(d, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] 明细 {mid} HTTP "
                      f"{getattr(d, 'status_code', '?')}")
                continue
            try:
                arr = (d.json() or {}).get("data") or []
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 明细 {mid} 解析失败 {type(e).__name__}")
                continue
            det = arr[0] if arr else {}
            answer = clean(det.get("reply"))
            if len(answer) < 10:
                continue
            out.append({
                "source": SITE["key"],
                "id": mid,
                "url": HOST + f"/zmhd/lyxq/?id={mid}",
                "question": clean(det.get("decribe")) or clean(it.get("title")),
                "answer": answer,
                "asked_at": det.get("createTime") or it.get("createTime"),
                "answered_at": det.get("replytime"),
                "dept": clean(det.get("dept")) or clean(it.get("dept")),
                "channel": "政民互动·咨询选登",
                "extra": {
                    "title": clean(it.get("title")),
                    "asker": det.get("name"),
                    "state": it.get("statue"),
                    "platform": "山东一体化 CMS（hdjl-service）",
                    "answer_kind": "部门答复（常引法规原文）",
                },
            })
            got += 1
        print(f"    [{SITE['key']}] 第 {page} 页：{len(rows)} 条（收 {got}，累计 {len(out)}）")
        page += 1
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
