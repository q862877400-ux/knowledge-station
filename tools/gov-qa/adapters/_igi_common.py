"""IGI 平台公共基座（`/IGI/nbhd/openGovmsgbox.do`）——**多省共用**的留言信箱开放接口。

## 平台识别（2026-10-07）
同一套接口在至少两省出现：
 · 吉林：`https://haiyun.jl.gov.cn/IGI`（siteId=117, appId=96, groupId=172），
   详情 `method=viewGovmsgbox&siteId=117&metadataId=<id>`；
 · 贵州：`https://sthj.guizhou.gov.cn/IGI`（siteId=501471, appId=590）。
⇒ 记入台账「**发现通用平台**」，加省只需补 (base, siteId, appId, groupId) 三个值。

## 通用调用契约
 · 列表：`GET {base}/nbhd/openGovmsgbox.do?method=listGovmsgboxs
   &siteId=&order=1&appId=&groupId=&pageIndex=N&pageSize=M`
 · 明细：`GET {base}/nbhd/openGovmsgbox.do?method=viewGovmsgbox&siteId=&metadataId=<id>`
 · ⚠ **必须带 Referer**（指向该厅站点的信箱页），否则服务端 403。
 · 记录字段：`TITLE / CONTENT / HTMLCONTENT / SUBMITTIME / REPLYTIME / REPLYDEPT /
   METADATAID / ISREPLY / PROVINCE / CITY / AREA / REGION / QUERYNUMBER / GOVMSGBOXTYPE`
   —— **含省/市/区三级归属**（本模块唯一的县级归属来源）。
"""
from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path

LIST_TPL = ("{base}/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
            "&siteId={sid}&order=1&appId={aid}&pageIndex={p}&pageSize={n}")
LIST_TPL_GROUP = (LIST_TPL + "&groupId={gid}")
DETAIL_TPL = ("{base}/nbhd/openGovmsgbox.do?method=viewGovmsgbox"
              "&siteId={sid}&metadataId={mid}")
PAUSE = 1.2
PAGE_SIZE = 20
TAG_RE = re.compile(r"<[^>]+>")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def existing_ids(site_key: str) -> set[str]:
    """读 `data/<site_key>-*.jsonl` 已有 id（供适配器做**续采**用，可选）。

    ⚠ 为什么需要它：IGI 列表接口**只按 `pageIndex` 翻页**，没有「从某条之后」的游标。
    若每轮都从第 1 页跑，`harvest.py` 的按 id 去重会把新数据全挡掉 ⇒ **第二轮起恒 0 新增**
    （实测 sn-igi/xz-igi 就卡在首批几条上）。适配器开跑前取一次已有 id 传进 `skip_ids`，
    已知条目不再请求明细 ⇒ `limit` 变成「本轮新增条数」，反复跑即可逐轮推进。
    """
    ids: set[str] = set()
    try:
        for p in DATA_DIR.glob(f"{site_key}-*.jsonl"):
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    mid = str(json.loads(line).get("id") or "").strip()
                    if mid:
                        ids.add(mid)
    except Exception:                                                       # noqa: BLE001
        pass
    return ids


def clean(frag: str | None) -> str:
    """去标签 + **还原 HTML 实体** + 压空白（答复正文是 HTML 片段）。

    ★ 2026-10-09 修（**影响全部 96 个 IGI 适配器，含另一个对话的线**）：
      原实现只去标签、**不还原实体** ⇒ `&nbsp;` 会以**字面 6 个字符**留在正文里
      （`re.sub(r"\\s+")` 匹配不到它 —— 它不是空白字符，是实体文本）。
      实测 `sx-igi` 7,281 条：**958 条（13.2%）正文含字面 `&nbsp;`**、
      **422 条（5.8%）以它开头**（例：`"&nbsp; &nbsp; &nbsp;经与留言人沟通…"`）
      ⇒ 污染考卷语料。山西/内蒙古/贵州/广西/宁夏等 IGI 源同样受影响。
      顺序沿用本仓既有教训（`SITE-REGISTRY` §十二 jx-zf）：**先去标签、再还原实体**，
      最后压空白（`&nbsp;` 还原成 `\\xa0` 后由 `\\s+` 吃掉）。
      ⚠ 参数名由 `html` 改为 `frag` —— 原名会**遮蔽 `html` 模块**。
      ⚠ 已落盘的历史行**不会被改写**（`harvest` 按 id 去重、只追加）⇒
        存量要清必须整站重采（`skip_ids=set()`）。
    """
    if not frag:
        return ""
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", frag))).strip()


def ts(ms) -> str | None:
    """毫秒时间戳 → `YYYY-MM-DD HH:MM:SS`；非法/0 返回 None。"""
    try:
        v = int(ms)
    except (TypeError, ValueError):
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v / 1000)) if v > 0 else None


