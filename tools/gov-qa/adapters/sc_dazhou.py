"""适配器：**达州市·政民互动·书记市长信箱（市长信箱 JSON API，ThinkPHP）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe33/36/38/39.txt）
 · 门户 `https://www.dazhou.gov.cn`（ThinkPHP 站群）。
 · 政民互动入口：首页导航「市长信箱」→ `https://www.dazhou.gov.cn/xinxiang/`（SPA，tab 加载子页）。
   tab：`html/home.html`（首页）/ `html/publicity.html`（**来信选登**）/ `html/statistics.html`（统计）
        / `html/my-letter.html`（我的信件，需登录）。
 · 列表 API（**JSON**，`js/publicity.js` 反推）：
     `GET /xinxiang/api/Letter/publicityLetterList?page=N&type_id=&keyword=`
     → `{"code":1,"data":{"total":259,"per_page":10,"last_page":26,"data":[…]}}`
     条目字段：`id` / `serial_number` / `title` / `zgtitle` / `content`(问题正文) /
               `type_name` / `createtime`(unix) / `overtime`(unix) / `node`(当前节点) /
               `acceptdepartments[].name`(承办部门)。
 · 详情 API（`js/letters.js` 反推）：
     `GET /xinxiang/api/Letter/letterInfo?id=<id>`
     → `{"code":1,"data":{…,"content":问题,"reply":[{"way":答复正文,"department_id":…,
          "createtime":unix}],"createtime":"YYYY-MM-DD",…}}`
     ★ 答复 = 全部 `reply[].way` 拼接（一封可多部门分答）。
 · 样例：id 6062「恳请优化嘉合锦悦府小区附近公交线路」→ 达州市交通运输局答复（2026-09-22）。
"""
from __future__ import annotations

import time

SITE = {
    "key": "sc-dazhou",
    "name": "达州市·政民互动·市长信箱",
    "kind": "api",
    "level": "city",
    "entry": "https://www.dazhou.gov.cn/xinxiang/",
    "status": "ok",
    "note": "ThinkPHP JSON API：列表 /xinxiang/api/Letter/publicityLetterList?page=N（total=259）；详情 /xinxiang/api/Letter/letterInfo?id=<id>（reply[].way=答复）",
}

BASE = "https://www.dazhou.gov.cn"
LIST_URL = BASE + "/xinxiang/api/Letter/publicityLetterList"
DETAIL_URL = BASE + "/xinxiang/api/Letter/letterInfo"
REFERER = BASE + "/xinxiang/"
PAGE_SIZE = 10
PAUSE = 0.8


def _clean(s) -> str:
    if not s:
        return ""
    return str(s).replace("\r\n", "\n").replace("\r", "\n").strip()


def _ts(v):
    """unix 秒 → 'YYYY-MM-DD HH:MM:SS'；已是字符串则原样返回。"""
    if v is None or v == "":
        return None
    if isinstance(v, str) and not v.isdigit():
        return v.strip() or None
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(v)))
    except Exception:                                                       # noqa: BLE001
        return None


def _dept(it: dict):
    ds = it.get("acceptdepartments") or []
    names = [d.get("name") for d in ds if isinstance(d, dict) and d.get("name")]
    return "、".join(names) if names else None


def harvest(fetch, *, limit: int | None = None, max_pages: int = 200) -> list[dict]:
    """翻页取列表（JSON）→ 逐条取详情（JSON）拼答复。"""
    out: list[dict] = []
    seen: set[str] = set()
    total_pages = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            return out
        if total_pages is not None and page > total_pages:
            break
        try:
            r = fetch(LIST_URL, params={"page": page, "type_id": "", "keyword": ""},
                      headers={"Referer": REFERER})
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
        data = j.get("data") or {}
        rows = data.get("data") or []
        if total_pages is None:
            total_pages = int(data.get("last_page") or 0) or None
            print(f"    [{SITE['key']}] 共 {data.get('total')} 条 / {total_pages} 页")
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
            answer = ""
            asked = _ts(it.get("createtime"))
            title = _clean(it.get("zgtitle") or it.get("title"))
            question = _clean(it.get("content"))
            try:
                vr = fetch(DETAIL_URL, params={"id": sid}, headers={"Referer": REFERER})
                vd = (vr.json().get("data") or {}) if getattr(vr, "status_code", 0) == 200 else {}
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
                continue
            reps = vd.get("reply") or []
            blocks = [_clean(x.get("way")) for x in reps if isinstance(x, dict) and x.get("way")]
            answer = "\n".join(b for b in blocks if b)
            if len(answer) < 10:            # 未答复，跳过
                continue
            if vd.get("content"):
                question = _clean(vd.get("content"))
            if vd.get("title") or vd.get("zgtitle"):
                title = _clean(vd.get("zgtitle") or vd.get("title"))
            if title and question and not question.startswith(title):
                question = f"{title}\n{question}"
            elif not question:
                question = title
            if vd.get("createtime"):
                asked = _ts(vd.get("createtime")) or asked
            answered = _ts(reps[-1].get("createtime")) if reps else None
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": f"{DETAIL_URL}?id={sid}",
                "question": question,
                "answer": answer,
                "asked_at": asked,
                "answered_at": answered,
                "dept": _dept(it),
                "channel": "政民互动·市长信箱",
                "extra": {
                    "title": title,
                    "serial": it.get("serial_number"),
                    "type": it.get("type_name"),
                    "node": it.get("node"),
                    "platform": "达州 ThinkPHP JSON（xinxiang/api/Letter）",
                },
            })
            time.sleep(PAUSE)
        if new == 0:
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
