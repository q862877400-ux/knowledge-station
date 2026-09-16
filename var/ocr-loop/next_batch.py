# -*- coding: utf-8 -*-
"""分批选取**全新语料**（2026-09-15 立，用户指令：防过拟合、每批都必须是别的文档）。

**为什么需要它**：目标是把 35,243 部全部 VLM 化，而"同一批文档反复审计"会过拟合
（用户明确纠正过）。故推进方式必须是**逐批换全新文档**。人工记"哪些跑过"迟早出错，
本工具把这条纪律变成机器保证：

    本批候选 = 语料全量
             − 库内已用（doc_meta.file_path）
             − 已跑过的所有批次（evolve/fresh_corpus_work*.json 的 paths）
             − 留出集（evolve/holdout.json 的 paths，**锁定不参与**）
             − 归一 stem 撞键的重复副本（撞键即弃用，HISTORY 血泪教训）
    再按 4 层分层 + 层内固定种子哈希排序取前 N → **确定性可复现**。

用法：
  python var/ocr-loop/next_batch.py --size 231            # 取下一批（写 work_batch2.json）
  python var/ocr-loop/next_batch.py --size 231 --name work_batch3.json
  python var/ocr-loop/next_batch.py --stats               # 只看剩余可用量与分层分布

只写 `evolve/<name>.json`（清单），不写库、不写 parse_out、不调云。
"""
from __future__ import annotations

import argparse
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

SEED = "ks-evolve-2026-fresh"
STRATA = [(0, 10000), (10000, 20000), (20000, 30000), (30000, 10 ** 9)]


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


def hkey(p: Path) -> str:
    return hashlib.sha256(f"{SEED}|{AI.norm_stem(p.stem)}".encode()).hexdigest()


def used_paths() -> set[str]:
    conn = sqlite3.connect(f"file:{get_settings().db_path}?mode=ro", uri=True)
    out = {str(r[0] or "").lower().replace("/", "\\")
           for r in conn.execute("SELECT file_path FROM doc_meta")}
    conn.close()
    return out


def prior_batch_paths() -> set[str]:
    """已建批次清单里的全部 paths（含历史批），本批必须排除。"""
    out: set[str] = set()
    for f in sorted(EV.glob("*.json")):
        if not (f.name.startswith("work_batch") or
                f.name.startswith("fresh_corpus_work") or
                f.name.startswith("holdout")):
            continue
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        out |= {str(p) for p in (obj.get("paths") or [])}
    return out


#: 下载副本后缀（`…(1)` / `…(2)`）：挑代表时**优先无后缀**的那份。
_DUP_SUFFIX = re.compile(r"\(\d+\)\s*$")


def _rep_order(p: Path) -> tuple[int, str]:
    """撞键组的代表选择序（**确定性、可复现**）：先"有无副本后缀"，再路径字典序。"""
    return (1 if _DUP_SUFFIX.search(p.stem) else 0, str(p))


def candidates() -> list[Path]:
    """全新、未用过、不在留出集里的候选；**每个归一 stem 恰好一个代表**。

    **2026-09-16 修（本仓库最大内容缺口，见 HANDOFF §10.31）**：
    原实现是

        byname = {未过 block 的文件按 norm_stem 分组}
        return [v[0] for v in byname.values() if len(v) == 1]   # ← 整组丢弃

    ——**归一 stem 撞键的组被整组丢掉**。而这些文件又**不在** `block` 里
    （否则第一步就拦掉了），于是它们**从未进入任何批次、从未被 OCR**。
    实测：抽 200 组，**有覆盖 0 / 无覆盖 200**；按比例外推约
    **3,228 个标准 / 6,625 个文件**——比巨型缺口(33 部)大两个数量级，
    而且 driver 的"剩余候选"**永远不含它们**，**链条跑到底也补不上**。

    **它们绝大多数不是"不同文档同名"，而是"同一标准的多份副本"**：
    `GB 1499.1-2024 …(1).pdf / (2).pdf / .pdf`；
    `GB 3836.15-2024` 三份只差**全角空格 / 半角空格 / 无空格**（归一后同键）。

    原规则的正当来源是 HISTORY 血泪教训：6 部法律文档都叫 `source.pdf`
    → 索引撞成一个键，把《民法典》误报成"塌缩 1065→22"。
    **它要防的是"不同文档同名"，不是"同一文档多副本"。**

    **改法：每组保留恰好一个代表，且代表在整语料上固定。**
      - 先在整个语料上分组（**不是**过 block 之后才分组）→ 代表不随
        block 变动而漂移；
      - 代表 = `min(members, key=_rep_order)`（优先无 `(N)` 后缀的那份）；
      - 代表被 block 命中 → **该组不再产出候选**（非代表永不浮出）。
    于是**一个键恒对应一个文档**（原保护分毫未降），而
    **每个不同标准至少被 OCR 一次**。
    对病态情形（6 部不同文档同名）从"0 部"变"1 部——**严格更好**。
    """
    used = used_paths()
    prior = prior_batch_paths()
    hold = json.loads((EV / "holdout.json").read_text(encoding="utf-8"))
    hold_paths = {str(p) for p in (hold.get("paths") or [])}
    block = used | prior | hold_paths
    byname: dict[str, list[Path]] = defaultdict(list)
    for p in sorted(CORPUS.rglob("*.pdf")):
        byname[AI.norm_stem(p.stem)].append(p)
    out: list[Path] = []
    for members in byname.values():
        rep = min(members, key=_rep_order)
        key = str(rep).lower().replace("/", "\\")
        if key in block or str(rep) in block:
            continue
        out.append(rep)
    return out


def pick(cand: list[Path], size: int) -> list[Path]:
    """4 层按可用量等比例取，层内哈希序（确定性、可复现）。"""
    buckets: dict[int, list[Path]] = defaultdict(list)
    for p in cand:
        buckets[stratum_of(p.stem)].append(p)
    total = len(cand)
    out: list[Path] = []
    for i in range(len(STRATA)):
        s = sorted(buckets.get(i, []), key=hkey)
        take = max(1, round(size * len(s) / max(total, 1)))
        out += s[:take]
    return sorted(out, key=lambda p: (std_num(p.stem) or 0, p.stem))[:size]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=231)
    ap.add_argument("--name", default="")
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()

    cand = candidates()
    print(f"剩余可用全新候选：{len(cand)} 部")
    print("分层分布:", dict(sorted(Counter(stratum_of(p.stem)
                                      for p in cand).items())))
    if a.stats:
        return
    work = pick(cand, a.size)
    if len(work) < a.size:
        print(f"⚠ 候选不足：只取到 {len(work)} 部（要 {a.size}）")
    name = a.name or f"work_batch{time.strftime('%Y%m%d-%H%M')}.json"
    obj = {"built_at": time.strftime("%Y-%m-%d %H:%M:%S"), "seed": SEED,
           "n": len(work), "size_requested": a.size,
           "rule": ("全新语料、归一 stem 唯一、排除库内已用/已跑批次/留出集；"
                    "4 层按哈希序取 —— **每批全新文档**（防过拟合）"),
           "strata": dict(sorted(Counter(stratum_of(p.stem)
                                         for p in work).items())),
           "paths": [str(p) for p in work]}
    (EV / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    print(f"\n本批 {len(work)} 部 → {EV / name}")
    print("层分布:", obj["strata"])
    for p in work[:5]:
        print("   ", p.stem[:64])


if __name__ == "__main__":
    main()
