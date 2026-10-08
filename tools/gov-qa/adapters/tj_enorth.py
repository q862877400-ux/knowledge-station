"""适配器：**天津市·政民零距离**（北方网 enorth 平台，55 部门/区县）。

## 站点形态（2026-10-08 实探，证据 recon/tj-enorth-api.txt、recon/tj-enorth-depts.json）

· 平台＝北方网民生频道「政民零距离」`http://ms.enorth.com.cn/zmljl/`（天津官方网络问政），
  后端＝津云网上问政中心 `zw.enorth.com.cn/gov_open/`。
  ⚠ **与 `tj-hdjl`（天津门户 www.tj.gov.cn/zmhd）不是一回事**：tj-hdjl 是门户自采的
  「留言选登」（约 500 条），本适配器走的是**问政平台全量**（63 万条量级），两者可能部分重叠。

· 列表（HTML 表格，gb2312，非 JSON）：
  `GET http://zw.enorth.com.cn/gov_open/question/zero/list9a.jsp?deptId=<id>&curpage=<p>&rows=<n>`
  每行 `[类别] 标题(链接) 日期 已回复/未超时`；页内含「共 N 条记录 第 X/Y 页」。
  翻页实测 curpage 1/2/3 两两 0 重叠 ⇒ 翻页正确。

· 明细（静态 HTML，gb2312，**无需 cookie / Referer**）：
  `GET https://zw.enorth.com.cn/gov_open/<id>.html`
  结构：`<div class="block-q">`（问 题：发表人/提问时间/标题/正文）
      + `<div class="block-q block-a">`（反 馈：回复部门/回复时间/答复正文）。

## ★ 采量与 id 连续性（为什么必须走分页、不能区间扫）

· 明细 id **全站稀疏且非单调**（100000→200、4700000→404、4752000→200）⇒ **禁止区间扫**，
  只能从 `list9a.jsp` 分页拿 id。
· 列表页**不含答复正文** ⇒ 必须逐条抓明细。630,595 条 × 1.5s ≈ 263 小时，
  **全量不可行，也不该这么压一个政府站** ⇒ 用 `TJ_ENORTH_DEPTS` / `TJ_ENORTH_CAP` 逐部门限量跑。

## 环境变量（逐部门限量跑的关键）

· `TJ_ENORTH_DEPTS`：逗号分隔的 deptId 白名单；**空 = 全部 55 个**。
· `TJ_ENORTH_CAP`：**每个 dept** 最多取多少条；**0 = 不限**（默认）。
  两者都不设时行为合理：全 dept、不限量（供 `--list` 与抽验用；真跑全量请务必设 CAP）。
"""
from __future__ import annotations

import os
import re
import time

SITE = {
    "key": "tj-enorth",
    "name": "天津市·政民零距离",
    "kind": "static",
    "level": "province",
    "entry": "http://ms.enorth.com.cn/zmljl/",
    "status": "ok",
    "note": "北方网 enorth 问政平台（zw.enorth.com.cn/gov_open），55 部门/区县 / 63 万条；"
            "列表 list9a.jsp 分页 + 逐条明细（无需 cookie/Referer）；"
            "明细 id 不连续，禁止区间扫；用 TJ_ENORTH_DEPTS/TJ_ENORTH_CAP 逐部门限量跑",
}

LIST_URL = "http://zw.enorth.com.cn/gov_open/question/zero/list9a.jsp"
LIST_TPL = LIST_URL + "?deptId={dept}&curpage={page}&rows={rows}"
DETAIL_TPL = "https://zw.enorth.com.cn/gov_open/{id}.html"

PAUSE = 1.5
PAGE_SIZE = 100          # 实测 rows=100 返回 100 条
MAX_PAGES = 2000         # 单 dept 最多翻多少页（62013 条 / 100 ≈ 621 页，留足余量）

