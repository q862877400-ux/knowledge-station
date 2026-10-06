"""第 ② 步（**修正版**）：严格判据下，LawRefBook 与真库的差异。

## 为什么要重写（我自己踩的坑，留痕）
第一版判据是"**归一化后一方包含另一方**"。抽验发现大量**假命中**：
 · `最高人民法院关于适用《民法典》总则编若干问题的解释` 被判成"我们库有民法典"（**把司法解释当本体**）；
 · `对外使用国徽图案的办法` 被判成命中 `国徽`；
 · `突发事件应对法` 被判成命中 `应急管理部关于学习宣传贯彻…的通知`（**通知不是法律本体**）。
 ⇒ 于是"能对上 17 部"是**虚高**的，**那个数不能用**。

## 本版判据（严格，且把三种情况分开）
归一化 = 去空白/全角括号/书名号/标点 + 去前导「中华人民共和国」+ 去尾部版本标记（如 `(2021修正)`、`(2024-12-25)`）。
 · **A 有本体**：库里文档名归一化后 **完全等于** 法律名；
 · **B 只有通知/公告**：库里存在**包含**该法律名的**通知/公告/解读**类文档，但**没有本体**；
   ⇒ 这一档是**真实缺口**（用户问起来，库里给不出条文，只能给个通知）；
 · **C 完全没有**。

只读真库；不写库内数据。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\17-compare-strict.py
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
OUT = HERE / "lawrefbook-vs-library-strict.json"
OUT_GAP = HERE / "gap-list-strict.md"
ZIP = ROOT / "var" / "tmp" / "lawrefbook" / "laws.zip"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

#: 库里这些词出现在名字里 ⇒ 那是"通知/公告/解读"，**不是法规本体**
WRAPPER = ("通知", "公告", "解读", "答记者问", "征求意见", "公示", "学习宣传", "贯彻")


def fix(name: str) -> str:
    """zip 内文件名被按 CP437 解出 ⇒ 还原（原编码是 UTF-8；第一版误写成 gbk，见 16 脚本注释）。"""
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
    s = re.sub(r"（?\d{4}年?修正）?$", "", s)
    return s.strip()


def main() -> int:
    if not ZIP.exists():
        print(f"⛔ 没找到 {ZIP}")
        return 1
    with zipfile.ZipFile(ZIP) as z:
        names = [fix(n) for n in z.namelist() if n.endswith(".md")]
    laws = []
    for n in names:
        base, dept = Path(n).stem, Path(n).parent.name
        mm = re.match(r"^(.*?)\((\d{4}-\d{2}-\d{2})\)$", base)
        laws.append({"name": (mm.group(1) if mm else base),
                     "date": (mm.group(2) if mm else None), "dept": dept})
    seen, uniq = set(), []
    for L in laws:                                  # 同名多版本只留一份（列表里仍然算"有"）
        if L["name"] not in seen:
            seen.add(L["name"])
            uniq.append(L)
    print(f"[strict] LawRefBook：{len(laws)} 个文件 / **{len(uniq)} 部不同法规**", flush=True)

    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    lib = [{"no": a or "", "name": b or ""} for a, b in
           c.execute("SELECT standard_no, standard_name FROM doc_meta")]
    lib_n = [(x, norm(x["name"]) or norm(x["no"])) for x in lib]
    lib_gb = [x for x in lib if re.match(r"^\s*GB", x["no"], re.I)]
    lib_non = [x for x in lib if not re.match(r"^\s*GB", x["no"], re.I)]
    print(f"[strict] 真库：{len(lib)} 篇（GB 系 {len(lib_gb)}，非 GB 系 {len(lib_non)}）", flush=True)

    # 库里归一化名字的索引
    exact: dict[str, list] = {}
    for x, n in lib_n:
        if n:
            exact.setdefault(n, []).append(x)

    A, B, C = [], [], []
    for L in uniq:
        k = norm(L["name"])
        if len(k) < 3:
            continue
        if k in exact:
            # 本体在库里：但要排除"命中的那篇本身是通知"
            body = [x for x in exact[k] if not any(w in x["name"] for w in WRAPPER)]
            if body:
                A.append({**L, "lib": body[0]})
                continue
        wrap = [x for x, n in lib_n
                if n and k in n and any(w in x["name"] for w in WRAPPER)]
        (B if wrap else C).append({**L, **({"wrap": wrap[0]["name"]} if wrap else {})})

    print(f"\n[strict] **A 库里有本体**：{len(A)} 部", flush=True)
    print(f"[strict] **B 库里只有通知/公告、没有本体**：{len(B)} 部", flush=True)
    print(f"[strict] **C 库里完全没有**：{len(C)} 部", flush=True)

    dept_gap: dict[str, int] = {}
    for x in B + C:
        dept_gap[x["dept"]] = dept_gap.get(x["dept"], 0) + 1

    OUT.write_text(json.dumps({
        "why": "业主指示：下载 LawRefBook 与真库比对出添补清单（**修正版：严格判据**）",
        "correction": ("第一版判据（互相包含）产生大量**假命中**（把司法解释当民法典本体、把'国徽'当命中、"
                       "把通知当法律本体）⇒ '能对上 17 部'虚高、不可用。本版改为："
                       "本体=归一化完全相等且非通知类；只有通知单列一档。"),
        "source": {"repo": "RanKKI/LawRefBook", "zip_md_files": len(names),
                   "distinct_laws": len(uniq), "license_note": "SPDX=NOASSERTION；README 主张依著作权法第五条公有领域"},
        "library": {"total": len(lib), "gb_family": len(lib_gb), "non_gb": len(lib_non)},
        "counts": {"A_lib_has_body": len(A), "B_lib_only_notice": len(B), "C_lib_none": len(C)},
        "gap_by_dept": dict(sorted(dept_gap.items(), key=lambda kv: -kv[1])),
        "A_sample": [{"name": x["name"], "lib": x["lib"]["name"][:40]} for x in A[:20]],
        "B_sample": [{"name": x["name"], "wrap": (x.get("wrap") or "")[:60]} for x in B[:20]],
        "C_sample": [{"name": x["name"], "dept": x["dept"]} for x in C[:30]],
        "boundary": [
            "判据是**名称层面**的（严格相等 / 通知类包含），**不是逐条比对条文** ⇒ 只说『这部法规有没有』，",
            "不说『内容是否一致』；同名不同版本只算一次。",
            "真库侧含 GB 系文档（同名者会被算作 A）。",
        ],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# LawRefBook × 我们库 —— 法规层添补清单（严格判据）", "",
             f"来源：`RanKKI/LawRefBook` 的 `laws.zip`（**{len(uniq)} 部不同法规**，{len(names)} 个文件）",
             f"我们库：{len(lib)} 篇，其中国标（GB 系）{len(lib_gb)} 篇、非国标 {len(lib_non)} 篇", "",
             "| 档 | 含义 | 部数 |", "|---|---|---|",
             f"| **A** | 库里**有本体** | **{len(A)}** |",
             f"| **B** | 库里**只有通知/公告，没有本体** | **{len(B)}** |",
             f"| **C** | 库里**完全没有** | **{len(C)}** |", "",
             f"⇒ **需要补的 = B + C = {len(B) + len(C)} 部**", "", "## 按类别（B+C）", ""]
    for d, n in sorted(dept_gap.items(), key=lambda kv: -kv[1]):
        lines.append(f"- {d}：{n} 部")
    lines += ["", "## B 档：库里只有通知、没有本体（用户问起来答不出条文）", ""]
    for x in B:
        lines.append(f"- {x['name']}　（库里现有：{(x.get('wrap') or '')[:50]}）")
    lines += ["", "## C 档：完全没有（前 300 部）", ""]
    for x in C[:300]:
        lines.append(f"- [{x['dept']}] {x['name']}")
    OUT_GAP.write_text("\n".join(lines), encoding="utf-8")

    print("\n[strict] A 档前 12：")
    for x in A[:12]:
        print(f"     {x['name']}  ←→  {x['lib']['name'][:44]}", flush=True)
    print("\n[strict] B 档前 8：")
    for x in B[:8]:
        print(f"     {x['name']}  （库里只有：{(x.get('wrap') or '')[:44]}）", flush=True)
    print(f"\n已写 {OUT}\n已写 {OUT_GAP}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
