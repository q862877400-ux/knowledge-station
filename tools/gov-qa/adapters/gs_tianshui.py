"""适配器：**天水市·政民互动（书记留言板 / 市长留言板，万户 leadermail）**。

## 站点事实（2026-10-08 实测，worker-gansu）
 · 天水门户 `www.tianshui.gov.cn`（**http 可达**）政民互动「留言评论 / 留言答复」是
   万户（VSBSite）**leadermail** 模块，列表**服务端渲染**：
     · 聚合列表 GET `http://www.tianshui.gov.cn/zmhd/xj_list.jsp
         ?totalpage=<N>&PAGENUM=<p>&urltype=tree.TreeTempUrl&wbtreeid=3861`
       —— 一页**同时渲染 4 个栏目**（共 404/202/656/1182 条），每栏 15 行，
       且 `PAGENUM` **同步驱动 4 栏翻页**（栏目页数 27/14/44/79，翻到自己的末页即空）。
       ⇒ 遍历 PAGENUM=1..max(79) 并按 leadermailid 去重即可取全（约 2444 条）。
     · 行内链接 `xj_info.jsp?urltype=leadermail.LeaderMailContentUrl&wbtreeid=3861&leadermailid=<HASH>`
     · 详情 GET `http://www.tianshui.gov.cn/zmhd/xj_info.jsp?...&leadermailid=<HASH>`
       → HTML 表格，标签/值为相邻 `<td>`：流水号 / 标题 / 写信时间 / 信件内容 /
         处理状态 / 回复内容 / 处理对象 / 处理时间。
"""
from __future__ import annotations

import re
import time

BASE = "http://www.tianshui.gov.cn/zmhd/"
LIST_TPL = (BASE + "xj_list.jsp?totalpage={tp}&PAGENUM={p}"
            "&urltype=tree.TreeTempUrl&wbtreeid={col}")
DETAIL_TPL = (BASE + "xj_info.jsp?urltype=leadermail.LeaderMailContentUrl"
              "&wbtreeid={col}&leadermailid={mid}")
COLUMN = "3861"
PAUSE = 1.5
MAX_PAGES = 300
TAG_RE = re.compile(r"<[^>]+>")
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
ROW_RE = re.compile(r"leadermailid=([0-9A-F]{16,})")
TOTALPAGE_RE = re.compile(r"totalpage=(\d+)")
#: 各栏真实条数：「共 N 条」（实测 404 / 202 / 656 / 1182）
COUNTS_RE = re.compile(r"共\s*(\d+)\s*条")
#: 每栏每页行数（实测 15）
ROWS_PER_PAGE = 15

#: 详情页标签（去空白后匹配）→ 规范键。占位/头部行会被「下一格仍是标签」规则跳过。
LABELS = {
    "流水号": "流水号",
    "标题": "标题",
    "写信时间": "写信时间",
    "信件内容": "信件内容",
    "处理状态": "处理状态",
    "回复内容": "回复内容",
    "处理对象": "处理对象",
    "处理时间": "处理时间",
}

SITE = {
    "key": "gs-tianshui",
    "name": "天水市·政民互动（书记留言板·市长留言板）",
    "kind": "static",
    "level": "city",
    "entry": BASE,
    "status": "ok",
    "note": "万户 leadermail；聚合列表 xj_list.jsp(wbtreeid=3861) 4 栏同页翻页；约 2444 条；须 http",
}


def clean(html: str | None) -> str:
    """去标签 + 压空白（正文是 HTML 片段）。"""
    if not html:
        return ""
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip()


def _norm(s: str) -> str:
    return (s or "").replace(" ", "").replace("\xa0", "").replace("&nbsp;", "").strip()


def parse_detail(html: str) -> dict[str, str]:
    """解析详情页 → {规范标签: 值}（label/value 相邻两个 <td>；跳过「下一格仍是标签」）。"""
    cells = [clean(x) for x in TD_RE.findall(html or "")]
    out: dict[str, str] = {}
    for i, c in enumerate(cells):
        key = LABELS.get(_norm(c))
        if not key or i + 1 >= len(cells):
            continue
        val = cells[i + 1]
        if _norm(val) in LABELS:            # 头部行的标签（如「信件内容」后紧跟「流水号」）跳过
            continue
        out.setdefault(key, val)
    return out


def existing_ids(site_key: str) -> set:
    """读 `data/<site_key>-*.jsonl` 已有 id（供增量续采，避免重取明细）。"""
    import glob
    import json
    import os
    ids: set = set()
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    try:
        for p in glob.glob(os.path.join(data_dir, f"{site_key}-*.jsonl")):
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.strip():
                        try:
                            mid = str(json.loads(line).get("id") or "").strip()
                        except Exception:                                   # noqa: BLE001
                            continue
                        if mid:
                            ids.add(mid)
    except Exception:                                                       # noqa: BLE001
        pass
    return ids


