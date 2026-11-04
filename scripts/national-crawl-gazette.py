"""抓「政府公报」里刊登的规范性文件（2026-11-02）。

## 为什么单独做一条线

实测（R68）：山西、贵州、福建等省的规范性文件**不在列表页里**，而在**政府公报**中：
省公报把省政府令、省政府文件、省政府办公厅文件按期集中刊登。
这些站既没有"文件列表"，也没有可跟的分页链接 —— 静态与 CDP 都抽不出条目。

## 做法

1. 从公报**年目录**枚举各期（山西：`/zfcbw/zfgb2/2025nzfgb_*/dNq_*/`）；
2. 每期抓正文，用**标题 + 文号**正则切出文件：
   标题（以"XX省人民政府…"开头，含 关于/印发/公布 等）+ 文号（如 `晋政办发〔2024〕58号`）；
3. 按口径过滤：只要规范性文件（办法/规定/条例/细则/决定/通知/意见…），
   **任免、表彰、会议、批复征地类一律丢**（任免在公报里占比很大）；
4. 条目落库：`url = 该期地址#doc序号`，`date = 文号年份-月` 或期号日期，
   正文指向该期正文（整期共享一份，避免重复落盘）。

## 用法

    .venv\\Scripts\\python.exe scripts/national-crawl-gazette.py --site 山西省 --max-issues 20
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


sys.path.insert(0, str(ROOT / "scripts"))
ncs = __import__("national_crawl_common")      # 公用件（加载器/合并存库）
ncf = ncs.load_script("ncf", "scripts/national-crawl-fetch.py")

#: 文号格式：晋政办发〔2024〕58号 / 黔府发〔2024〕3号 / 闽政〔2018〕86号
DOCNO_RE = re.compile(r"([\u4e00-\u9fa5]{2,10}〔\d{4}〕\s*\d+\s*号)")
#: 标题：以省名开头，含公文体裁词
TITLE_RE = re.compile(
    r"([\u4e00-\u9fa5]{2,12}(?:省|自治区|市)人民政府(?:办公厅)?"
    r"[\u4e00-\u9fa5、，（）()《》“”\-—0-9]{6,80}?"
    r"(?:通知|办法|规定|条例|细则|决定|意见|批复|通告|公告|规则|方案|规划))")
#: 这些是人事/事务类，公报里占比大，必须丢
DROP = ("任免", "免职", "任职", "表彰", "名单", "会议纪要", "慰问", "座谈")


def issue_list(index_html: str, base: str, year: str = "") -> list[str]:
    """抽出各期地址。

    ⚠ 实测（2026-11-02）：山西省的"年目录"页只回 393 字节空壳，
    真正的期号清单**藏在每一期页面底部的档案导航里**（一期页面链到 355 个其它期）。
    ⇒ 从任意一期出发都能拿到全库期号；这里同时兼容"年目录"与"任意一期"两种入口。
    """
    urls: list[str] = []
    for m in re.finditer(r'href="([^"]*?d\d+q_\d+/?/?)"', index_html,
                         re.IGNORECASE):
        u = ncf.urljoin(base, m.group(1))
        if year and year not in u:
            continue
        if u.rstrip("/") == base.rstrip("/"):
            continue
        if u not in urls:
            urls.append(u)
    urls.sort(key=lambda x: int(mm.group(1))
              if (mm := re.search(r"d(\d+)q_", x)) else 0)
    return urls


def parse_link_list(html: str, url: str, province: str) -> list[dict]:
    """从「链接列表页」切条目：锚文本里带标题 + 文号（如贵州省的 `qfh` 栏目）。

    ⚠ 为什么需要它（2026-11-02）：贵州省的规范性文件页是**普通链接列表**，
    `parse_items()` 一条也抽不出（它认的是"列表项 + 同行日期"的结构），
    但锚文本里就有完整标题和文号 ⇒ 直接按锚文本切。
    """
    items: list[dict] = []
    seen: set[str] = set()
    for m in ncf.LINK_RE.finditer(html):
        href, inner = m.group(1), m.group(2)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        if len(text) < 12:
            continue
        no = DOCNO_RE.search(text)
        title = DOCNO_RE.split(text)[0].strip(" （(")
        if no:
            title = title.replace(no.group(1), "").strip(" （(")
        if len(title) < 10 or not ncf.is_title(title):
            continue
        if any(w in title for w in DROP):
            continue
        key = no.group(1) if no else title
        if key in seen:
            continue
        seen.add(key)
        year = re.search(r"〔(\d{4})〕", no.group(1)) if no else None
        items.append({
            "title": title, "url": ncf.urljoin(url, href),
            "date": f"{year.group(1)}-01" if year else None,
            "docno": no.group(1) if no else "", "source": province,
        })
    return items


def issue_date(txt: str) -> str | None:
    """取该期出版日期。

    ⚠ 只在**页头前 2500 字**里找：整页里第一个日期常是导航里的无关日期
    （实测把 2025 年的期判成了 2026 年）。
    """
    head = txt[:2500]
    m = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*出版", head)
    if not m:
        m = re.search(r"(20\d{2})[-年.](\d{1,2})[-月.](\d{1,2})", head)
    if not m:
        return None
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def parse_issue(html: str, url: str, province: str) -> list[dict]:
    """从一期公报正文里切出文件条目（同期内按文号去重）。"""
    txt = ncf.main_text(html)
    pub = issue_date(txt)
    items: list[dict] = []
    seen: set[str] = set()
    for i, m in enumerate(TITLE_RE.finditer(txt)):
        title = m.group(1).strip()
        if any(w in title for w in DROP):
            continue
        tail = txt[m.end(): m.end() + 40]
        near = txt[max(0, m.start() - 40):m.start()]
        no = DOCNO_RE.search(tail) or DOCNO_RE.search(near)
        docno = no.group(1) if no else ""
        key = docno or title
        if key in seen:
            continue
        seen.add(key)
        year = re.search(r"〔(\d{4})〕", docno)
        date = pub or (f"{year.group(1)}-01" if year else None)
        if not ncf.is_title(title):
            continue
        items.append({
            "title": title, "url": f"{url}#doc{i}", "date": date,
            "docno": docno, "source": province, "issue": url,
        })
    return items


def save_issue_text(url: str, html: str) -> str:
    """把**整期正文**落成一份 txt，返回相对仓根的路径。

    公报一期里有 5~11 条文件，逐条落会把同一份正文重复写 10 次（实测浪费 10 倍磁盘）。
    条目通过 `text_file` 指到这份整期正文；再按 `docno` 去正文里定位自己那一段。
    """
    import hashlib
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    out = ROOT / "var" / "data" / "national" / "gazette-text"
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{key}.txt"
    if not f.exists():
        f.write_text(ncf.clean_body(ncf.main_text(html), ""), encoding="utf-8")
    return str(f.relative_to(ROOT))



def fill_detail_texts(items: list[dict], gap: float = 1.0) -> int:
    """给「链接列表」条目逐条抓详情页正文（列表页不是正文）。

    ⚠ 实测（2026-11-03）：R70 把列表页 HTML 当成整期正文存了 —— 里面是
    天气预报脚本和一堆导航链接，**根本不是文件正文**。公报期页这样做还勉强
    （整期页面确实含全部文件正文），但链接列表页必须逐条进详情页。
    """
    tr = ncf.default_transport()
    out = ROOT / "var" / "data" / "national" / "gazette-text"
    out.mkdir(parents=True, exist_ok=True)
    filled = 0
    for x in items:
        if not x.get("url") or "#doc" in x["url"]:
            continue
        try:
            st, body = tr.fetch(x["url"], timeout=30)
        except Exception as exc:                 # noqa: BLE001
            print(f"    详情失败 {type(exc).__name__}")
            continue
        if st != 200 or not isinstance(body, str):
            continue
        txt = ncf.clean_body(ncf.main_text(body), x.get("title") or "")
        if len(txt) < 80:
            continue
        import hashlib
        key = hashlib.sha256(x["url"].encode()).hexdigest()[:16]
        f = out / f"detail-{key}.txt"
        f.write_text(txt, encoding="utf-8")
        x["text_file"] = str(f.relative_to(ROOT))
        x["text_chars"] = len(txt)
        filled += 1
        time.sleep(gap)
    return filled


def crawl(site: str, index_url: str, max_issues: int, gap: float,
          args_year: str = "", cdp_port: int = 0) -> dict:
    tr = ncf.default_transport()

    def get(u: str):
        """静态取页；`--cdp` 时用浏览器渲染后再取（脚本空壳页用）。"""
        if not cdp_port:
            return tr.fetch(u, timeout=30)
        nb = ncs.load_script("nb", "scripts/national-crawl-browser.py")
        page = nb.CDPPage(cdp_port)
        try:
            page.open(u)
            html = ""
            deadline = time.time() + 18
            while time.time() < deadline:
                h = page.html()
                if h and len(h) > 3000:
                    html = h
                    # ⚠ 只等 HTML 够大是不够的：吉林这类站在 5 秒后才有列表，
                    # 提前退出会拿到 5 万字节的空壳（实测诊断脚本等"能解析出条目"
                    # 拿到 13 条，这里只等长度拿到 0 条）。
                    if (parse_issue(h, u, site) or
                            parse_link_list(h, u, site)):
                        break
                time.sleep(1.0)
            return (200 if html else 0), html
        finally:
            page.close()

    proc = None
    if cdp_port:
        nb = ncs.load_script("nb", "scripts/national-crawl-browser.py")
        proc = nb.start_debug_browser(ncs.find_browser(), cdp_port)
        if not nb.wait_debug_port(cdp_port):
            return {"site": site, "status": "cdp_port_failed", "items": 0}
    try:
        return _crawl_pages(site, index_url, max_issues, gap, args_year, get)
    finally:
        if proc is not None:
            proc.terminate()


def _crawl_pages(site, index_url, max_issues, gap, args_year, get) -> dict:
    st, body = get(index_url)
    if st != 200 or not isinstance(body, str):
        return {"site": site, "status": f"index_http_{st}", "items": 0}
    issues = issue_list(body, index_url, year=args_year or "")[:max_issues]
    if not issues:
        issues = [index_url]
    # 政府 CMS 常用 `createPageHTML('page-div',50,1,'common_listfgwj','shtml')`
    # 把总页数写在页面脚本里（实测新疆 50 页、贵州 177 页都是这套）。
    # 抽出来后按 `stem_N.ext` 规则生成后续页，避免一页页手传地址。
    m = re.search(
        r"createPageHTML\([^,]+,\s*(\d+)\s*,\s*\d+\s*,\s*'([^']+)'\s*,\s*'([^']+)'",
        body)
    if m and len(issues) < max_issues:
        total, stem, ext = int(m.group(1)), m.group(2), m.group(3)
        host = ncf.urlsplit(index_url)
        prefix = f"{host.scheme}://{host.netloc}{ncf.urlsplit(index_url).path.rsplit('/', 1)[0]}/"
        for p in range(2, min(total, max_issues) + 1):
            u = f"{prefix}{stem}_{p}.{ext}"
            if u not in issues:
                issues.append(u)
        print(f"  分页脚本：共 {total} 页，本轮取 {len(issues)} 页")
    print(f"  {site}: 共 {len(issues)} 页/期")
    allitems: list[dict] = []
    seen_keys: set[str] = set()
    for i, u in enumerate(issues, 1):
        try:
            st2, b2 = get(u)
        except Exception as exc:                 # noqa: BLE001
            print(f"    {i}/{len(issues)} 失败 {type(exc).__name__}")
            continue
        if st2 != 200 or not isinstance(b2, str):
            print(f"    {i}/{len(issues)} http {st2}")
            continue
        got = []
        # 两种结构都在时取**条数多的**：实测福建省 `parse_issue` 只切出 2 条、
        # `parse_link_list` 切出 13 条，固定优先会把 11 条丢掉。
        a = parse_issue(b2, u, site)
        b = parse_link_list(b2, u, site)
        parsed = a if len(a) >= len(b) else b
        for x in parsed:
            key = x.get("docno") or x.get("title")
            if key in seen_keys:
                continue
            seen_keys.add(key)
            got.append(x)
        # 公报期页：整期正文存一份，条目指过去
        if got and got[0].get("issue"):
            tf = save_issue_text(u, b2)
            for x in got:
                x["text_file"] = tf
                x["text_chars"] = len(ncf.main_text(b2))
        allitems.extend(got)
        print(f"    {i}/{len(issues)} {len(got)} 条  {u[-32:]}")
        time.sleep(gap)
    if not allitems:
        return {"site": site, "status": "gazette_empty", "items": 0}
    need = [x for x in allitems if not x.get("text_file")]
    filled = fill_detail_texts(need, gap) if need else 0
    print(f"  详情页补正文：{filled}/{len(need)}")
    res = ncs.merge_and_save(site, index_url, allitems, engine="gazette")
    return {"site": site, "status": "gazette_ok", "items": len(allitems),
            "total": res["items_total"], "new": res["items_new"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--index", default="")
    ap.add_argument("--max-issues", type=int, default=12)
    ap.add_argument("--gap", type=float, default=1.0)
    ap.add_argument("--year", default="", help="只处理含该年份的期")
    ap.add_argument("--cdp", type=int, default=0,
                    help="用浏览器渲染取页（脚本空壳站），值为调试端口")
    args = ap.parse_args()
    index = args.index
    if not index:
        disc = json.loads(
            (ROOT / "docs" / "channels" / "data" / "national-discover.json")
            .read_text(encoding="utf-8"))["results"]
        rec = next((r for r in disc if r["site"] == args.site), None)
        index = (rec or {}).get("board_url") or ""
    if not index:
        print("没有公报目录地址")
        return 1
    print(f"公报目录：{index}")
    r = crawl(args.site, index, args.max_issues, args.gap, args.year,
              cdp_port=args.cdp)
    print("结果:", json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
