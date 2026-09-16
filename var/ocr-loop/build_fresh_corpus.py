# -*- coding: utf-8 -*-
"""在**全新语料**上重建语料集 + 留出集（2026-09-15 用户指令）。

用户指令：「之前一直在重复做的 260 部不要用了，免得过拟合，用别的文档。」

设计（沿用 scout.py 既有规则，保证可比、可复现）：
- 候选 = 语料库中**从未使用**过、且**归一 stem 唯一**（不撞键）的 PDF；
- 4 层（标准号区间）× 层内按**源 PDF 名哈希**排序（固定种子）→ 留出集每层 7 部；
- 留出集**锁定**，永不参与修复决策；工作集取其余。
- **一票否决**：任何路径/标准号与旧 260 部或旧留出集重叠的，一律剔除。

只写 var/ocr-loop/evolve/ 下的清单文件，不写库、不写 parse_out。
"""
import hashlib
import json
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"D:\AI\work space\zcode")
CORPUS = Path(r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)")
EV = ROOT / "var" / "ocr-loop" / "evolve"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "var" / "ocr-loop"))
from src.core.config import get_settings  # noqa: E402
import artifact_index as AI                   # noqa: E402

SEED = "ks-evolve-2026-fresh"          # 新种子：与旧样本彻底解耦
STRATA = [(0, 10000), (10000, 20000), (20000, 30000), (30000, 10 ** 9)]
N_WORK = 232
N_HOLDOUT_PER_STRATUM = 7              # 4 层 × 7 = 28

conn = sqlite3.connect(f"file:{get_settings().db_path}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
used_paths = {str(r["file_path"] or "").lower().replace("/", "\\")
              for r in conn.execute("SELECT file_path FROM doc_meta")}
conn.close()
old_hold = json.loads((EV / "holdout.json").read_text(encoding="utf-8"))
old_hold_nos = set(old_hold["std_nos"])


def std_of(stem: str) -> str:
    """'GB／T 649-2023 化学试剂 溴化钾(1)' → 'GB/T 649-2023'（规范化）。"""
    s = stem.replace("／", "/").replace("（", "(").replace("）", ")")
    m = re.match(r"\s*(GB(?:/T|/Z)?)\s*(\d+(?:\.\d+)*)\s*[-—]\s*(\d{4})", s, re.I)
    if m:
        return f"{m.group(1).upper().replace('/T', '/T')} {m.group(2)}-{m.group(3)}"
    return s.split()[0] if s.split() else stem


def std_num(stem: str) -> int | None:
    m = re.search(r"(\d{1,6})", stem)
    return int(m.group(1)) if m else None


def stratum_of(stem: str) -> int:
    n = std_num(stem)
    if n is None:
        return -1
    for i, (lo, hi) in enumerate(STRATA):
        if lo <= n < hi:
            return i
    return -1


# ---- 候选：全新 + stem 唯一 + 不与旧留出集重叠 ----
byname: dict[str, list[Path]] = defaultdict(list)
for p in sorted(CORPUS.rglob("*.pdf")):
    if str(p).lower().replace("/", "\\") in used_paths:
        continue
    byname[AI.norm_stem(p.stem)].append(p)

cand = [v[0] for v in byname.values() if len(v) == 1]
cand = [p for p in cand if std_of(p.stem) not in old_hold_nos]
print(f"候选（全新·不撞键·不含旧留出集）: {len(cand)} 部")

buckets: dict[int, list[Path]] = defaultdict(list)
for p in cand:
    buckets[stratum_of(p.stem)].append(p)


def hkey(p: Path) -> str:
    return hashlib.sha256(f"{SEED}|{AI.norm_stem(p.stem)}".encode()).hexdigest()


holdout: list[Path] = []
for i in range(len(STRATA)):
    s = sorted(buckets.get(i, []), key=hkey)
    holdout += s[:N_HOLDOUT_PER_STRATUM]
hold_set = set(holdout)

work: list[Path] = []
for i in range(len(STRATA)):
    s = sorted([p for p in buckets.get(i, []) if p not in hold_set], key=hkey)
    # 各层按可用量等比例取，保证工作集层分布均衡
    take = max(1, round(N_WORK * len(s) / max(len(cand) - len(holdout), 1)))
    work += s[:take]
work = sorted(work, key=lambda p: std_of(p.stem))[:N_WORK]
holdout = sorted(holdout, key=lambda p: std_of(p.stem))

print(f"工作集 {len(work)} 部 · 留出集 {len(holdout)} 部")
print("工作集层分布:", dict(Counter(stratum_of(p.stem) for p in work)))
print("留出集层分布:", dict(Counter(stratum_of(p.stem) for p in holdout)))

# 断言：绝不与旧语料/旧留出集重叠
overlap = [p for p in work + holdout
           if str(p).lower().replace("/", "\\") in used_paths
           or std_of(p.stem) in old_hold_nos]
print(f"与旧语料/旧留出集重叠: {len(overlap)}（必须为 0）")
assert not overlap, overlap[:3]

ts = time.strftime("%Y-%m-%d %H:%M:%S")
(EV / "holdout.json").replace(EV / "holdout.json.old260")      # 旧留出集留档
(EV / "fresh_corpus_work.json").write_text(json.dumps(
    {"built_at": ts, "seed": SEED, "n": len(work),
     "rule": "全新语料、stem 唯一、不与旧 260 部/旧留出集重叠；4 层按哈希排序取",
     "std_nos": [std_of(p.stem) for p in work],
     "paths": [str(p) for p in work]}, ensure_ascii=False, indent=1), encoding="utf-8")
(EV / "holdout.json").write_text(json.dumps(
    {"built_at": ts, "seed": SEED, "n": len(holdout), "locked": True,
     "rule": "全新语料 4 层 × 每层按源 PDF 名哈希取前 7 部，固定种子（永不参与修复决策）",
     "strata": {str(k): len([p for p in holdout if stratum_of(p.stem) == k])
                for k in sorted(set(stratum_of(p.stem) for p in holdout))},
     "std_nos": [std_of(p.stem) for p in holdout],
     "paths": [str(p) for p in holdout]}, ensure_ascii=False, indent=1),
    encoding="utf-8")
print(f"→ 旧留出集留档 holdout.json.old260")
print(f"→ 工作集 {EV / 'fresh_corpus_work.json'}")
print(f"→ 新留出集 {EV / 'holdout.json'}（locked）")
print("\n工作集前 5:")
for p in work[:5]:
    print("  ", p.relative_to(CORPUS))
