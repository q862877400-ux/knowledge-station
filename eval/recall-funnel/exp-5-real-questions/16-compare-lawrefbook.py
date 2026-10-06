"""第 ② 步：把 LawRefBook 的 1,586 部法律 **与真库里那 386 篇法律/条例比对**，出一张"缺哪些"清单。

## 业主 2026-10-07 指示："要"（下载 + 比对出添补清单）

## 数据
`var/tmp/lawrefbook/laws.zip`（8,259,238 字节，sha256 `ef09fecc…`）：
 · **1,613 项 / 1,586 个 `.md` 法律全文** + 1 个 `.sqlite3` + 1 个 `.txt`
 · 文件名格式：`<法律名>(YYYY-MM-DD).md`（日期 = 发布日期），按法律部门分目录
 · ⚠ **zip 内文件名是 GBK/CP936 编码** ⇒ Python 默认按 CP437 解出乱码，需 `cp437→gbk` 回转

## 比对口径（要写清，别让人误读）
 · 真库侧取 **`standard_no` 不是 GB/GB·T/GB·Z 开头**的文档（即法律/条例/部门规章/公告那 386 篇）；
 · 名称归一化：去空格与全角括号差异、去「中华人民共和国」前缀、去版本年份；
 · 命中判据：**归一化后一方包含另一方**（长度 ≥ 4），并**分层报**（精确 / 包含 / 未命中）；
 · ⇒ 输出"**LawRefBook 有、我们库没有**"的清单（这才是添补清单），以及反向的。

只读真库；不写任何库内数据。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\16-compare-lawrefbook.py
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "lawrefbook-vs-library.json"
OUT_GAP = HERE / "gap-list-lawrefbook.txt"
ZIP = ROOT / "var" / "tmp" / "lawrefbook" / "laws.zip"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"


def fix(name: str) -> str:
    """zip 内文件名被 Python 按 CP437 解出来 ⇒ 还原成原始编码。

    ⚠ **我自己踩过的坑（2026-10-07）**：第一版写成 `cp437 → gbk`，**错**。
    文件名原始编码是 **UTF-8**（`σ«¬` = 字节 E5 AE AA = 「宪」的 UTF-8）。
    归错编码 ⇒ 一个名字都匹配不上 ⇒ 报出"1,585 部全都缺、0 部能对上"这种**荒唐数字**。
    正确顺序：先试 utf-8，不行再试 gbk，都不行就原样返回。
    """
    try:
        raw = name.encode("cp437")
    except UnicodeEncodeError:
        return name
    for enc in ("utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return name


def norm(s: str) -> str:
    s = re.sub(r"[\s（）()《》〈〉·・、,，.。\-—_/]", "", s or "")
    s = re.sub(r"^中华人民共和国", "", s)
    s = re.sub(r"（?\d{4}年?修订）?$", "", s)
    s = re.sub(r"\(?\d{4}-\d{2}-\d{2}\)?$", "", s)
    return s


def main() -> int:
    if not ZIP.exists():
        print(f"⛔ 没找到 {ZIP}（先跑 15-fetch-zip-retry.py）")
        return 1

    with zipfile.ZipFile(ZIP) as z:
        raw = z.namelist()
    # sqlite3 那个单独记
    odd = [n for n in raw if n.endswith((".sqlite3", ".txt"))]
    mds = [fix(n) for n in raw if n.endswith(".md")]
    laws = []
    for m in mds:
        base = Path(m).stem                       # 去掉 .md
        dept = Path(m).parent.name
        mm = re.match(r"^(.*?)\((\d{4}-\d{2}-\d{2})\)$", base)
        if mm:
            laws.append({"name": mm.group(1), "date": mm.group(2), "dept": dept})
        else:
            laws.append({"name": base, "date": None, "dept": dept})
    print(f"[cmp] LawRefBook：{len(mds)} 部法律；另有 {len(odd)} 个非 md：{[fix(o) for o in odd]}", flush=True)
    depts: dict[str, int] = {}
    for x in laws:
        depts[x["dept"]] = depts.get(x["dept"], 0) + 1
    print(f"[cmp] 法律部门分布：{depts}", flush=True)

    # 真库侧
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    rows = c.execute("SELECT standard_no, standard_name FROM doc_meta").fetchall()
    lib_all = [{"no": a or "", "name": b or ""} for a, b in rows]
    lib_law = [x for x in lib_all
               if not re.match(r"^\s*GB", x["no"], re.I)]
    print(f"[cmp] 真库：总计 {len(lib_all)} 篇；非 GB 系（法律/规章/公告）{len(lib_law)} 篇", flush=True)

    lib_norm = [(x, norm(x["name"]) or norm(x["no"])) for x in lib_law]
    lib_all_norm = [(x, norm(x["name"]) or norm(x["no"])) for x in lib_all]

    have, miss = [], []
    for L in laws:
        k = norm(L["name"])
        if len(k) < 4:
            continue
        hit = None
        for x, n in lib_norm:
            if n and (n == k or (len(k) >= 4 and (k in n or n in k))):
                hit = {"lib_no": x["no"], "lib_name": x["name"], "exact": n == k}
                break
        if hit is None:                      # 也看看 GB 系里有没有同名的（可能被标成标准）
            for x, n in lib_all_norm:
                if n and (n == k or (len(k) >= 4 and (k in n or n in k))):
                    hit = {"lib_no": x["no"], "lib_name": x["name"], "exact": n == k, "in_gb": True}
                    break
        (have if hit else miss).append({**L, "match": hit})

    print(f"\n[cmp] **LawRefBook 有、我们库能对上**：{len(have)} 部", flush=True)
    print(f"[cmp] **LawRefBook 有、我们库没有**：{len(miss)} 部", flush=True)

    # 反向：我们库有、LawRefBook 没有（也是有用信息）
    lk = {norm(L["name"]) for L in laws if len(norm(L["name"])) >= 4}
    rev_miss = []
    for x in lib_law:
        n = norm(x["name"]) or norm(x["no"])
        if len(n) < 4:
            continue
        if not any(n in k or k in n for k in lk):
            rev_miss.append(x)
    print(f"[cmp] 反向（我们库有、LawRefBook 没有）：{len(rev_miss)} 篇", flush=True)

    OUT.write_text(json.dumps({
        "why": "业主指示：下载 LawRefBook 数据并与真库比对，出添补清单",
        "source": {"repo": "RanKKI/LawRefBook", "file": "laws.zip",
                   "bytes": ZIP.stat().st_size,
                   "law_count": len(laws), "depts": depts,
                   "non_md": [fix(o) for o in odd],
                   "license_note": "仓库 SPDX=NOASSERTION；README 主张依《著作权法》第五条属公有领域"},
        "library": {"total_docs": len(lib_all), "non_gb_docs": len(lib_law)},
        "counts": {"lawrefbook_has_and_lib_matches": len(have),
                   "lawrefbook_has_but_lib_missing": len(miss),
                   "lib_has_but_lawrefbook_missing": len(rev_miss)},
        "missing_sample": [{"name": x["name"], "date": x["date"], "dept": x["dept"]} for x in miss[:120]],
        "matched_sample": [{"name": x["name"], "lib": x["match"]["lib_name"][:50]} for x in have[:20]],
        "reverse_missing_sample": [{"no": x["no"][:50], "name": x["name"][:60]} for x in rev_miss[:40]],
        "boundary": [
            "命中判据是**名称归一化后互相包含**，**不是逐条比对条文** ⇒ 只能说明『这部法律我们库里没有』，",
            "不能说明『条文内容一致』。同名不同版本（如历年修正）也只会各算一次。",
            "真库侧取『standard_no 非 GB 系』的文档；GB 系里同名者单独标 in_gb。",
        ],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# LawRefBook 有、我们库没有的法律（添补清单）", "",
             f"来源：RanKKI/LawRefBook `laws.zip`（{ZIP.stat().st_size/1e6:.2f} MB，"
             f"{len(laws)} 部法律）", f"我们库侧：非 GB 系文档 {len(lib_law)} 篇", "",
             f"**共 {len(miss)} 部**（下表按法律部门分组，最多 400 条）", ""]
    bym: dict[str, list] = {}
    for x in miss:
        bym.setdefault(x["dept"], []).append(x)
    for d, xs in sorted(bym.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"## {d}（{len(xs)} 部）")
        for x in xs[:400]:
            lines.append(f"- {x['name']}" + (f"　（{x['date']}）" if x["date"] else ""))
        lines.append("")
    OUT_GAP.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n[cmp] 缺的前 25 部：")
    for x in miss[:25]:
        print(f"     {x['dept']:12s} {x['name']}  ({x['date']})", flush=True)
    print(f"\n已写 {OUT}\n已写 {OUT_GAP}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