def harvest_igi(fetch, *, SITE: dict, base: str, site_id: str, app_id: str,
                group_id: str | None, referer: str,
                limit: int | None = None, max_pages: int = 200,
                page_from: int = 1,
                skip_ids: set[str] | None = None) -> list[dict]:
    """翻页取列表（仅已答复），逐条取明细拿答复正文，返回统一记录。

    `skip_ids`：已落盘的 id 集合；命中则**不请求明细**、不计入 `limit` ⇒
    `limit` 语义变为「本轮新增条数」，可反复跑逐轮推进（见 `existing_ids()`）。

    `page_from`（2026-10-09 新增，默认 1 = 旧行为不变）：**从第几页开始翻**。
    用于把一个大站按页窗口切开、逐窗口落盘（见 `recon/igi-chunked.py --page-chunk`）。
    动机：`harvest_igi` 是「翻完页才返回」⇒ 一个 5,000 条的大站要跑 ~2 小时，
    中途被中断则**整站零产出**（`igi-chunked.py` 的逐 siteId 落盘也救不了站内的部分）。
    ★ 调用方必须自行保证 `max_pages` 是**绝对页号上界**（不是窗口长度）。

    ★ 2026-10-09 两处默认值改动（原因见 SITE-REGISTRY §十一，**影响另一个对话**）：
     1. `skip_ids=None` 由「不跳过」改为「**自动取 `existing_ids(SITE['key'])`**」。
        原因：85 个薄壳适配器（`gz_*` 36 + `jl_*` 38 + 其他）都没传这个参数，
        它们的续采**恒 0 新增**（实测 `gz-zrzy --limit 5` 收 5 条全是旧记录）。
        要显式关掉（例如想重刷已落盘条目的内容）传 `skip_ids=set()`。
     2. `max_pages` 由 30 提到 200。原因：30 页 × 20 = **600 条硬顶**，
        贵州 `gz-zrzy`(598) / `gz-portal`(571) / `gz-whhly`(505) 都卡在这个顶上，
        而第 31 页以后**确实还有数据**（实测 200）；旧值让那部分永远取不到。
    """
    if skip_ids is None:
        skip_ids = existing_ids(SITE.get("key", ""))
    out: list[dict] = []
    skipped = 0
    for page in range(page_from, max_pages + 1):
        if limit and len(out) >= limit:
            break
        if group_id:
            url = LIST_TPL_GROUP.format(base=base, sid=site_id, aid=app_id,
                                        gid=group_id, p=page, n=PAGE_SIZE)
        else:
            url = LIST_TPL.format(base=base, sid=site_id, aid=app_id,
                                  p=page, n=PAGE_SIZE)
        r = fetch(url, headers={"Referer": referer})
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            rows = (r.json().get("datas") or {}).get("data") or []
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        if not rows:
            break
        answered = [x for x in rows if int(x.get("ISREPLY") or 0) == 1]
        print(f"    [{SITE['key']}] 第 {page} 页：{len(rows)} 条（已答复 {len(answered)}）")
        for it in answered:
            if limit and len(out) >= limit:
                break
            mid = it.get("METADATAID")
            if mid and skip_ids and str(mid) in skip_ids:
                skipped += 1                      # 已落盘 ⇒ 省掉一次明细请求
                continue
            answer = ""
            if mid:
                time.sleep(PAUSE)
                d = fetch(DETAIL_TPL.format(base=base, sid=site_id, mid=mid),
                          headers={"Referer": referer})
                if getattr(d, "status_code", 0) == 200:
                    try:
                        replies = (d.json().get("datas") or {}).get("REPLYS") or []
                        answer = clean(" ".join(
                            (x or {}).get("REPLYHTMLCONTENT") or "" for x in replies))
                    except Exception as e:                                  # noqa: BLE001
                        print(f"    [{SITE['key']}] 明细 {mid} 解析失败 {type(e).__name__}")
            if len(answer) < 10:
                continue
            extra = {
                "title": clean(it.get("TITLE")),
                "query_number": it.get("QUERYNUMBER"),
                "msg_type": it.get("GOVMSGBOXTYPE"),
                "province": it.get("PROVINCE"),
                "city": it.get("CITY"),
                "area": it.get("AREA"),
                "region": it.get("REGION"),
                "platform": "IGI",
                "answer_kind": "办理答复（厅长信箱，常引条款/标准号）",
            }
            chain = [x for x in (extra["province"], extra["city"], extra["area"]) if x]
            if chain:
                extra["pForumNames"] = chain
            out.append({
                "source": SITE["key"],
                "id": str(mid),
                "url": SITE["entry"] + f"?id={mid}",
                "question": clean(it.get("CONTENT")) or clean(it.get("HTMLCONTENT"))
                            or extra["title"],
                "answer": answer,
                "asked_at": ts(it.get("SUBMITTIME") or it.get("CRTIME")),
                "answered_at": ts(it.get("REPLYTIME") or it.get("FINISHTIME")),
                "dept": clean(it.get("REPLYDEPT") or it.get("DEALDEPTNAME")),
                "channel": "厅长信箱·信件公示",
                "extra": extra,
            })
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条"
          + (f"（跳过已落盘 {skipped} 条）" if skipped else ""))
    return out
