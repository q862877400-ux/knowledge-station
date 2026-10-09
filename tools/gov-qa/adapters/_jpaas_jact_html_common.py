"""jpaas-jact「留言选登」变体 · **列表 JSON + 明细 HTML** 公共引擎（多市共用）。

## 与 `_jpaas_jact_common` 的区别
`_jpaas_jact_common.harvest_jpaas` 的明细走 JSON 接口
`interface/transact/find-transact-detail`。但**泰州/扬州**实测该接口返回「无权限」，
真实明细是**服务端渲染的 HTML 页** `front/mail-pub-detail?iid=<iid>`
（页面模板取自 `/jact_files/pagemodel/SZ/images/page.js` 的
`_url + 'mail-pub-detail?iid=' + d.iid`）。故另起本引擎，复用 `_jact_common.parse_detail`
解析「标签 <td> / 值 <td>」结构。

## 接口
```
列表 GET {base}/api-gateway/jpaas-jact-web-server/front/find-mail-pub-list
        ?{platform_key}={platform_value}&pageNum=<p>&pageSize=<n>
     → {"code":0,"count":N,"data":[{iid,title,transactNo,submitDate,handleTime,
        handleGroup,submitTargetName,state,…}]}
     ⚠ 参数名因站而异：泰州/扬州都吃 `platformIid`（首页链接里带的就是它）。
     ⚠ `front/mail-pub-list.do`（带 .do）返回的是**门户 HTML 页**，不是数据；别用。
明细 GET {base}/api-gateway/jpaas-jact-web-server/front/mail-pub-detail?iid=<iid>
     → HTML 表格：标题/内容/办件分类/办件编号/提交时间/处理状态/答复内容/答复部门/答复日期
       （`_jact_common.parse_detail` 解析，标签别名见下）
```

## 标签别名（各市用词不同，实测）
泰州/扬州：`答复内容/答复部门/答复日期`（省平台 jact 多为 `内容回复/答复单位/回复日期`）
⇒ 用 `ALIASES` 归一，否则答复取不到 ⇒ 整站收 0 条。
"""
from __future__ import annotations

import html as _html
import re
import time

LIST_PATH = "/api-gateway/jpaas-jact-web-server/front/find-mail-pub-list"
DETAIL_PATH = "/api-gateway/jpaas-jact-web-server/front/mail-pub-detail"
PAUSE = 1.5
PAGE_SIZE = 20
TAG_RE = re.compile(r"<[^>]+>")
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)

ALIASES = {
    "标题": "标题",
    "内容": "内容",
    "提交时间": "提交时间",
    "来信日期": "提交时间",
    "来信时间": "提交时间",
    "处理状态": "处理状态",
    "答复内容": "内容回复",
    "回复内容": "内容回复",
    "内容回复": "内容回复",
    "答复部门": "答复单位",
    "回复单位": "答复单位",
    "答复单位": "答复单位",
    "答复日期": "回复日期",
    "回复时间": "回复日期",
    "回复日期": "回复日期",
}


def _cell_text(html: str | None) -> str:
    if not html:
        return ""
    return _html.unescape(re.sub(r"\s+", " ", TAG_RE.sub(" ", html))).strip()


def _norm(label: str) -> str:
    """标签归一：**去掉全部空白 + 去尾部冒号**（扬州用「标 题：」「答复内容：」）。

    泰州无冒号、扬州带全角冒号且字间有空格 ⇒ 不归一就一个都匹配不上（踩过：扬州收 0 条空转）。
    """
    return re.sub(r"\s+", "", label).rstrip("：:")


