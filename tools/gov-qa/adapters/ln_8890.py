"""适配器：**辽宁省·12345 民心智慧听**（省政务服务网 `lnzwfw.gov.cn/8890`，JeecgBoot 前端 + 公开 JSON 接口）。

## 站点事实（2026-10-09 实探，证据 recon/ln8890/）

· 入口 `https://www.lnzwfw.gov.cn/8890/`（SPA「12345 民心智慧听」）。前端壳是
  JeecgBoot（`_app.config.js`：`VITE_GLOB_DOMAIN_URL=https://www.lnzwfw.gov.cn/8890/server-api`），
  业务代码按路由懒加载（chunk 见 vendor 内 `__vitePreload`）。
· **公开接口（无需登录 / cookie，实测 200）** 定义在业务 chunk `portal-632feec9.js`，
  基址 `{DOMAIN}/common/`：
    · 知识库列表：`GET /common/knowledge/page?pageNo=<p>&pageSize=100`
      → `result.total=13942`、`pages=140`；每条**已含问答**
      （`fileName`=问题、`fileMemo`=答复、`key1/2/3`=分类、`upBmmc`=部门、
       `city_dictText`、`startDate/endDate`）。明细 `GET /common/knowledge/get?id=<id>`。
    · 咨询投诉列表：`GET /common/page_qa?pageNo=<p>&pageSize=100`
      → `result.total=8210`、`pages=83`；列表**只有问题**（`askTitle`/`askContent`，
      `answerContent=null`）⇒ 需逐条 `GET /common/get_qa_byId?id=<id>` 取答复
      （`answerContent`/`unit`/`city_dictText`/`type_dictText`/`askName`/`finishDate`）。
    · 计数：`/common/count_qa`=8210、`/common/knowledge/count`=13942。
  ⚠ `/common/appeal/page`（我的诉求）返回 `result=null` —— 需登录，**不采**。
· `pageSize` 上限 100（传 200 仍返回 100）。

## 环境变量（分阶段跑的关键）

· `LN8890_PARTS`：`kb`（知识库）/`qa`（咨询投诉），逗号分隔；默认 `kb,qa`。
· `LN8890_QA_FROM` / `LN8890_QA_TO`：咨询投诉**页码区间**（1 基、含端点；TO=0 表示到末页）。
  因 `harvest.py` 只在跑完时落盘，qa 逐条明细耗时较长，可按页段分批跑、每段独立落盘。
"""
from __future__ import annotations

import html as _html
import math
import os
import re
import time

SITE = {
    "key": "ln-8890",
    "name": "辽宁省·12345民心智慧听（咨询投诉+知识库）",
    "kind": "api",
    "level": "province",
    "entry": "https://www.lnzwfw.gov.cn/8890/",
    "status": "ok",
    "note": "JeecgBoot 公开接口 /common/knowledge/page(13942) + /common/page_qa(8210，逐条 get_qa_byId)；无需登录",
}

DOMAIN = "https://www.lnzwfw.gov.cn/8890/server-api"
KB_PAGE_API = DOMAIN + "/common/knowledge/page"
QA_PAGE_API = DOMAIN + "/common/page_qa"
QA_DETAIL_API = DOMAIN + "/common/get_qa_byId"
KB_DETAIL_API = DOMAIN + "/common/knowledge/get"
REFERER = "https://www.lnzwfw.gov.cn/8890/"
PAGE_SIZE = 100
PAUSE = 1.5
MAX_CONSEC_FAIL = 8          # 连续失败熔断阈值

TAG_RE = re.compile(r"<[^>]+>")


def clean(s) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", _html.unescape(TAG_RE.sub(" ", str(s)))).strip()


def _parts() -> set[str]:
    raw = os.environ.get("LN8890_PARTS", "kb,qa")
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _get_json(fetch, url: str, params: dict | None = None):
    """GET + JSON，失败返回 None（绝不抛异常冒泡）。"""
    try:
        r = fetch(url, params=params, headers={"Referer": REFERER})
    except Exception:                                                       # noqa: BLE001
        return None, "exc"
    if getattr(r, "status_code", 0) != 200:
        return None, f"http{getattr(r, 'status_code', '?')}"
    try:
        return r.json(), None
    except Exception:                                                       # noqa: BLE001
        return None, "json"


def _page(fetch, api: str, page: int):
    """取一页，返回 (records, total, err)。"""
    data, err = _get_json(fetch, api, {"pageNo": page, "pageSize": PAGE_SIZE})
    if err:
        return [], None, err
    res = (data or {}).get("result") or {}
    return (res.get("records") or []), res.get("total"), None


def _harvest_kb(fetch, out: list[dict], limit: int | None) -> int:
    """知识库：列表即含问答，逐页收。"""
    consec = 0
    total = None
    page = 1
    while True:
        if limit and len(out) >= limit:
            break
        rows, total, err = _page(fetch, KB_PAGE_API, page)
        if err:
            consec += 1
            print(f"    [{SITE['key']}] kb 第 {page} 页失败 {err}（连败 {consec}）")
            if consec >= MAX_CONSEC_FAIL:
                print(f"    [{SITE['key']}] kb 连败 {consec} 次，熔断")
                break
            time.sleep(PAUSE)
            page += 1
            continue
        consec = 0
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                break
            mid = str(it.get("id") or "")
            answer = clean(it.get("fileMemo"))
            question = clean(it.get("fileName"))
            if not mid or len(answer) < 10 or len(question) < 4:
                continue
            out.append({
                "source": SITE["key"] + "-kb",
                "id": mid,
                "url": f"{KB_DETAIL_API}?id={mid}",
                "question": question,
                "answer": answer,
                "asked_at": it.get("startDate"),
                "answered_at": it.get("endDate"),
                "dept": clean(it.get("upBmmc")) or None,
                "channel": "知识库",
                "extra": {
                    "key1": it.get("key1"),
                    "key2": it.get("key2"),
                    "key3": it.get("key3"),
                    "city": it.get("city_dictText"),
                    "type": it.get("type_dictText"),
                    "view_count": it.get("viewCount"),
                    "like_count": it.get("likeCount"),
                    "platform": "辽宁12345民心智慧听",
                    "answer_kind": "知识库答复",
                },
            })
        npages = math.ceil((total or 0) / PAGE_SIZE) if total else 0
        print(f"    [{SITE['key']}] kb 第 {page}/{npages or '?'} 页：{len(rows)} 条"
              f"（累计 {len(out)}）")
        if total and page * PAGE_SIZE >= total:
            break
        page += 1
        time.sleep(PAUSE)
    return len(out)


