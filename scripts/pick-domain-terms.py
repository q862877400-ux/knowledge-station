"""从本机知识库里**机械**抽出「跨领域的专业术语」清单，给"大白话↔行话"那道翻译用。

用途：产出提示词 A 的输入（让模型写"不懂这行的人会怎么说"）。选法全机械、不手挑，
任何人重跑都能得到同一份。

命令：
    .venv\\Scripts\\python.exe scripts\\pick-domain-terms.py
    # 真库路径是本机固定值（换机器要改 DB）；只读，不动真库。

四个判据（每一个都试过；错过的版本见文末留痕）：
  1. **形态**：术语条目的写法是「编号 中文名 英文名 中文定义」——中文串后紧跟英文名、
     英文名后**必须紧跟中文**。这一条能自然排除 "标签应符合 GB/T 1234 的规定"
     这类（GB 后面是 / 不是中文）。
  2. **够重要**：被 ≥3 篇**不同文件**正式定义过。
  3. **是行话不是泛词**（一）：落在 ≤2 个 CCS 大类里。横跨十几个大类的（如「资源」）是通用词。
  4. **是行话不是泛词**（二）：`正式定义它的文件数 ÷ 它在库里的命中条数` ≥ 1/12。
     在库里到处出现、却只有少数文件正式定义它的（如「正常工作」「单位产品」）是泛词。
     比值分布脚本原样打出来（本机实测：最小 0.0012 / 中位 0.075 / 最大 1.0）。

输出：`var/tmp/terms-50.txt`（可直接粘进提示词 A）+ `var/tmp/terms-50-evidence.md`（来源自查表）

字段口径（踩过的坑）：
  * 领域标签在 `doc_meta.domain_tags`，形态 `'["CCS:C65 劳动安全技术综合"]'`；
    **`ccs_code` 与 `ccs_name` 两列在本机全空**（各 0 条）——别照列名想当然。
  * 显示领域**不要**用"该大类字母下最常见的子类名"：那是抽签出来的，会出现
    「浓香型白酒 → 卫生、安全、劳动保护」这种笑话。本脚本直接显示**定义该术语的文件里
    最常见的那个完整标签**（如 `CCS:X61 蒸馏酒`），是数据里的事实。
  * `hierarchy_path` **不含**「术语」字样（实测 0 条命中，只存祖先编号）⇒ 不能用它定位术语章节。

留痕（我在"给一份术语清单"这件小事上连错三轮）：
  v1：`LIKE '%[A-Za-z]%'` —— SQLite 的 LIKE **不支持方括号字符类**，整条查询 0 行；
      改用 hierarchy_path 定位术语章节 ⇒ 也是 0 行（它不含「术语」）。
      而且当时把"中文串 + 后面的标准号"当术语 ⇒ 抓出「中华人民共和国国家标准」(348 篇)、
      「标签应符合」「试样的采取按」这类假条目，还混进「资源」「产品」「类型」等泛词。
  v2：读 `ccs_code`/`ccs_name` ⇒ 两列全空、0 篇打上标签；领域名用"最多子类名"⇒ 打错。
  v3：改用 `domain_tags` + 完整标签显示 + 泛词比值筛 + 开头虚词过滤
      （杀掉「与短路保护电器」这种半截话）。
只读真库。
"""
from __future__ import annotations

import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
from src.core.text_utils import segment_for_fts  # noqa: E402

DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
OUT_DIR = Path(r"D:\AI\work space\zcode\var\tmp")

TERM_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*)?\s*"
    r"([\u4e00-\u9fff][\u4e00-\u9fff（）()·、\-]{2,15}?)\s*"
    r"([A-Za-z][A-Za-z \-/(),]{2,60}?)\s*"
    r"(?=[\u4e00-\u9fff（])"
)
TAG_RE = re.compile(r"CCS:[A-Z]\d+\s+[^\"\]]+")

STOP_SUB = ("应符合", "应按", "术语", "定义", "范围", "规范性引用", "符号", "缩略语",
            "本文件", "本部分", "本标准", "中华人民共和国", "国家标准", "一般要求",
            "规定", "要求")
STOP_TAIL = ("的", "和", "与", "或", "及", "按", "应", "须", "宜", "由", "在", "对", "为", "是")
# 开头是虚词 ⇒ 是半截话（实测抓到过「与短路保护电器」）
STOP_HEAD = ("与", "和", "或", "及", "的", "在", "由", "对", "为", "是", "以", "按", "其", "该", "等")

# 比值上限：正式定义它的文件数 ÷ 它在库里的命中条数。越小越"专"。
# 1/12 = 定义它的文件数不到它出现条数的 8%。阈值是定的，分布会原样报出来。
RATIO_MIN = 1 / 12


def clean(t: str) -> str | None:
    t = t.strip().strip("（）()·、-—")
    if not (3 <= len(t) <= 14):
        return None
    if any(k in t for k in STOP_SUB):
        return None
    if t.endswith(STOP_TAIL):
        return None
    if t.startswith(STOP_HEAD):
        return None
    return t