#: 55 个部门/区县（deptId 非连续，取自 ms.enorth.com.cn/zmljl/{quxian|bumen}/<slug>/ 内嵌 iframe）。
#: 见 recon/tj-enorth-depts.json（含各自 total）。数字会随时间增长，采集时以接口为准。
DEPTS = [
    # —— 区县 16（total 合计 398,742）——
    {"kind": "quxian", "slug": "binhai", "dept_id": "1002040000000000"},
    {"kind": "quxian", "slug": "heping", "dept_id": "1002001000000000"},
    {"kind": "quxian", "slug": "hebei", "dept_id": "1002004000000000"},
    {"kind": "quxian", "slug": "hexi", "dept_id": "1002003000000000"},
    {"kind": "quxian", "slug": "hedong", "dept_id": "1002002000000000"},
    {"kind": "quxian", "slug": "nankai", "dept_id": "1002005000000000"},
    {"kind": "quxian", "slug": "hongqiao", "dept_id": "1002006000000000"},
    {"kind": "quxian", "slug": "dongli", "dept_id": "1002010000000000"},
    {"kind": "quxian", "slug": "xiqing", "dept_id": "1002011000000000"},
    {"kind": "quxian", "slug": "jinnan", "dept_id": "1002012000000000"},
    {"kind": "quxian", "slug": "beichen", "dept_id": "1002013000000000"},
    {"kind": "quxian", "slug": "wuqing", "dept_id": "1002014000000000"},
    {"kind": "quxian", "slug": "baodi", "dept_id": "1002015000000000"},
    {"kind": "quxian", "slug": "jinghai", "dept_id": "1002017000000000"},
    {"kind": "quxian", "slug": "ninghe", "dept_id": "1002018000000000"},
    {"kind": "quxian", "slug": "jixian", "dept_id": "1002016000000000"},
    # —— 部门 39（total 合计 231,853）——
    {"kind": "bumen", "slug": "fagaiwei", "dept_id": "1001019000000000"},
    {"kind": "bumen", "slug": "jiaowei", "dept_id": "1001022000000000"},
    {"kind": "bumen", "slug": "kewei", "dept_id": "1001007000000000"},
    {"kind": "bumen", "slug": "jingxin", "dept_id": "1001020000000000"},
    {"kind": "bumen", "slug": "mzzjw", "dept_id": "1001003000000000"},
    {"kind": "bumen", "slug": "gongan", "dept_id": "1001023000000000"},
    {"kind": "bumen", "slug": "minzheng", "dept_id": "1001024000000000"},
    {"kind": "bumen", "slug": "sifaju", "dept_id": "1001004000000000"},
    {"kind": "bumen", "slug": "caizhengju", "dept_id": "1001005000000000"},
    {"kind": "bumen", "slug": "shebao", "dept_id": "1001025000000000"},
    {"kind": "bumen", "slug": "guihua", "dept_id": "1001034000000000"},
    {"kind": "bumen", "slug": "huanbao", "dept_id": "1001028000000000"},
    {"kind": "bumen", "slug": "jiaotong", "dept_id": "1001027000000000"},
    {"kind": "bumen", "slug": "shirong", "dept_id": "1001029000000000"},
    {"kind": "bumen", "slug": "gangkou", "dept_id": "1001038000000000"},
    {"kind": "bumen", "slug": "shuiwu", "dept_id": "1001031000000000"},
    {"kind": "bumen", "slug": "nongwei", "dept_id": "1001030000000000"},
    {"kind": "bumen", "slug": "shangwu", "dept_id": "1001021000000000"},
    {"kind": "bumen", "slug": "wenguang", "dept_id": "1001032000000000"},
    {"kind": "bumen", "slug": "weiji", "dept_id": "1001002000000000"},
    {"kind": "bumen", "slug": "tyjrju", "dept_id": "1001006000000000"},
    {"kind": "bumen", "slug": "yingjiju", "dept_id": "1001008000000000"},
    {"kind": "bumen", "slug": "shenjiju", "dept_id": "1001010000000000"},
    {"kind": "bumen", "slug": "waiban", "dept_id": "1001011000000000"},
    {"kind": "bumen", "slug": "shichang", "dept_id": "1001001000000000"},
    {"kind": "bumen", "slug": "guoziwei", "dept_id": "1001012000000000"},
    {"kind": "bumen", "slug": "tiyu", "dept_id": "1001060000000000"},
    {"kind": "bumen", "slug": "tongjiju", "dept_id": "1001013000000000"},
    {"kind": "bumen", "slug": "hzjlban", "dept_id": "1001017000000000"},
    {"kind": "bumen", "slug": "yibaoju", "dept_id": "1001014000000000"},
    {"kind": "bumen", "slug": "jgswju", "dept_id": "1001015000000000"},
    {"kind": "bumen", "slug": "renfangban", "dept_id": "1001016000000000"},
    {"kind": "bumen", "slug": "zwfwban", "dept_id": "1001018000000000"},
    {"kind": "bumen", "slug": "zscqj", "dept_id": "1001040000000000"},
    {"kind": "bumen", "slug": "liangshiju", "dept_id": "1001037000000000"},
    {"kind": "bumen", "slug": "jinrong", "dept_id": "1001061000000000"},
    {"kind": "bumen", "slug": "xiaofang", "dept_id": "1001041000000000"},
    {"kind": "bumen", "slug": "tjsw", "dept_id": "1001043000000000"},
    {"kind": "bumen", "slug": "tongxinguanli", "dept_id": "1001065000000000"},
    {"kind": "bumen", "slug": "gongjijin", "dept_id": "1001063000000000"},
]

