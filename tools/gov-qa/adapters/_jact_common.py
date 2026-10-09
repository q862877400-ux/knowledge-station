"""江苏省级厅局「统一咨询投诉 / 咨询建言」平台（jact）· 共用采集引擎。

## 平台事实（2026-10-08 实测，28 个厅局信箱全部跑通）
江苏省政府门户「互动交流 → 咨询建言」（`https://www.jiangsu.gov.cn/col/col81602/`）
聚合了**各厅局自己域名下部署的同款 jact 应用**（万户 hanweb 系，路径 `/jact/front/`）：
 · 生态环境厅 `https://sthjt.jiangsu.gov.cn/jact/`（sysid=143，431 条）
 · 发改委     `https://fzggw.jiangsu.gov.cn/jact/`（sysid=112，143 条）
 · 教育厅     `https://jyt.jiangsu.gov.cn/jact/`（sysid=126/34，810/404 条）…
**每个厅域名单独部署、数据各自独立**；同一域名下可有**多个 sysid**（不同栏目/信箱，
实测两两**不重叠** ⇒ 都要采）。⇒ **按 (host, sysid) 各采各的**。

## 接口
```
POST {base}/jact/front/dataproxy_mailpublist.do
       ?startrecord=<本页起>&endrecord=<本页止>&perpage=<每页数>&groupSize=3
     body(表单) sysid=<厅局号>&datadetailid=&dicvalue=&mailnumber=&querycode=&
                groupid=&mailstate=&starttime=&endtime=&keyword=
     header 带 Referer: {base}/jact/front/mailpublist.do?sysid=<n>
 → **返回的是 JS 文本、不是 JSON**：
     totalRecord=431.0;totalPage=23;dataStore=["<tr …><a href='mailpubdetail.do?transactId=483417&sysid=143'>标题</a>…</tr>", …]
GET  {base}/jact/front/mailpubdetail.do?transactId=<id>&sysid=<n>
 → HTML 表格：label 在左 <td>、值在右 <td>：标题 / 内容(问题) / 提交时间 /
   处理状态 / 回复日期 / 内容回复(答复) / 答复单位。
```

## 解析要点（踩过的坑）
 · **列表是 JS 文本，绝不 eval**：先取 `dataStore = [ … ];` 的数组体，再用
   `"([^"]*)"` 抠每个元素 —— 元素是**双引号包裹**、内部 HTML **只用单引号**，
   所以不会误切（实测确认内部无 `"`）。
 · `transactId` 从每条 `<a href='mailpubdetail.do?transactId=…&sysid=…'>` 抠。
 · **明细是 HTML**：label/value 是**相邻的两个 `<td>`**，逐 td 取文本后
   「某 td 文本 == 标签 ⇒ 下一 td 即值」。
 · 列表里的 `title='点击标题查看详细信息'` 是 `<a>` 的属性，**真标题在 `<a>` 内文**。

## 新增一个江苏厅局 = 复制一个薄适配器
```python
from adapters._jact_common import harvest_jact
SITE = {"key": "js-xx", "name": "江苏省某厅", ...}
HOST, SYSID = "xx", "123"
def harvest(fetch, *, limit=None):
    return harvest_jact(fetch, SITE=SITE, host=HOST, sysid=SYSID, limit=limit)
```
（host+sysid 清单与实测 totalRecord 见 recon/js-jact-hunt.txt。）
"""
from __future__ import annotations

import html as _html
import re
import time

LIST_PATH = "/jact/front/dataproxy_mailpublist.do"
DETAIL_PATH = "/jact/front/mailpubdetail.do"
PAGE_SIZE = 19
GROUP_SIZE = 3
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")
#: dataStore 数组体（元素是双引号字符串；内部 HTML 只用单引号，故 [^"]* 安全）
DATASTORE_RE = re.compile(r"dataStore\s*=\s*\[(.*?)\]\s*;", re.S)
ELEM_RE = re.compile(r'"([^"]*)"')
TOTAL_RE = re.compile(r"totalRecord\s*=\s*([0-9.]+)")
ROW_TID_RE = re.compile(r"transactId=(\d+)")
ROW_TITLE_RE = re.compile(
    r"<a\s[^>]*href='[^']*transactId=\d+[^']*'[^>]*>([^<]*)</a>", re.I)
ROW_NUM_RE = re.compile(r"<td[^>]*\btitle='([^']+)'")
ROW_DATE_RE = re.compile(r">\s*(\d{4}-\d{2}-\d{2}[ \d:]*?)\s*<")
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
#: 单元格（含 `<th>`）——个别同构站点（甘肃定西）标签在 `<th>`、值在 `<td>`，
#: 只取 `<td>` 会把标签丢掉 ⇒ 整站收 0 条。默认仍只取 `<td>`（见 parse_detail）。
CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)

