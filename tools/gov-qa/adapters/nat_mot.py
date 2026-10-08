"""适配器：**交通运输部·留言咨询**（`qa.mot.gov.cn/mapplys`，自研 JSON 列表 + HTML 明细）。

## 站点事实（2026-10-09 实测，证据 recon/nat-mot-*）
 · 门户 `qa.mot.gov.cn` 重定向到 `/mapplys/`（留言咨询系统）。
 · 列表接口（**JSON**，无需登录）：
   `GET https://qa.mot.gov.cn/mapplys/pub/visitor/userIndex/getUserByLeavingMessage
        ?pageNo=<页>&pageSize=<每页>&orderByFiled=CRTIME`
   → `{"datas":[{TITLE, QUESTIONID, id, CRTIME, PUBTIME, ZTTYPE, ZTTYPENAME, ...}],
       "pageNo":1,"pages":2603,"totalSize":7808}`
   ⚠ 列表里的 `TEXTCONTENT`(问题) / `ANSWERTEXTCONTENT`(答复) 是 **未序列化的 Oracle CLOB**
     （值形如 `oracle.sql.CLOB@617a7813`），**不能直接用** ⇒ 必须逐条取明细页。
 · 明细（**服务端渲染 HTML**，答复原文在此）：
   `GET .../pub/visitor/userIndex/questionDetail?id=<QUESTIONID>`
   页内：提问 `<h2>标题</h2>` + `<h6>【详细描述】</h6><p>正文</p>`；
   答复在 `dafu_wd` 块内 `<div class="fl w100 tiwen_cont_wd">…</div>`，
   答复单位 `答复单位：XXX`，答复时间在 `dafu_wd` 的 `<font class="fr">…</font>`。
 · 实测答复常点名文件（例：《交通运输部关于加强水上客运安全管理的意见》交海发〔2014〕142 号）⇒ 优质考卷料。

## 规模与节奏
 · `totalSize≈7808`（`pageSize=20` ⇒ 约 391 页）。**逐条明细 ⇒ 单条约 2s，全量约 4.3h**。
   ⚠ 全量采集请先与 team-lead 报备（>2h）。`limit` 用于试跑/分批。
 · 明细页是 HTML（重），请求间隔默认 2.0s。
"""
from __future__ import annotations

import os
import re
import time


def _env_page_from() -> int:
    """起始页号：环境变量 `GOVQA_PAGE_FROM`（用于把超长源分块采）。"""
    try:
        return max(1, int(os.environ.get("GOVQA_PAGE_FROM", "1")))
    except ValueError:
        return 1

SITE = {
    "key": "nat-mot",
    "name": "交通运输部·留言咨询",
    "kind": "api",
    "level": "national",
    "entry": "https://qa.mot.gov.cn/mapplys/",
    "status": "ok",
    "note": "自研 JSON 列表(getUserByLeavingMessage,totalSize≈7808)+HTML 明细(questionDetail)",
}

BASE = "https://qa.mot.gov.cn/mapplys"
LIST_API = BASE + "/pub/visitor/userIndex/getUserByLeavingMessage"
DETAIL_API = BASE + "/pub/visitor/userIndex/questionDetail"
REFERER = "https://qa.mot.gov.cn/mapplys/"
PAGE_SIZE = 20
#: ⚠ 本站反爬很凶：**短时间（约 1 分钟内 ~30 次请求）即触发 IP 级 403**（2026-10-09 实测，
#:   整站含列表接口一起 403，冷却数十分钟才恢复）。⇒ 间隔给足、遇 403 立即熔断。
PAUSE = 3.0
#: 连续 403 达此值即停（避免硬刷把 IP 封更久）
MAX_403 = 3
#: 明细连续失败多少次就熔断（返回已收部分，避免长跑成果全丢）
MAX_CONSEC_FAIL = 8

SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
#: 提问块：标题 + 【详细描述】正文
Q_TITLE_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S | re.I)
Q_BODY_RE = re.compile(r"【详细描述】\s*</b>\s*</h6>\s*<p[^>]*>(.*?)</p>", re.S | re.I)
#: 答复块：dafu_wd 整段（含答复正文/时间/单位）
#: ⚠ 结束注释实测是 `<!--dafu_wd end -->`（`end` 后有空格）——别写成无空格的紧贴式。
DAFU_RE = re.compile(r'<div[^>]*class="[^"]*dafu_wd[^"]*"[^>]*>(.*?)<!--\s*dafu_wd\s+end\s*-->', re.S | re.I)
DAFU_BODY_RE = re.compile(r'<div[^>]*class="[^"]*tiwen_cont_wd[^"]*"[^>]*>(.*?)</div>', re.S | re.I)
DAFU_TIME_RE = re.compile(r'<font[^>]*class="fr"[^>]*>\s*([\d\-: ]+?)\s*</font>', re.S | re.I)
DEPT_RE = re.compile(r"答复单位[:：]\s*(.*?)\s*(?:<|$)", re.S | re.I)
#: 提问块的时间：提问 h1 的 font.fr 里 "姓名 编号 时间"
ASK_H1_RE = re.compile(r'<h1[^>]*h1_wd[^>]*>\s*<span[^>]*>\s*提问.*?</span>\s*<font[^>]*class="fr"[^>]*>(.*?)</font>', re.S | re.I)
ASK_TIME_RE = re.compile(r"([12]\d{3}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def _text(html: str | None) -> str:
    """去脚本/样式/注释后去标签、压空白。"""
    if not html:
        return ""
    t = SCRIPT_RE.sub(" ", html)
    t = TAG_RE.sub(" ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", t).strip()


def _parse_detail(html: str) -> dict:
    """从明细 HTML 抽 (question, answer, asked_at, answered_at, dept)。"""
    body = _text(html)
    mt = Q_TITLE_RE.search(html)
    title = _text(mt.group(1)) if mt else ""
    mb = Q_BODY_RE.search(html)
    desc = _text(mb.group(1)) if mb else ""
    question = title if not desc else f"{title} {desc}".strip()

    md = DAFU_RE.search(html)
    answer = ""
    answered_at = None
    dept = None
    if md:
        block = md.group(1)
        mbody = DAFU_BODY_RE.search(block)
        answer = _text(mbody.group(1)) if mbody else ""
        mtm = DAFU_TIME_RE.search(block)
        answered_at = mtm.group(1).strip() if mtm else None
        mdp = DEPT_RE.search(_text(block))
        dept = mdp.group(1).strip() if mdp else None
    if not answer:                       # 明细结构变化时退一步：整页找 答复单位 前的正文
        mdp = DEPT_RE.search(body)
        dept = mdp.group(1).strip() if mdp else None

    asked_at = None
    ma = ASK_H1_RE.search(html)
    if ma:
        mtm = ASK_TIME_RE.search(_text(ma.group(1)))
        asked_at = mtm.group(1) if mtm else None
    return {"question": question, "answer": answer, "asked_at": asked_at,
            "answered_at": answered_at, "dept": dept}


def harvest(fetch, *, limit: int | None = None, page_size: int = PAGE_SIZE,
            page_from: int | None = None) -> list[dict]:
    """翻页取列表，逐条取明细拿答复原文，返回统一记录。

    `fetch` 见 harvest.py 的 `_Fetcher`（可调用 = GET）。`limit` 为总条数上限。

    `page_from` = 起始页号（默认读环境变量 `GOVQA_PAGE_FROM`，再默认 1）。
    ⚠ 本源 **IP 级反爬很敏感**（约 30 个请求即 403）⇒ 分块要小：
        GOVQA_PAGE_FROM=1  ... --limit 500    # 每页 20 条 ⇒ 500 条 = 25 页
        GOVQA_PAGE_FROM=26 ... --limit 500    # 批间歇 ≥30 分钟
    """
    out: list[dict] = []
    page = page_from if page_from is not None else _env_page_from()
    total = None
    f403 = 0
    consec_fail = 0
    while True:
        if limit and len(out) >= limit:
            break
        r = fetch(LIST_API, params={"pageNo": page, "pageSize": page_size,
                                    "orderByFiled": "CRTIME"},
                  headers={"Referer": REFERER})
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停；本站 403 常为 IP 级反爬，需冷却）")
            break
        try:
            j = r.json()
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（{type(e).__name__}，停）")
            break
        rows = j.get("datas") or []
        if total is None:
            total = j.get("totalSize")
            print(f"    [{SITE['key']}] totalSize={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            qid = it.get("QUESTIONID") or it.get("id")
            if not qid:
                continue
            time.sleep(PAUSE)
            # ⚠ 明细请求必须兜异常：否则长跑中一条超时会让 harvest.py 整站丢弃、
            #   已收的全丢（2026-10-09 在 nat-tax 上踩过：跑 63 分钟后零产出）。
            try:
                d = fetch(DETAIL_API, params={"id": qid}, headers={"Referer": REFERER})
            except Exception as e:                                          # noqa: BLE001
                consec_fail += 1
                print(f"    [{SITE['key']}] 明细 {qid} {type(e).__name__}"
                      f"（连续失败 {consec_fail}/{MAX_CONSEC_FAIL}）")
                if consec_fail >= MAX_CONSEC_FAIL:
                    print(f"    [{SITE['key']}] 连续 {consec_fail} 次失败 ⇒ 熔断，"
                          f"返回已收 {len(out)} 条（下次续采）")
                    return out
                time.sleep(PAUSE * 3)
                continue
            consec_fail = 0
            code = getattr(d, "status_code", 0)
            if code == 403:
                f403 += 1
                print(f"    [{SITE['key']}] 明细 {qid} HTTP 403（连续第 {f403} 次）")
                if f403 >= MAX_403:
                    print(f"    [{SITE['key']}] 连续 {f403} 次 403 ⇒ 触发 IP 级反爬，熔断停止"
                          f"（已收 {len(out)} 条）。请冷却数十分钟后再跑。")
                    return out
                time.sleep(PAUSE * 3)
                continue
            if code != 200:
                print(f"    [{SITE['key']}] 明细 {qid} HTTP {code}（跳过）")
                continue
            f403 = 0
            info = _parse_detail(d.text or "")
            if len(info["answer"] or "") < 10:
                print(f"    [{SITE['key']}] {qid} 未取到答复正文（跳过）")
                continue
            out.append({
                "source": SITE["key"],
                "id": str(qid),
                "url": f"{DETAIL_API}?id={qid}",
                "question": info["question"] or _text(it.get("TITLE")),
                "answer": info["answer"],
                "asked_at": info["asked_at"],
                "answered_at": info["answered_at"],
                "dept": info["dept"],
                "channel": "留言咨询",
                "extra": {
                    "title": _text(it.get("TITLE")),
                    "zttpe": it.get("ZTTYPENAME"),
                    "crtime_ms": it.get("CRTIME"),
                    "pubtime_ms": it.get("PUBTIME"),
                    "platform": "mot-mapplys",
                },
            })
        if total is not None and page * page_size >= int(total):
            break
        page += 1
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