def harvest(fetch, *, limit: int | None = None,
            skip_ids: set | None = None) -> list[dict]:
    """遍历聚合列表 PAGENUM，逐条取详情，返回已答复留言（问题 + 答复全文）。

    ★ 2026-10-10 第 7 轮两处改动：

    1. **加 `skip_ids`**（`None` 时自动取已落盘 id）：命中则**连明细都不取**，
       且不计入 `limit` ⇒ 可反复跑逐轮推进。
    2. **给「第 3 步逐条取明细」加进度日志**。原来的日志只有第 2 步（扫列表），
       而**最慢的是第 3 步**（每条一次详情请求 + `PAUSE`）⇒
       跑起来会出现「列表日志停在某一页、之后长时间没有任何输出」的假象。
       **我为此误判了两次**（先判「站点侧节流」，其实是静默阶段）。
       ⇒ 现在每 50 条打一行，一眼能看出是「慢」还是「死」。
    """
    if skip_ids is None:
        skip_ids = existing_ids(SITE.get("key", ""))
    if skip_ids:
        print(f"    [{SITE['key']}] 已落盘 {len(skip_ids)} 条，命中则跳过明细")
    referer = BASE
    # 1) 先取第 1 页，拿最大 totalpage（4 栏中最大者）
    first = fetch(LIST_TPL.format(tp=1, p=1, col=COLUMN), headers={"Referer": referer})
    if getattr(first, "status_code", 0) != 200:
        print(f"    [{SITE['key']}] 列表首页 HTTP {getattr(first, 'status_code', '?')}（停）")
        return []
    # ⚠ 2026-10-10 实测修正：`totalpage` 只是**回显参数**，不是真实页数 ——
    #   传 `tp=1` 页面就显示 `totalPage=0`，传 `tp=99` 就显示 `99`。
    #   **真实条数在各栏标题的「共 N 条」里**（实测 404 / 202 / 656 / 1182）。
    #   ⇒ 从「共 N 条」算页数：每栏 15 行/页 ⇒ ceil(max(N) / 15)。
    counts = [int(x) for x in COUNTS_RE.findall(first.text or "")]
    tps = [int(x) for x in TOTALPAGE_RE.findall(first.text or "")]
    if counts:
        maxpage = -(-max(counts) // ROWS_PER_PAGE)      # 向上取整
    elif tps:
        maxpage = max(tps)
    else:
        maxpage = 1
    maxpage = max(1, min(maxpage, MAX_PAGES))
    print(f"    [{SITE['key']}] 各栏共 {sorted(set(counts))} 条"
          f"（totalpage 回显 {sorted(set(tps))}）→ 遍历 1..{maxpage}")

    # 2) 收集全部 leadermailid（去重，保持出现顺序）
    #    ⚠ 有了 `skip_ids` 之后，判「够不够」要看**未见过的**条数，
    #      不能看 `len(ids)`（后者含已落盘的）。
    ids: list[str] = []
    seen: set[str] = set()
    unseen = 0
    for p in range(1, maxpage + 1):
        if limit and unseen >= limit * 3:       # 列表远快于详情，留足余量即可
            break
        if p == 1:
            text = first.text or ""
        else:
            r = fetch(LIST_TPL.format(tp=maxpage, p=p, col=COLUMN),
                      headers={"Referer": referer})
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] 列表第 {p} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（停）", flush=True)
                break
            text = r.text or ""
        new = 0
        for mid in ROW_RE.findall(text):
            if mid not in seen:
                seen.add(mid)
                ids.append(mid)
                new += 1
                if mid not in skip_ids:
                    unseen += 1
        print(f"    [{SITE['key']}] 列表第 {p}/{maxpage} 页：新增 {new} 条"
              f"（累计 {len(ids)}，其中未见 {unseen}）", flush=True)
        time.sleep(PAUSE)

    # 3) 逐条取详情（★ 这是最慢的一步：每条一次请求 + PAUSE ⇒ 必须有进度日志）
    out: list[dict] = []
    skipped = 0
    todo = [m for m in ids if m not in skip_ids]
    print(f"    [{SITE['key']}] 待取明细 {len(todo)} 条"
          f"（总候选 {len(ids)}，跳过已落盘 {len(ids) - len(todo)}）", flush=True)
    for i, mid in enumerate(todo, 1):
        if limit and len(out) >= limit:
            print(f"    [{SITE['key']}] 达 limit={limit}（明细已取 {i - 1} 条）", flush=True)
            break
        try:
            d = fetch(DETAIL_TPL.format(col=COLUMN, mid=mid), headers={"Referer": referer})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 明细 {mid}：{type(e).__name__}（跳过）")
            time.sleep(PAUSE)
            continue
        if getattr(d, "status_code", 0) != 200:
            time.sleep(PAUSE)
            continue
        f = parse_detail(d.text or "")
        answer = f.get("回复内容", "").strip()
        if len(answer) < 10:                # 未答复/办理中，跳过
            time.sleep(PAUSE)
            continue
        skip_ids.add(mid)
        title = f.get("标题", "")
        body = f.get("信件内容", "")
        out.append({
            "source": SITE["key"],
            "id": mid,
            "url": DETAIL_TPL.format(col=COLUMN, mid=mid),
            "question": title if not body else f"{title}\n{body}",
            "answer": answer,
            "asked_at": f.get("写信时间") or None,
            "answered_at": f.get("处理时间") or None,
            "dept": f.get("处理对象") or None,
            "channel": "政民互动·留言选登",
            "extra": {
                "serial": f.get("流水号"),
                "handle_status": f.get("处理状态"),
                "platform": "wanhu-leadermail",
            },
        })
        if i % 50 == 0:
            print(f"    [{SITE['key']}] 明细进度 {i}/{len(todo)}，已收 {len(out)} 条", flush=True)
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条"
          + (f"（跳过已落盘 {skipped} 条）" if skipped else ""))
    return out
