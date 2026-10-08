"""适配器：**科学技术部·公众问答**（`app.most.gov.cn/ac_gzcy_app/gzwd`，RuoYi 后台接口）。

## 站点事实（2026-10-09 实测，证据 recon/nat-most-*）
 · 入口 `https://app.most.gov.cn/ac_gzcy_app/gzwd`（科技部门户 → 互动 → 公众问答）。
 · 列表接口（**POST，免登录**）：
   `POST https://app.most.gov.cn/ac_gzcy_app/gzwd/viewMessagelist?tid=<N>&pageSize=<M>&pageNum=<P>`
   → JSON `{"total":4797,"rows":[{id,tid,title,content,answerinfoTotal,
          createTime,bjTime,answerDeptName,startName}]}`
   ⚠ **必须 POST**（GET 返回 `Request method 'GET' not supported`）。
 · **答复正文内联在 `answerinfoTotal`**（无需明细请求）⇒ 采得很快。
 · tid 分类（实测条数）：1=业务咨询 4797 / 2=政策咨询 2065 / 3=提出建议 582 / 4=反馈问题 1367，
   合计约 **8811** 条。
 · 另有 `commonQuestionlist`（常见问题解答）栏目，接口同族，本适配器一并采（channel 区分）。
 · 实测答复常点名《文件》（例：《国家重点研发计划管理暂行办法》国科发资〔2024〕28 号）⇒ 优质考卷料。
"""
from __future__ import annotations

import hashlib
import time

SITE = {
    "key": "nat-most",
    "name": "科学技术部·公众问答",
    "kind": "api",
    "level": "national",
    "entry": "https://app.most.gov.cn/ac_gzcy_app/gzwd",
    "status": "ok",
    "note": "RuoYi 后台接口 viewMessagelist(POST)；答复内联 answerinfoTotal；tid1-4 合计≈8811",
}

BASE = "https://app.most.gov.cn/ac_gzcy_app/gzwd"
LIST_API = BASE + "/viewMessagelist"
COMMON_API = BASE + "/commonQuestionlist"
REFERER = BASE + "/viewMessage?tid=1"
PAGE_SIZE = 50
PAUSE = 1.5

#: (tid, 栏目名)
TIDS = [("1", "业务咨询"), ("2", "政策咨询"), ("3", "提出建议"), ("4", "反馈问题")]


def _post_list(fetch, url: str, params: dict, page: int, page_size: int) -> dict:
    r = fetch.post(url, params=params, data={"pageSize": page_size, "pageNum": page},
                   headers={"Referer": REFERER, "X-Requested-With": "XMLHttpRequest"})
    if getattr(r, "status_code", 0) != 200:
        raise RuntimeError(f"HTTP {getattr(r, 'status_code', '?')}")
    return r.json()


def _row(r: dict, channel: str) -> dict | None:
    answer = (r.get("answerinfoTotal") or "").strip()
    if len(answer) < 10:
        return None
    title = (r.get("title") or "").strip()
    content = (r.get("content") or "").strip()
    # ⚠ 常见问题（commonQuestionlist）返回的 id 为 null，须自造稳定 id（否则去重失效/无限追加）
    rid = str(r.get("id") or r.get("qNum") or "")
    if not rid:
        rid = "c-" + hashlib.md5(f"{title}|{content}|{answer}".encode("utf-8")).hexdigest()[:16]
    return {
        "source": SITE["key"],
        "id": rid,
        "url": REFERER,
        "question": title + (("\n" + content) if content else ""),
        "answer": answer,
        "asked_at": r.get("createTime"),
        "answered_at": r.get("bjTime"),
        "dept": r.get("answerDeptName"),
        "channel": channel,
        "extra": {
            "title": r.get("title"),
            "tid": r.get("tid"),
            "start_name": r.get("startName"),
            "platform": "most-gzwd",
        },
    }


def harvest(fetch, *, limit: int | None = None, page_size: int = PAGE_SIZE) -> list[dict]:
    """取科技部公众问答四个分类的问答（答复内联，无需明细）。"""
    out: list[dict] = []
    seen: set[str] = set()
    for tid, name in TIDS:
        if limit and len(out) >= limit:
            break
        page = 1
        total = None
        while True:
            if limit and len(out) >= limit:
                return out[:limit]
            try:
                j = _post_list(fetch, LIST_API, {"tid": tid}, page, page_size)
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] {name} 第 {page} 页失败 {type(e).__name__}: {e}（停）")
                break
            rows = j.get("rows") or []
            if total is None:
                total = j.get("total")
                print(f"    [{SITE['key']}] {name}（tid={tid}）total={total}")
            if not rows:
                break
            new_ids = 0
            for r in rows:
                rec = _row(r, name)
                if rec and rec["id"] not in seen:
                    seen.add(rec["id"])
                    out.append(rec)
                    new_ids += 1
            if new_ids == 0:            # 同页重复（服务端忽略分页）⇒ 立即停，防死循环
                break
            if total is not None and page * page_size >= int(total):
                break
            page += 1
            time.sleep(PAUSE)
    # 常见问题解答（接口同族；字段可能略有出入，容错）
    if not (limit and len(out) >= limit):
        page = 1
        ctotal = None
        seen: set[str] = set()
        while True:
            try:
                j = _post_list(fetch, COMMON_API, {}, page, page_size)
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 常见问题 第 {page} 页失败 {type(e).__name__}（停）")
                break
            rows = j.get("rows") or []
            if ctotal is None:
                ctotal = j.get("total")
                print(f"    [{SITE['key']}] 常见问题解答 total={ctotal}")
            if not rows:
                break
            # ⚠ commonQuestionlist **忽略 pageNum**（任何页都返回同一批，实测 total=15）
            #   ⇒ 必须靠 (a) total 边界 (b) 去重集 双保险，否则**死循环**（踩过）。
            new_ids = 0
            for r in rows:
                rec = _row(r, "常见问题解答")
                if rec and rec["id"] not in seen:
                    seen.add(rec["id"])
                    out.append(rec)
                    new_ids += 1
            if limit and len(out) >= limit:
                return out[:limit]
            if new_ids == 0:
                break
            if ctotal is not None and page * page_size >= int(ctotal):
                break
            page += 1
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