def main() -> int:
    # 第一个参数 = 要多少条术语（默认 50）。业主 2026-09-24："测试用例可以再多一点"
    # —— 50 条 × 2 条说法 = 100 条，命中数只有个位数，**分不出 2% 与 4% 的差别**。
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    out_terms = OUT_DIR / f"terms-{N}.txt"
    out_table = OUT_DIR / f"terms-{N}-evidence.md"
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    # ① 每篇文件的完整标签（用于显示领域，不做外部断言）
    doc_tags: dict[str, list[str]] = {}
    for doc_id, tags in conn.execute("SELECT doc_id, domain_tags FROM doc_meta"):
        ts = [t.strip() for t in TAG_RE.findall(tags or "")]
        if ts:
            doc_tags[doc_id] = ts
    print(f"带领域标签的文章 {len(doc_tags):,} / 6,797")

    # ② 术语条目：形态 = 「编号 中文名 英文名 中文定义」
    term_docs: dict[str, set[str]] = defaultdict(set)
    n = 0
    for doc_id, txt in conn.execute("SELECT doc_id, content_text FROM clause_revision"):
        n += 1
        m = TERM_RE.match(txt or "")
        if not m:
            continue
        t = clean(m.group(1))
        if t:
            term_docs[t].add(doc_id)
    print(f"扫描 {n:,} 条；抽到候选术语 {len(term_docs):,} 个")

    # ③ 初筛：被 ≥3 篇文件正式定义，且落在 ≤2 个 CCS 大类里
    # ⚠ 这里**必须 sorted**：`dset` 是 set，而 Python 的字符串哈希默认随机化
    #   ⇒ 不排序的话 tags 顺序每次不同，后面 `Counter(tags).most_common(1)` 在打平时
    #   会选到不同的大类，于是分桶与轮转取全变 —— **本脚本第一版就是这样不确定的**
    #   （实测同一天连跑三次，末行分别是 地点概率 / 二乙基二硫代氨基甲酸钠 / 另一条）。
    pool: list[tuple[str, int, list[str]]] = []
    for t, dset in term_docs.items():
        tags = sorted(tg for d in sorted(dset) for tg in doc_tags.get(d, ()))
        if len(dset) < 3 or not tags:
            continue
        cats = {tg.split()[0].split(":")[1][0] for tg in tags}
        if len(cats) > 2:
            continue
        pool.append((t, len(dset), tags))
    print(f"初筛后（≥3 篇定义 且 ≤2 个大类）剩 {len(pool):,} 个")

    # ④ 复筛：正式定义它的文件数 ÷ 它在库里的命中条数 —— 太小的是泛词。
    #    阈值**自适应**：先试 RATIO_MIN，不够 N 就依次放宽，并写明实际用了哪一档。
    #    这样"要 300 条"不会因为阈值太紧只挤出几十条，也不会悄悄换掉判据而不留痕。
    cand: list[tuple[str, int, list[str], int, float]] = []
    ratios: list[float] = []
    for t, dcnt, tags in pool:
        seg = segment_for_fts(t)
        if not seg.strip():
            continue
        try:
            hits = conn.execute(
                "SELECT count(*) FROM clause_fts WHERE clause_fts MATCH ?", (f'"{seg}"',)
            ).fetchone()[0]
        except sqlite3.OperationalError:
            continue
        if hits <= 0:
            continue
        r = dcnt / hits
        ratios.append(r)
        cand.append((t, dcnt, tags, hits, r))
    ratios.sort()
    if ratios:
        import statistics
        print(f"复筛前 {len(pool)} 个；比值(定义文件数/命中条数) 分布："
              f"最小 {ratios[0]:.4f} / 中位 {statistics.median(ratios):.4f} / 最大 {ratios[-1]:.4f}")
    kept: list = []
    used = None
    for thr in (RATIO_MIN, 1 / 20, 1 / 30, 1 / 50, 0.0):
        kept = [c for c in cand if c[4] >= thr]
        used = thr
        if len(kept) >= N:
            break
    print(f"泛词比值阈值实际用了 {used:.4f}（该档剩 {len(kept)} 个候选，要 {N} 个）")

    # ⑤ 按"定义它的文件里最常见的完整标签"的大类字母分桶，轮转取满 N
    by_cat: dict[str, list] = defaultdict(list)
    for item in kept:
        cat = Counter(item[2]).most_common(1)[0][0].split()[0].split(":")[1][0]
        by_cat[cat].append(item)
    for c in by_cat:
        by_cat[c].sort(key=lambda x: (-x[1], x[0]))
    cats = [c for c, v in sorted(by_cat.items(), key=lambda x: -len(x[1])) if len(v) >= 3]

    picked: list = []
    idx = 0
    while len(picked) < N:
        progressed = False
        for c in cats:
            if idx < len(by_cat[c]) and len(picked) < N:
                picked.append(by_cat[c][idx])
                progressed = True
        if not progressed:
            break
        idx += 1

    print()
    print("=" * 78)
    print(f"给提示词 A 的术语清单（{len(picked)} 个，整段复制）")
    print("=" * 78)
    term_lines = "\n".join(p[0] for p in picked)
    print(term_lines)

    print()
    print("=" * 78)
    print("自查用（不用粘给模型）")
    print("=" * 78)
    rows = ["| # | 术语 | 正式定义它的文件数 | 在库里命中条数 | 里头最常见的标签（领域） |",
            "|---|---|---|---|---|"]
    for i, (t, dcnt, tags, hits, r) in enumerate(picked, 1):
        top = Counter(tags).most_common(1)[0][0]
        rows.append(f"| {i} | {t} | {dcnt} | {hits} | {top} |")
        print(f"  {i:>2}. {t:<16} 定义 {dcnt:>2} 篇 / 命中 {hits:>5} 条  {top}")
    print()
    print(f"共 {len(picked)} 个；覆盖大类 " + "、".join(
        f"{c}={v}" for c, v in Counter(
            Counter(p[2]).most_common(1)[0][0].split()[0].split(":")[1][0] for p in picked
        ).most_common()))

    out_terms.write_text(term_lines + "\n", encoding="utf-8")
    out_table.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"\n已写 {out_terms}\n已写 {out_table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
