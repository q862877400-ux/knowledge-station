"""适配器：**四川省生态环境厅 · 政务服务互动交流知识库**（静态列表 + 静态明细）。

## 站点形态（2026-10-07 实探，见 recon/dept-hd-dig.json / sc-detail-debug.txt）
 · 列表页 `https://sthjt.sc.gov.cn/sthjt/c250403/zmhdzsk_index.shtml`
   —— 真问答列表（如「哪些建设项目需要编报告书/报告表/登记表？」）；**翻页 `_index_1` 不存在（404）**，
   所以全量就是该页上的条目（含 c250404 / c250405 两个子栏目）；
 · 明细页 `/sthjt/c25040x/YYYY/M/D/<uuid>.shtml`，清洗后正文形态（**实测**）：
   `… ＞ 栏目名 栏目名 【问题】？ 发布时间：YYYY-MM-DD HH:MM:SS 来源：处室 【答复】 政策依据：… 网站地图`
   ⚠ **没有「解答内容：」标记**（我最初照着旧印象写的正则，实测 0 命中——已按真实结构改）。

## 说明
 · 量小（15 条），价值在于**给四川落一个官方问答源**并补齐省别覆盖；
 · 答复是**FAQ 简答**（1-2 句），已在 `extra.answer_kind` 标注为 FAQ 简答，
   供下游区分「简短知识库答复」与「留言板办理答复」；
 · 四川全省统一问政平台 `wz.sc.gov.cn` 从本机不可达（ConnectError），故走厅站点这条窄路。
"""
from __future__ import annotations

import re
import time
from urllib.parse import urljoin

SITE = {
    "key": "sc-st",
    "name": "四川省生态环境厅·互动知识库",
    "kind": "static",
    "level": "province",
    "entry": "https://sthjt.sc.gov.cn/sthjt/c250403/zmhdzsk_index.shtml",
    "status": "ok",
    "note": "静态列表（单页，无翻页）+ 静态明细（解答内容：标记）；量小约 20 条",
}

BASE = "https://sthjt.sc.gov.cn"
LIST_URL = BASE + "/sthjt/c250403/zmhdzsk_index.shtml"
PAUSE = 1.0

DETAIL_RE = re.compile(r'href="(/sthjt/c25040\d/\d{4}/\d{1,2}/\d{1,2}/[0-9a-f]{32}\.shtml)"')
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
#: 问题 = 「发布时间：」之前那一段（导航用 ＞ 分隔，问题就是最后一节）
Q_RE = re.compile(r"([^＞>｜|]{6,150}?)\s*发布时间[：:]")
#: 发布时间
PUB_RE = re.compile(r"发布时间[：:]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}(?:[ T][0-9:]{5,8})?)")
#: 答复 = 「来源：X」之后到「政策依据：」/页脚之前
ANS_RE = re.compile(r"来源[：:]\s*[^\s]{0,24}\s*(.+?)(?:政策依据[：:]|网站地图|版权所有|$)", re.S)
FOOT_CUT = re.compile(r"(网站地图|版权所有|主办单位|网站标识码)")


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _parse_detail(html: str, url: str) -> dict | None:
    text = _text(html)
    m = ANS_RE.search(text)
    if not m:
        return None
    answer = FOOT_CUT.split(m.group(1))[0].strip()
    if len(answer) < 10:
        return None
    qm = Q_RE.search(text[:m.start() + 40])
    question = ""
    if qm:
        question = qm.group(1).strip()
        # 去掉导航残留（栏目名会在问题前重复一次）
        for sep in ("＞", ">", "|", "｜"):
            if sep in question:
                question = question.rsplit(sep, 1)[-1].strip()
        # 栏目名与问题粘连（实测：`建设项目环境影响评价 建设项目环境影响评价 【问题】？`）
        dup = re.match(r"^(.{3,40}?)\s*\1", question)
        if dup:
            question = question[dup.end():].strip()
        # 栏目名与问题粘连时，取最后一个以 ？/? 结尾的片段
        if "？" in question or "?" in question:
            tail = re.split(r"[？?]", question)
            for seg in tail:
                if len(seg) >= 6:
                    question = seg + "？"
    if not question or len(question) < 6:
        tm = TITLE_RE.search(html)
        question = _text(tm.group(1)) if tm else ""
    question = question.strip()[:150]
    if not question:
        return None
    pub = PUB_RE.search(text)
    return {"question": question, "answer": answer,
            "asked_at": pub.group(1) if pub else None}


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """抓四川厅互动知识库的问答（列表去重后逐条取明细）。"""
    r = fetch(LIST_URL)
    if getattr(r, "status_code", 0) != 200:
        print(f"    [{SITE['key']}] 列表 HTTP {getattr(r, 'status_code', '?')}（停）")
        return []
    links = sorted(set(DETAIL_RE.findall(r.text or "")))
    print(f"    [{SITE['key']}] 列表条目 {len(links)} 条（单页，无翻页）")
    out: list[dict] = []
    for href in links:
        if limit and len(out) >= limit:
            break
        time.sleep(PAUSE)
        d = fetch(urljoin(BASE, href))
        if getattr(d, "status_code", 0) != 200:
            continue
        try:
            rec = _parse_detail(d.text or "", href)
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 解析失败 {href[-28:]} {type(e).__name__}")
            continue
        if not rec:
            continue
        uid = href.rsplit("/", 1)[-1].replace(".shtml", "")
        out.append({
            "source": SITE["key"],
            "id": uid,
            "url": urljoin(BASE, href),
            "question": rec["question"],
            "answer": rec["answer"],
            "asked_at": rec["asked_at"],
            "answered_at": None,
            "dept": "四川省生态环境厅",
            "channel": "互动交流知识库",
            "extra": {"list_url": LIST_URL},
        })
    print(f"    [{SITE['key']}] 收 {len(out)} 条（列表 {len(links)} 条）")
    return out
