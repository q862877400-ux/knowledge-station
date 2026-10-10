"""适配器：**商丘市·市长信箱**（`/Petition/list?petitionLetterBoxId=13`）。

## 站点事实（2026-10-10 实测）

- 列表页 `https://www.shangqiu.gov.cn/Petition/list?petitionLetterBoxId=13`
  **服务端渲染**，一页 10 条，`<table class="letterList">` 里每行
  `<tr class="openLetter">`：
  ```
  <td class="num">1</td>
  <td class="title petitioncontent"><a title="主题" href="/petition/22880">主题</a></td>
  <td class="open">已公开</td>
  <td class="dep">睢阳区人民政府</td>
  <td class="state">已办结</td>
  <td class="date">2026-09-20</td>
  <td class="clicks">503</td>
  ```
- 分页：`/Petition/list_2?petitionLetterBoxId=13`、`_3`（**实测最大页号 3**）
- 详情 `https://www.shangqiu.gov.cn/petition/<数字 id>`，**服务端渲染**，
  `<tr class="trResults">` 里的 `<td class="tdCon">` 是**答复正文**，
  同区块还有「回复部门 / 回复日期」。

## ★ 为什么值得建

1. **它是河南第 1 个可采的市级源** —— 河南 18 个零记录市此前一条数据都没有。
2. **页面自带统计**：来信总数 **10,462** / 已办理 **10,441**（办理率 99.8%）。
3. **答复质量高**：实测 10/10 非空，且常带**具体部门/地点/时限/条款**
   （如「睢阳区住房和城乡建设局核实…已修复」「信号灯南北直行调整为 40 秒」）
   ⇒ 适合当考卷料。

## ⚠ 与既有负面结论的关系（别搞混）

`SITE-REGISTRY` 写着「**河南 10 市 —— 全部 NO/BLOCK，零命中**」——
**那条的上下文是 IGI 普查**，只证明**这些市没有 IGI**，
**不证明没有别的平台**。本条就是"别把一条否定结论当成全称结论"的实例。

## ⚠ 只采公开信件

列表页里 `class="open"` 是**公开状态**；实测本页 10 条**全是「已公开」**。
本适配器**只取列表页给出的条目**（站方已经筛选过公开性），不猜、不越权。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sq-szxx",
    "name": "商丘市·市长信箱",
    "kind": "static",
    "level": "city",
    "region": "商丘市",
    "entry": "https://www.shangqiu.gov.cn/Petition/list?petitionLetterBoxId=13",
    "status": "ok",
    "note": "服务端渲染 letterList 表 + /petition/<id> 详情；来信总数 10462（实测 10/10 答复非空）",
}

BASE = "https://www.shangqiu.gov.cn"
LIST_TPL = BASE + "/Petition/list{page}?petitionLetterBoxId=13"   # page="" 或 "_2"
DETAIL_TPL = BASE + "/petition/{mid}"
#: ⚠⚠ **站点有 CC 防护，明文写着「每秒不能多于 1 次页面请求」**（2026-10-10 实测）。
#:   我第一版设 `PAUSE = 1.0`（正好 1 次/秒）⇒ 连续抓十几条后**全站 403**
#:   （连首页都 403），403 页面原文：
#:   「检测到您的 IP 在短时间内请求次数过多……本站已开启 CC 防护……
#:     请勿使用扫描工具……**每秒不能多于 1 次页面请求**」。
#:   ⇒ 现在放宽到 **2.5 秒/请求**，留足余量；且**遇 403 立即停**（不重试、不硬闯）。
PAUSE = 2.5
MAX_PAGES = 30

#: HTML 注释 / doctype / CDATA —— 窄正则 `</?[A-Za-z]` **吃不掉**它们
#:   （`<!--` 不以字母开头）。实测（2026-10-10）：周口答复里混进了
#:   `<!--47个文件要求meta-->` ⇒ 必须在剥标签**之前**先剥注释。
_COMMENT = re.compile(r"<!--.*?-->|<![^>]*>", re.S)
_TAG = re.compile(r"</?[A-Za-z][^>]*>")          # ⚠ 只吃**真 HTML 标签**，
#   否则 `《出生证明》` 这类中文尖括号会被当成标签吃掉（本模块已踩过的坑）。
_BR = re.compile(r"(?i)<br\s*/?>")
_P = re.compile(r"(?i)</p>")
_WS = re.compile(r"[ \t\r\f\v]+")


def _clean(s) -> str:
    """去标签 + 还原实体 + 压空白。"""
    if not s:
        return ""
    s = _COMMENT.sub(" ", str(s))
    s = _BR.sub("\n", str(s))
    s = _P.sub("\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    s = s.replace("\xa0", " ")
    s = _WS.sub(" ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def _real(v) -> str:
    """清洗后只保留真实内容（`null`/空串一律当没有）。"""
    s = _clean(v)
    return "" if s.strip().lower() in ("null", "none", "undefined") else s


def _cell(row: str, cls: str) -> str:
    m = re.search(rf'<td[^>]*class="[^"]*\b{cls}\b[^"]*"[^>]*>(.*?)</td>', row, re.S)
    return m.group(1) if m else ""


def _parse_list(html: str) -> list:
    """从列表页抽条目（只读，不落库）。"""
    i = html.find('<table class="letterList">')
    if i < 0:
        return []
    seg = html[i:]
    j = seg.find("</tbody>")
    seg = seg[:j if j > 0 else len(seg)]
    out = []
    for row in re.findall(r'<tr[^>]*class="openLetter[^"]*"[^>]*>(.*?)</tr>', seg, re.S):
        m = re.search(r'href="/petition/(\d+)"', row)
        if not m:
            continue
        mid = m.group(1)
        title_m = re.search(r'<a[^>]*title="([^"]*)"', row)
        out.append({
            "id": mid,
            "title": _real(title_m.group(1) if title_m else _cell(row, "title")),
            "open_state": _real(_cell(row, "open")),
            "dept": _real(_cell(row, "dep")) or None,
            "state": _real(_cell(row, "state")),
            "date": _real(_cell(row, "date")),
            "clicks": _real(_cell(row, "clicks")),
        })
    return out


def _parse_detail(html: str) -> dict:
    """从详情页抽答复正文（`trResults` 区块）。"""
    out = {"question": "", "answer": "", "reply_dept": None, "reply_date": None}
    # 答复正文
    m = re.search(r'<tr class="trResults">(.*?)</tr>', html, re.S)
    if m:
        cm = re.search(r'<td class="tdCon"[^>]*>(.*?)</td>', m.group(1), re.S)
        out["answer"] = _real(cm.group(1)) if cm else ""
    # 回复部门 / 回复日期
    m2 = re.search(r'<tr class="trName">(.*?)</tr>', html, re.S)
    if m2:
        cells = re.findall(r'<td class="td(?:Name|Con)"[^>]*>(.*?)</td>', m2.group(1), re.S)
        if len(cells) >= 4:
            out["reply_dept"] = _real(cells[1]) or None
            out["reply_date"] = _real(cells[3]) or None
    # 信件内容（问题正文）
    m3 = re.search(r'<th[^>]*>信件内容</th>(.*?)</table>', html, re.S)
    if m3:
        cm = re.search(r'<td class="tdCon"[^>]*>(.*?)</td>', m3.group(1), re.S)
        out["question"] = _real(cm.group(1)) if cm else ""
    return out


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """翻列表 + 逐条取详情。

    ⚠ **逐条取详情必须打进度点**（本模块为此踩过 5 次坑：
    明细阶段静默会被误判成"站点节流"）。
    """
    out: list[dict] = []
    seen: set[str] = set()
    n_detail = n_fail = 0
    for page in range(1, MAX_PAGES + 1):
        if limit and len(out) >= limit:
            break
        url = LIST_TPL.format(page="" if page == 1 else f"_{page}")
        try:
            r = fetch(url)
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页失败 {type(e).__name__}（停）")
            break
        if getattr(r, "status_code", 0) == 403:
            # ⚠ 站点 CC 防护明确要求「每秒不能多于 1 次」⇒ **遇 403 立即停**，
            #   不重试、不硬闯（硬闯会让封禁时间更长）。
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP 403（CC 防护："
                  f"请求过快，需冷却；**停**，不重试）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP {getattr(r,'status_code','?')}（停）")
            break
        items = _parse_list(r.text)
        if not items:
            break
        for it in items:
            if limit and len(out) >= limit:
                break
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            det = {}
            try:
                d = fetch(DETAIL_TPL.format(mid=it["id"]))
                if getattr(d, "status_code", 0) == 200:
                    det = _parse_detail(d.text)
            except Exception:                                           # noqa: BLE001
                det = {}
            n_detail += 1
            if not det.get("answer"):
                n_fail += 1
                if n_detail % 10 == 0:
                    print(f"    [{SITE['key']}] 明细进度 {n_detail}"
                          f"（无答复 {n_fail}）", flush=True)
                time.sleep(PAUSE)
                continue
            if n_detail % 10 == 0:
                print(f"    [{SITE['key']}] 明细进度 {n_detail}"
                      f"（无答复 {n_fail}）", flush=True)
            out.append({
                "source": SITE["key"],
                "id": it["id"],
                "url": DETAIL_TPL.format(mid=it["id"]),
                "question": det.get("question") or it["title"],
                "answer": det["answer"],
                "asked_at": it["date"] or None,
                "answered_at": det.get("reply_date") or None,
                "dept": det.get("reply_dept") or it["dept"],
                "channel": "市长信箱",
                "extra": {
                    "title": it["title"],
                    "open_state": it["open_state"],
                    "case_state": it["state"],
                    "clicks": it["clicks"],
                    "platform": "商丘 power CMS（letterList + /petition/<id>）",
                },
            })
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条；明细取 {n_detail} 条，其中无答复 {n_fail} 条")
    return out
