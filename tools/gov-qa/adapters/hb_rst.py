"""适配器：**湖北省人力资源和社会保障厅·政务咨询留言（留言公开）**——TRS 静态列。

## 站点事实（2026-10-08 实测，证据 recon/gs-hb-hunt.txt 【湖北】）
 · 湖北省直部门子域 **不受瑞数 412 影响**（rst/nyt/wjw/zjt.hubei.gov.cn 均 200）。
 · 列表入口 `http://rst.hubei.gov.cn/hdjl/lxgs/zxjylygk/index.shtml`；
   静态分页 `index.shtml`(第1页) / `index_1.shtml` … `index_5.shtml`，
   每页 15 条，末页 5 条 ⇒ 约 80 条。
 · 明细形态 `./YYYYMM/tYYYYMMDD_ID.shtml`（TRS 静态页），实测 200，正文含：
     咨询内容（问题） / 答复时间 / 承办单位 / **办理情况公开（答复原文）**。
 · ⚠ 该列**每页列出的项**混在同页侧栏「最新」模块里，需只取本列 `./YYYYMM/t...` 的
   相对链接（本列 id=41057）。
"""
from __future__ import annotations

import re
import time

SITE = {
    "key": "hb-rst",
    "name": "湖北省人力资源和社会保障厅·政务咨询留言",
    "kind": "static",
    "level": "province",
    "entry": "http://rst.hubei.gov.cn/hdjl/lxgs/zxjylygk/",
    "status": "ok",
    "note": "TRS 静态列，约 80 条；明细含答复原文；省直部门子域不受瑞象 412 影响",
}

BASE = "http://rst.hubei.gov.cn/hdjl/lxgs/zxjylygk/"
MAX_PAGES = 12
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")
# 本列自身列表项：相对链接 ./YYYYMM/tYYYYMMDD_ID.shtml
ITEM_RE = re.compile(
    r'<a[^>]*href="\./(\d{6}/(t\d{8}_\d+)\.shtml)"[^>]*title="([^"]*)"')
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)


def _clean(html: str | None) -> str:
    if not html:
        return ""
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip()


def _parse_detail(html: str) -> dict:
    """从明细页取 问题 / 答复 / 承办单位 / 咨询时间 / 答复时间。"""
    # 先截出正文主体（去掉脚本/样式）
    body = re.sub(r"(?is)<script.*?</script>", " ", html)
    body = re.sub(r"(?is)<style.*?</style>", " ", body)
    text = _clean(body)

    def grab(label: str, nxt: list[str]) -> str:
        # 抓 label 到下一个 label 之间的文本
        m = re.search(label + r"[:：]\s*(.*?)(?=" + "|".join(nxt) + r"[:：]|$)",
                      text)
        return m.group(1).strip() if m else ""

    labels = ["咨询内容", "答复时间", "承办单位", "办理情况公开", "咨询人", "咨询时间",
              "咨询方式"]
    question = grab("咨询内容", labels)
    answer = grab("办理情况公开", labels)
    # 答复正文尾部会带上页面通用页脚（"扫一扫在手机上查看当前页面…"），截掉。
    answer = re.split(r"扫一扫在手机上查看当前页面", answer)[0].strip()
    dept = grab("承办单位", labels)
    asked = grab("咨询时间", labels)
    answered = grab("答复时间", labels)
    return {"question": question, "answer": answer, "dept": dept,
            "asked_at": asked, "answered_at": answered}


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(MAX_PAGES):
        if limit and len(out) >= limit:
            break
        url = BASE + ("index.shtml" if page == 0 else f"index_{page}.shtml")
        r = fetch(url)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        items = ITEM_RE.findall(r.text)
        if not items:
            break
        print(f"    [{SITE['key']}] 第 {page} 页：{len(items)} 条")
        for rel, rid, title in items:
            if limit and len(out) >= limit:
                break
            if rid in seen:
                continue
            seen.add(rid)
            time.sleep(PAUSE)
            d = fetch(BASE + rel)
            if getattr(d, "status_code", 0) != 200:
                continue
            det = _parse_detail(d.text)
            if len(det["answer"]) < 10:
                continue
            out.append({
                "source": SITE["key"],
                "id": rid,
                "url": BASE + rel,
                "question": det["question"] or title,
                "answer": det["answer"],
                "asked_at": det["asked_at"] or None,
                "answered_at": det["answered_at"] or None,
                "dept": det["dept"],
                "channel": "政务咨询留言·留言公开",
                "extra": {
                    "title": title,
                    "platform": "TRS-static",
                    "answer_kind": "政策咨询答复（人社厅，常引法规）",
                    "province": "湖北省",
                },
            })
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