#: 明细页里「标签 td → 值 td」的标签 → 规范键。
#: ⚠ 同一套 jact 在不同厅局域名下的**用词不一样**（实测 credit.jiangsu.gov.cn
#:   用「答复内容/答复机构/答复时间」，而多数厅用「内容回复/答复单位/回复日期」）
#:   ⇒ 必须做别名归一，否则整站「收 0 条」（踩过：js-credit 46 条全丢）。
LABEL_ALIASES = {
    "标题": "标题",
    "内容": "内容",
    "提交时间": "提交时间",
    "处理状态": "处理状态",
    "内容回复": "内容回复",
    "答复内容": "内容回复",
    "回复日期": "回复日期",
    "答复时间": "回复日期",
    "答复单位": "答复单位",
    "答复机构": "答复单位",
    # —— 第三种变体（山东滨州，2026-10-08 实测）：来信*/回复* 用词 ——
    "来信标题": "标题",
    "来信内容": "内容",
    "来信时间": "提交时间",
    "信件状态": "处理状态",
    "回复内容": "内容回复",
    "回复单位": "答复单位",
    "回复时间": "回复日期",
}

#: 「无答复」占位值（credit 站会先给一条「答复内容 = 无」，其后才是真答复）
_NO_ANSWER = {"", "无", "无。", "暂无", "-", "（无）", "(无)"}


def clean(html: str | None) -> str:
    """去标签 + 压空白 + 解码 HTML 实体（答复正文是 HTML 片段）。

    先剥标签、后 unescape：避免把正文里被转义的 `&lt;` 重新变成真标签再被剥掉
    （与 adapters/bj_hdjl.py 同口径）。答复常含 `GB&nbsp;18596-2001` 这类实体，
    不解码会让下游「按标准号/文号匹配」漏掉。
    """
    if not html:
        return ""
    return _html.unescape(re.sub(r"\s+", " ", TAG_RE.sub(" ", html))).strip()


def parse_list(text: str) -> tuple[int, list[dict]]:
    """解析列表响应（JS 文本）→ (totalRecord, [每行 {tid,title,num,date}])。"""
    total = 0
    m = TOTAL_RE.search(text or "")
    if m:
        try:
            total = int(float(m.group(1)))
        except ValueError:
            total = 0
    rows: list[dict] = []
    dm = DATASTORE_RE.search(text or "")
    if not dm:
        return total, rows
    for elem in ELEM_RE.findall(dm.group(1)):
        t = ROW_TID_RE.search(elem)
        if not t:
            continue
        title = ROW_TITLE_RE.search(elem)
        num = ROW_NUM_RE.search(elem)
        dates = ROW_DATE_RE.findall(elem)
        rows.append({
            "tid": t.group(1),
            "title": clean(title.group(1)) if title else "",
            "num": num.group(1).strip() if num else None,
            "date": dates[-1] if dates else None,
        })
    return total, rows


def parse_detail(html: str, *, include_th: bool = False,
                 aliases: dict | None = None) -> dict:
    """解析明细页 HTML → {规范标签: 值}（label/value 是相邻两个单元格）。

    · `include_th=True`：**把 `<th>` 也当单元格**。甘肃定西等站用
      `<th>标签</th><td>值</td>`，只取 `<td>` 会丢标签 ⇒ 收 0 条；
      默认 `False`（只取 `<td>`，江苏各站口径不变）。
    · `aliases`：可覆盖/扩展标签别名（默认用模块级 `LABEL_ALIASES`）。

    ⚠ 同一标签**可能重复出现**：实测 credit 站先输出「答复内容 = 无」，
    再输出真实答复 ⇒ 「内容回复」取**最后一个非占位值**，其余标签取首次出现。
    """
    rx = CELL_RE if include_th else TD_RE
    table = aliases or LABEL_ALIASES
    cells = [clean(x) for x in rx.findall(html or "")]
    out: dict[str, str] = {}
    for i, c in enumerate(cells):
        key = table.get(c)
        if not key or i + 1 >= len(cells):
            continue
        val = cells[i + 1]
        if key == "内容回复":
            if val not in _NO_ANSWER:       # 只接受真实答复；后出现的真答复覆盖「无」
                out[key] = val
        else:
            out.setdefault(key, val)
    return out