def _harvest_qa(fetch, out: list[dict], limit: int | None) -> int:
    """咨询投诉：翻列表拿 id，再逐条取答复。支持 LN8890_QA_FROM/TO 页段。"""
    page_from = max(1, _int_env("LN8890_QA_FROM", 1))
    page_to = _int_env("LN8890_QA_TO", 0)
    consec = 0
    total = None
    page = page_from
    while True:
        if limit and len(out) >= limit:
            break
        if page_to and page > page_to:
            break
        rows, total, err = _page(fetch, QA_PAGE_API, page)
        if err:
            consec += 1
            print(f"    [{SITE['key']}] qa 第 {page} 页失败 {err}（连败 {consec}）")
            if consec >= MAX_CONSEC_FAIL:
                print(f"    [{SITE['key']}] qa 连败 {consec} 次，熔断")
                break
            time.sleep(PAUSE)
            page += 1
            continue
        consec = 0
        if not rows:
            break
        npages = math.ceil((total or 0) / PAGE_SIZE) if total else 0
        got = 0
        for it in rows:
            if limit and len(out) >= limit:
                break
            mid = str(it.get("id") or "")
            if not mid:
                continue
            time.sleep(PAUSE)
            det, derr = _get_json(fetch, QA_DETAIL_API, {"id": mid})
            if derr:
                print(f"    [{SITE['key']}] qa 明细 {mid} 失败 {derr}")
                continue
            d = (det or {}).get("result") or {}
            answer = clean(d.get("answerContent"))
            question = clean(d.get("askContent")) or clean(d.get("askTitle")) \
                or clean(it.get("askContent")) or clean(it.get("askTitle"))
            if len(answer) < 10 or len(question) < 4:
                continue
            out.append({
                "source": SITE["key"],
                "id": mid,
                "url": f"{QA_DETAIL_API}?id={mid}",
                "question": question,
                "answer": answer,
                # ⚠⚠ **不再把 `createTime` 当提问时刻**（spec 005 T202，2026-10-10 实测）。
                #   证据：7,807 条里 **4,946 条（63.4%）挤在同一分钟**
                #   `2026-01-23 08:16`，折合 **82 条/秒** —— 真实群众提问不可能有这种速率
                #   ⇒ `createTime` 是**入库/批量发布时间**，不是提问时刻。
                #   同源 `ln-8890-kb`（走知识库接口、字段不同）13,941 条**零倒置**，
                #   是绝好的对照组 ⇒ 问题只在这一条路径的字段选择上。
                #   ⇒ 提问时刻**本源不可得**，诚实写 None（不许拿发布时间冒充）。
                "asked_at": None,
                # `finishDate` 是**纯日期**（`2026-09-29`，无时分秒），且实测**恒 ≤ createTime**；
                # 作为「办结日期」使用，精度只到天 —— 下游按天用，别当精确时刻。
                "answered_at": d.get("finishDate") or it.get("finishDate"),
                "dept": clean(d.get("unit")) or None,
                "channel": "咨询投诉",
                "extra": {
                    "ask_title": clean(d.get("askTitle")),
                    "ask_name": d.get("askName"),
                    "city": d.get("city_dictText"),
                    "type": d.get("type_dictText"),
                    "state": d.get("dataStatus_dictText"),
                    "view_count": d.get("viewCount") or it.get("viewCount"),
                    "platform": "辽宁12345民心智慧听",
                    "answer_kind": "办理答复",
                    # 保留原始值，但**标清它是入库时间不是提问时间**
                    "record_publish_time": d.get("createTime") or it.get("createTime"),
                    "time_fields_note": "createTime 是入库/批量发布时间（实测 63.4% 挤在同一分钟）；"
                                        "finishDate 是纯日期办结日；本源无可靠提问时刻",
                },
            })
            got += 1
        print(f"    [{SITE['key']}] qa 第 {page}/{npages or '?'} 页：{len(rows)} 条"
              f"（收 {got}，累计 {len(out)}）")
        if total and page * PAGE_SIZE >= total:
            break
        page += 1
        time.sleep(PAUSE)
    return len(out)


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采「12345 民心智慧听」公开语料：知识库 + 咨询投诉。

    · `limit`：**总条数**上限（`harvest.py --limit`）。
    · `LN8890_PARTS`：`kb`/`qa` 子集；`LN8890_QA_FROM/TO`：qa 页段。
    """
    parts = _parts()
    out: list[dict] = []
    print(f"    [{SITE['key']}] parts={sorted(parts)}，总上限 {limit or '∞'}")
    if "kb" in parts:
        _harvest_kb(fetch, out, limit)
        print(f"    [{SITE['key']}] 知识库累计 {len(out)} 条")
    if "qa" in parts:
        _harvest_qa(fetch, out, limit)
        print(f"    [{SITE['key']}] 咨询投诉累计 {len(out)} 条")
    print(f"    [{SITE['key']}] 合计收 {len(out)} 条")
    return out