def parse_detail_html(html: str) -> dict:
    """解析明细 HTML：`<td>标签</td><td>值</td>` 相邻两格 → {规范键: 值}。

    ⚠ 与 `_jact_common.parse_detail` 的差别：**标签先归一**（去空白/去尾部冒号），
    以兼容扬州「标 题：」这类写法；`内容回复` 取**最后一个非空值**（防占位）。
    """
    cells = [_cell_text(x) for x in TD_RE.findall(html or "")]
    out: dict[str, str] = {}
    for i, c in enumerate(cells):
        key = ALIASES.get(_norm(c))
        if not key or i + 1 >= len(cells):
            continue
        val = cells[i + 1]
        if key == "内容回复":
            if val and val not in {"无", "无。", "暂无", "-"}:
                out[key] = val
        else:
            out.setdefault(key, val)
    return out


def _env_page_from() -> int:
    """起始页号：环境变量 `GOVQA_PAGE_FROM`（用于把超长源分块采）。"""
    import os
    try:
        return max(1, int(os.environ.get("GOVQA_PAGE_FROM", "1")))
    except ValueError:
        return 1


def harvest_jpaas_html(fetch, *, SITE: dict, base: str, platform_key: str,
                       platform_value: str, referer: str,
                       page_size: int = PAGE_SIZE, limit: int | None = None,
                       pause: float = PAUSE, max_pages: int = 400,
                       page_from: int | None = None) -> list[dict]:
    """翻页取某 jpaas-jact 栏目的已答复留言（问题 + 答复原文，明细为 HTML）。

    `page_from` = 起始页号（默认读环境变量 `GOVQA_PAGE_FROM`，再默认 1）。
    ⚠ 存在的意义：`harvest.py` **只在跑完时落盘**，而本源逐条抓明细（单条 2-3s），
    总量上千条的栏目跑不完就被 timeout 杀掉 ⇒ **零产出**
    （2026-10-09 实测：扬州 7,837 条跑 6h40m 被 timeout 杀掉，白跑）。
    分块跑法：
        GOVQA_PAGE_FROM=1   ... --limit 2000
        GOVQA_PAGE_FROM=101 ... --limit 2000     # pageSize=20 ⇒ 2000 条 = 100 页
    """
    out: list[dict] = []
    total = None
    page = page_from if page_from is not None else _env_page_from()
    while page <= max_pages:
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(f"{base}{LIST_PATH}",
                      params={platform_key: platform_value,
                              "pageNum": page, "pageSize": page_size},
                      headers={"Referer": referer})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            j = r.json()
        except Exception:                                                   # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（停）")
            break
        rows = j.get("data") or []
        if total is None:
            total = j.get("count")
            print(f"    [{SITE['key']}] count={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            iid = it.get("iid")
            if not iid:
                continue
            try:
                d = fetch(f"{base}{DETAIL_PATH}", params={"iid": iid},
                          headers={"Referer": referer})
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 明细 {iid}：{type(e).__name__}（跳过）")
                time.sleep(pause)
                continue
            if getattr(d, "status_code", 0) != 200:
                time.sleep(pause)
                continue
            f = parse_detail_html(d.text or "")
            answer = (f.get("内容回复") or "").strip()
            if len(answer) < 10:            # 未答复/办理中，跳过
                time.sleep(pause)
                continue
            title = f.get("标题") or it.get("title") or ""
            body = f.get("内容") or ""
            question = title if not body else f"{title}\n{body}"
            out.append({
                "source": SITE["key"],
                "id": str(iid),
                "url": f"{base}{DETAIL_PATH}?iid={iid}",
                "question": question,
                "answer": answer,
                "asked_at": f.get("提交时间") or None,
                "answered_at": f.get("回复日期") or None,
                "dept": f.get("答复单位") or it.get("handleGroup")
                        or it.get("submitTargetName") or None,
                "channel": "政民互动·留言选登",
                "extra": {
                    "title": title,
                    "transact_no": it.get("transactNo"),
                    "handle_status": f.get("处理状态") or None,
                    "platform": "jpaas-jact（列表 JSON + 明细 HTML）",
                },
            })
            time.sleep(pause)
        if total is not None and page * page_size >= int(total):
            break
        page += 1
        time.sleep(pause)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