def _post_list(fetch, *, base: str, sysid: str, start: int, end: int,
               per_page: int) -> str:
    url = (f"{base}{LIST_PATH}?startrecord={start}&endrecord={end}"
           f"&perpage={per_page}&groupSize={GROUP_SIZE}")
    body = {
        "sysid": str(sysid), "datadetailid": "", "dicvalue": "",
        "mailnumber": "", "querycode": "", "groupid": "", "mailstate": "",
        "starttime": "", "endtime": "", "keyword": "",
    }
    r = fetch.post(url, data=body, headers={
        "Referer": f"{base}/jact/front/mailpublist.do?sysid={sysid}",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    if getattr(r, "status_code", 0) != 200:
        raise RuntimeError(f"dataproxy HTTP {getattr(r, 'status_code', '?')}")
    return r.text or ""


def existing_ids(site_key: str) -> set:
    """读 `data/<site_key>-*.jsonl` 已有 id（供增量续采）。

    ⚠ 2026-10-10 第 7 轮新增：本引擎原先**没有** `skip_ids`（和修复前的
    `_gd_hdjlpt_common` 一样），每次都从第 1 页重翻、**对每一行都取明细**
    （明细是本引擎最贵的一步），且 `limit` 把**已落盘的条数**算进去。

    **实测后果**：`js-yancheng --limit 1000` 跑 **1,737 秒**，
    结果「取到 1000 条，其中**新增 0 条**」—— 一条新的都没拿到。
    这解释了盐城完成度为什么长期卡在 49.8% 不动：
    **不是站点没数据，是采集器在原地打转。**
    """
    import glob
    import json
    import os
    ids: set = set()
    data_dir = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data")
    try:
        for p in glob.glob(os.path.join(data_dir, f"{site_key}-*.jsonl")):
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.strip():
                        try:
                            mid = str(json.loads(line).get("id") or "").strip()
                        except Exception:                               # noqa: BLE001
                            continue
                        if mid:
                            ids.add(mid)
    except Exception:                                                       # noqa: BLE001
        pass
    return ids


def harvest_jact(fetch, *, SITE: dict, host: str, sysid: str,
                 limit: int | None = None, pause: float = PAUSE,
                 per_page: int = PAGE_SIZE, scheme: str = "https",
                 include_th: bool = False, label_aliases: dict | None = None,
                 skip_ids: set | None = None) -> list[dict]:
    """按统一记录格式返回某江苏厅局 jact 信箱的留言选登（问题+答复全文）。

    ⚠ `fetch` 是 harvest.py 注入的 `_Fetcher`（用 `.post` 发列表、可调用发明细）。
    `scheme` 默认 `https`（江苏各站）；个别同构站点（如甘肃定西）只走 http，
    传 `scheme="http"` 即可，**不影响既有调用方**。
    `include_th` / `label_aliases` 同为**可选**扩展（默认与江苏口径完全一致），
    供标签在 `<th>`、用词不同的同构站点复用同一引擎。

    ★ `skip_ids`（2026-10-10 第 7 轮新增）：`None` 时自动取 `existing_ids(SITE['key'])`；
    命中已落盘的 `tid` **连明细都不取**、且**不计入 `limit`** ⇒
    `limit` 语义变为「本轮**新增**条数」，可反复跑逐轮推进。
    要显式关掉（重刷已落盘条目的内容）传 `skip_ids=set()`。
    """
    if skip_ids is None:
        skip_ids = existing_ids(SITE.get("key", ""))
    base = f"{scheme}://{host}"
    out: list[dict] = []
    total = None
    skipped = 0
    page = 1
    while True:
        start = (page - 1) * per_page + 1
        end = page * per_page
        try:
            text = _post_list(fetch, base=base, sysid=sysid,
                              start=start, end=end, per_page=per_page)
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        t, rows = parse_list(text)
        if total is None:
            total = t
            print(f"    [{SITE['key']}] {host} sysid={sysid} totalRecord={total}"
                  + (f"（已落盘 {len(skip_ids)} 条，命中则跳过）" if skip_ids else ""))
        if not rows:
            break
        for row in rows:
            if limit and len(out) >= limit:
                print(f"    [{SITE['key']}] 达 limit={limit}"
                      + (f"（跳过已落盘 {skipped} 条）" if skipped else ""))
                return out
            tid = row["tid"]
            if str(tid) in skip_ids:
                skipped += 1            # ★ 已落盘 ⇒ 不取明细、不计入 limit
                continue
            try:
                d = fetch(f"{base}{DETAIL_PATH}?transactId={tid}&sysid={sysid}",
                          headers={"Referer":
                                   f"{base}/jact/front/mailpublist.do?sysid={sysid}"})
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 明细 {tid}：{type(e).__name__}（跳过）")
                time.sleep(pause)
                continue
            if getattr(d, "status_code", 0) != 200:
                time.sleep(pause)
                continue
            f = parse_detail(d.text or "", include_th=include_th,
                             aliases=label_aliases)
            answer = f.get("内容回复", "").strip()
            if not answer:
                time.sleep(pause)
                continue                # 未答复/办理中，跳过
            skip_ids.add(str(tid))      # ★ 运行中也要并回去，防同页重复
            title = f.get("标题") or row["title"]
            body = f.get("内容", "")
            question = title if not body else f"{title}\n{body}"
            out.append({
                "source": SITE["key"],
                "id": str(tid),
                "url": f"{base}{DETAIL_PATH}?transactId={tid}&sysid={sysid}",
                "question": question,
                "answer": answer,
                "asked_at": f.get("提交时间") or None,
                "answered_at": f.get("回复日期") or None,
                "dept": f.get("答复单位") or None,
                "channel": "咨询建言·留言选登",
                "extra": {
                    "host": host,
                    "sysid": str(sysid),
                    "mail_number": row.get("num"),
                    "handle_status": f.get("处理状态") or None,
                },
            })
            time.sleep(pause)
        if total is not None and page * per_page >= total:
            break
        page += 1
        time.sleep(pause)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
