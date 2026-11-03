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
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ncf = _load("ncf", "scripts/national-crawl-fetch.py")
ncs = _load("ncs", "scripts/national_crawl_common.py")

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
        no = DOCNO_RE.search(tail) or DOCNO_RE.search(txt[max(0, m.start() - 40):m.start()])
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


def crawl(site: str, index_url: str, max_issues: int, gap: float,
          args_year: str = "") -> dict:
    tr = ncf.default_transport()
    st, body = tr.fetch(index_url, timeout=30)
    if st != 200 or not isinstance(body, str):
        return {"site": site, "status": f"index_http_{st}", "items": 0}
    issues = issue_list(body, index_url, year=args_year or "")[:max_issues]
    if not issues:
        issues = [index_url]
    print(f"  {site}: 找到 {len(issues)} 期")
    allitems: list[dict] = []
    seen_keys: set[str] = set()
    for i, u in enumerate(issues, 1):
        try:
            st2, b2 = tr.fetch(u, timeout=30)
        except Exception as exc:                 # noqa: BLE001
            print(f"    {i}/{len(issues)} 失败 {type(exc).__name__}")
            continue
        if st2 != 200 or not isinstance(b2, str):
            print(f"    {i}/{len(issues)} http {st2}")
            continue
        got = []
        for x in parse_issue(b2, u, site):
            key = x.get("docno") or x.get("title")
            if key in seen_keys:
                continue
            seen_keys.add(key)
            got.append(x)
        allitems.extend(got)
        print(f"    {i}/{len(issues)} {len(got)} 条  {u[-32:]}")
        time.sleep(gap)
    if not allitems:
        return {"site": site, "status": "gazette_empty", "items": 0}
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
    r = crawl(args.site, index, args.max_issues, args.gap, args.year)
    print("结果:", json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