# ---- 解析正则（列表页 / 明细页）----
ROW_RE = re.compile(r"<tr\b.*?</tr>", re.S | re.I)
LINK_RE = re.compile(r'<a\s+href="(https://zw\.enorth\.com\.cn/gov_open/(\d+)\.html)"[^>]*>(.*?)</a>',
                     re.S | re.I)
DATE_RE = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2}(?:\s+[0-9]{2}:[0-9]{2})?)")
TOTAL_RE = re.compile(r"共\s*([0-9]+)\s*条记录")
PAGE_RE = re.compile(r"第\s*([0-9]+)\s*/\s*([0-9]+)\s*页")
REPLIED_MARK = "已回复"

H5_RE = re.compile(r'<h5><span class="f-bold">标题：</span>(.*?)</h5>', re.S)
ASKER_RE = re.compile(r'发表人：</span>\s*([^<]+?)\s*</span>', re.S)
ASKTIME_RE = re.compile(r'提问时间：</span>\s*([0-9]{4}-[0-9]{2}-[0-9]{2}[^<]*)')
DEPT_RE = re.compile(r'回复部门：</span>\s*(?:<a[^>]*>)?([^<]+)')
REPTIME_RE = re.compile(r'回复时间：</span>\s*([0-9]{4}-[0-9]{2}-[0-9]{2}[^<]*)')
CONTENT_RE = re.compile(r"<span class='content'>(.*?)</span>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
ANS_MARK = "icon-answer"        # 反馈块标记：其前为问题块、其后为答复块


def _dec(resp) -> str:
    """gb2312 解码（该站 Content-Type 为 GBK，但历史页可能混杂；逐级回退）。"""
    raw = getattr(resp, "content", b"") or b""
    for enc in ("gb2312", "gbk", "utf-8"):
        try:
            return raw.decode(enc)
        except Exception:                                                   # noqa: BLE001
            continue
    return raw.decode("utf-8", "replace")


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _parse_list(html: str) -> list[dict]:
    """从 list9a.jsp 表格里取每行：明细 URL / id / 标题 / 日期 / 是否已回复。"""
    rows = []
    for tr in ROW_RE.findall(html):
        m = LINK_RE.search(tr)
        if not m:
            continue
        url, mid, title = m.group(1), m.group(2), _text(m.group(3))
        dm = DATE_RE.search(tr)
        rows.append({
            "url": url,
            "id": mid,
            "title": title,
            "date": dm.group(1) if dm else None,
            "answered": REPLIED_MARK in tr,
        })
    return rows


def _parse_detail(html: str, fallback_title: str = "") -> dict | None:
    """从明细页取 问题/答复/发表人/提问时间/回复部门/回复时间。"""
    i = html.find(ANS_MARK)
    q_html, a_html = (html[:i], html[i:]) if i >= 0 else (html, "")

    q = ""
    for c in CONTENT_RE.findall(q_html):
        t = _text(c)
        if len(t) > len(q):
            q = t
    a = ""
    for c in CONTENT_RE.findall(a_html):
        t = _text(c)
        if len(t) > len(a):
            a = t

    tm = H5_RE.search(html)
    title = _text(tm.group(1)) if tm else (fallback_title or "")
    if not q:
        q = title
    if len(q) < 4 or len(a) < 10:            # 无答复 → 丢弃
        return None

    asker = ASKER_RE.search(q_html)
    askt = ASKTIME_RE.search(q_html)
    dept = DEPT_RE.search(a_html)
    rept = REPTIME_RE.search(a_html)
    return {
        "question": q,
        "answer": a,
        "asked_at": askt.group(1).strip() if askt else None,
        "answered_at": rept.group(1).strip() if rept else None,
        "dept": dept.group(1).strip() if dept else None,
        "asker": asker.group(1).strip() if asker else None,
        "title": title,
    }


def _selected_depts() -> list[dict]:
    """按 TJ_ENORTH_DEPTS 过滤（空 = 全部 55 个）。"""
    want = {x.strip() for x in os.environ.get("TJ_ENORTH_DEPTS", "").split(",") if x.strip()}
    if not want:
        return list(DEPTS)
    return [d for d in DEPTS if d["dept_id"] in want]


def _cap() -> int:
    try:
        return max(0, int(os.environ.get("TJ_ENORTH_CAP", "0") or "0"))
    except ValueError:
        return 0


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """逐部门翻列表 + 逐条抓明细，取「已回复」问答。

    · `limit`：**跨 dept 总条数**上限（`harvest.py --limit` 传入）。
    · `TJ_ENORTH_CAP`：**每 dept** 上限（到了就换下一个 dept）。
    · `TJ_ENORTH_DEPTS`：限定要跑的 deptId（空 = 全部）。
    """
    depts = _selected_depts()
    cap = _cap()
    out: list[dict] = []
    print(f"    [{SITE['key']}] dept {len(depts)} 个，每 dept 上限 "
          f"{cap or '∞'}，总上限 {limit or '∞'}")

    for d in depts:
        if limit and len(out) >= limit:
            break
        did, slug = d["dept_id"], d["slug"]
        sub_key = f"{SITE['key']}-{slug}"
        take = 0
        total = None
        for page in range(1, MAX_PAGES + 1):
            if limit and len(out) >= limit:
                break
            if cap and take >= cap:
                break
            time.sleep(PAUSE)
            r = fetch(LIST_TPL.format(dept=did, page=page, rows=PAGE_SIZE))
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{sub_key}] 列表第 {page} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（停）")
                break
            html = _dec(r)
            if total is None:
                mt = TOTAL_RE.search(html)
                total = int(mt.group(1)) if mt else None
            rows = _parse_list(html)
            if not rows:
                break
            mp = PAGE_RE.search(html)
            last = (mp and int(mp.group(1)) >= int(mp.group(2)))
            answered = [x for x in rows if x["answered"]]
            print(f"    [{sub_key}] 第 {page} 页：{len(rows)} 条（已回复 {len(answered)}）")
            if not answered and last:
                break
            for it in answered:
                if limit and len(out) >= limit:
                    break
                if cap and take >= cap:
                    break
                time.sleep(PAUSE)
                dr = fetch(it["url"])
                if getattr(dr, "status_code", 0) != 200:
                    continue
                rec = _parse_detail(_dec(dr), it["title"])
                if not rec:
                    continue
                out.append({
                    "source": sub_key,
                    "id": it["id"],
                    "url": it["url"],
                    "question": rec["question"],
                    "answer": rec["answer"],
                    "asked_at": rec["asked_at"] or it["date"],
                    "answered_at": rec["answered_at"],
                    "dept": rec["dept"],
                    "channel": f"政民零距离·{slug}",
                    "extra": {
                        "title": rec["title"],
                        "asker": rec["asker"],
                        "dept_kind": d["kind"],
                        "dept_id": did,
                        "dept_slug": slug,
                        "dept_total": total,
                        "answer_kind": "办理答复（政民零距离）",
                    },
                })
                take += 1
            if last:
                break
        print(f"    [{sub_key}] 收 {take} 条（dept 总 {total}）")

    print(f"    [{SITE['key']}] 合计收 {len(out)} 条")
    return out
