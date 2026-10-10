"""适配器：**安阳市·政民互动**（`leader-mail/list`，市长信箱/连线政府/市长电话）。

## 站点事实（2026-10-10 实测）

- 列表接口：`POST https://page.anyang.gov.cn/zwfw/leader-mail/list`
  表单参数 `size` / `page` / `systemType`（**不是** pageNum/pageSize —— 从页面 JS 抄的）
- 响应：`{"result":200,"msg":"成功","obj":{"datas":[...],
  "pageNumber","pageSize","totalPage","totalRow"}}`
- **每条记录自带问答全文**（`askContent` + `replyContent`）⇒ **不需要逐条取明细**
- `systemType` 分三类（实测 `totalRow`）：

  | systemType | 名称 | 总量 |
  |---|---|---|
  | 0 | 连线政府 | 338 |
  | 1 | 市长电话 | 1,620 |
  | 2 | 市长信箱 | 551 |
  | 3 | （空）| 0 |

  ⇒ 合计 **2,509 条**

## 质量（铁律第 6 条：取明细确认答复非空）

抽 6 页（每类 3 页 × 20 条）共 **120 条，空答复 0**，答复含具体部门/金额/电话
（如「两项补贴发放标准均为 92.5 元/人月」「拨打 2263370 进行咨询」）。

## ⚠ 与既有负面结论的关系

`SITE-REGISTRY` 的「河南 10 市全判死」**只对 IGI 成立**。
安阳首页直接暴露了这个 `api` 端点 ⇒ **它不是"没有平台"，是"没有 IGI"**。

## ⚠ 只采公开答复

接口返回的是**已答复**的公开信件（`status=3`），本适配器照单采，不猜、不越权。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "ay-zmhd",
    "name": "安阳市·政民互动（市长信箱/连线政府/市长电话）",
    "kind": "api",
    "level": "city",
    "region": "安阳市",
    "entry": "https://www.anyang.gov.cn/zmhd/hygq/",
    "status": "ok",
    "note": "POST page.anyang.gov.cn/zwfw/leader-mail/list（size/page/systemType）；"
            "响应自带问答全文；实测 totalRow 合计 2,509（连线政府 338 / 市长电话 1620 / "
            "市长信箱 551），抽 120 条空答复 0",
}

API = "https://page.anyang.gov.cn/zwfw/leader-mail/list"
REFERER = "https://www.anyang.gov.cn/zmhd/hygq/"
PAGE_SIZE = 20
#: `systemType` → 中文名（实测）
SYSTEMS = {0: "连线政府", 1: "市长电话", 2: "市长信箱"}
PAUSE = 0.6
MAX_PAGES = 400

#: HTML 注释 / doctype / CDATA —— 窄正则 `</?[A-Za-z]` **吃不掉**它们
#:   （`<!--` 不以字母开头）。实测（2026-10-10）：周口答复里混进了
#:   `<!--47个文件要求meta-->` ⇒ 必须在剥标签**之前**先剥注释。
_COMMENT = re.compile(r"<!--.*?-->|<![^>]*>", re.S)
_TAG = re.compile(r"</?[A-Za-z][^>]*>")     # 只吃**真 HTML 标签**
_BR = re.compile(r"(?i)<br\s*/?>")
_WS = re.compile(r"[ \t\r\f\v]+")


def _clean(s) -> str:
    if not s:
        return ""
    s = _COMMENT.sub(" ", str(s))
    s = _BR.sub("\n", str(s))
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    s = s.replace("\xa0", " ")
    s = _WS.sub(" ", s)
    return re.sub(r"\n{2,}", "\n", s).strip()


def _real(v) -> str:
    s = _clean(v)
    return "" if s.strip().lower() in ("null", "none", "undefined") else s


def _norm_dt(v) -> str | None:
    """`2026/10/9 10:38:35` → `2026-10-09 10:38:35`（本模块统一格式）。"""
    s = str(v or "").strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})(?:\s+(\d{1,2}):(\d{2}):(\d{2}))?$", s)
    if not m:
        return None
    y, mo, d, hh, mm, ss = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d} {int(hh or 0):02d}:{mm or '00'}:{ss or '00'}"


def harvest(fetch, *, limit: int | None = None, max_pages: int = MAX_PAGES) -> list[dict]:
    """翻 3 个 `systemType` 的全部页。

    ⚠ 本接口是 **POST 表单**，而 `harvest.py` 传进来的 `fetch` 是 `client.get`
    的包装（**不接受 `method=` 参数**，实测会报
    `Client.get() got an unexpected keyword argument 'method'`）。
    ⇒ 本适配器**自建一个 httpx client** 发 POST，不用传入的 `fetch`。
    （与 `xz_lasa` / `_post_list_common` / `_jact_common` 同法。）

    ⚠⚠ **逐页打进度点** —— 本模块为"列表阶段有日志、明细阶段静默"踩过 5 次坑
    （被误判成"站点节流"）。本接口**响应自带问答全文**，所以没有明细阶段，
    但翻页仍要打点。
    """
    import httpx

    out: list[dict] = []
    seen: set[str] = set()
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120 Safari/537.36")
    with httpx.Client(timeout=30, headers={"User-Agent": ua},
                      follow_redirects=True, trust_env=False, verify=False) as c:
        for st, sysname in SYSTEMS.items():
            if limit and len(out) >= limit:
                break
            total = None
            for page in range(1, max_pages + 1):
                if limit and len(out) >= limit:
                    break
                try:
                    r = c.post(API, data={"size": PAGE_SIZE, "page": page,
                                          "systemType": st},
                               headers={"Referer": REFERER})
                except Exception as e:                                  # noqa: BLE001
                    print(f"    [{SITE['key']}] {sysname} 第 {page} 页失败 "
                          f"{type(e).__name__}（停该分类）")
                    break
                if getattr(r, "status_code", 0) != 200:
                    print(f"    [{SITE['key']}] {sysname} 第 {page} 页 HTTP "
                          f"{getattr(r,'status_code','?')}（停该分类）")
                    break
                try:
                    obj = (r.json().get("obj") or {})
                except Exception:                                       # noqa: BLE001
                    print(f"    [{SITE['key']}] {sysname} 第 {page} 页非 JSON（停该分类）")
                    break
                if total is None:
                    total = obj.get("totalRow")
                    print(f"    [{SITE['key']}] {sysname}: totalRow={total} "
                          f"totalPage={obj.get('totalPage')}", flush=True)
                rows = obj.get("datas") or []
                if not rows:
                    break
                added = 0
                for it in rows:
                    mid = _real(it.get("mailNum"))
                    ans = _real(it.get("replyContent"))
                    q = _real(it.get("askContent"))
                    if not mid or mid in seen:
                        continue
                    seen.add(mid)
                    if not ans:
                        continue
                    out.append({
                        "source": SITE["key"],
                        "id": mid,
                        "url": SITE["entry"],
                        "question": q or _real(it.get("title")),
                        "answer": ans,
                        "asked_at": _norm_dt(it.get("createDate")),
                        "answered_at": _norm_dt(it.get("replyDate")),
                        "dept": _real(it.get("replySite")) or None,
                        "channel": sysname,
                        "extra": {
                            "title": _real(it.get("title")),
                            "system": _real(it.get("system")) or sysname,
                            "system_type": st,
                            "case_state": it.get("status"),
                            "satisfaction": _real(it.get("satisfaction")) or None,
                            "platform": "安阳市政府网站统一技术平台（leader-mail）",
                        },
                    })
                    added += 1
                print(f"    [{SITE['key']}] {sysname} 第 {page} 页：{len(rows)} 条"
                      f"（收 {added}）", flush=True)
                time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
