# -*- coding: utf-8 -*-
"""产物稳定索引（2026-09-15 收敛循环 v2 立）。

**为什么要它**：`parse_out/<doc_id>/` 是**按 doc_id 键控**的，而入库会给每部
文档重发 ULID → 复用重导之后，现库 doc_id 指向的产物目录**大量不存在**（实测
只有 32.8% 能按 doc_id 直取）。自进化循环全程不得写库，更不能因为重导就把
产物"弄丢"——所以必须有一条**与 doc_id 无关**的定位链路。

**稳定键**：深度产物的文件名内嵌源 PDF 的文件名（`mineru/.../auto/<pdf名>_layout.json`），
故用「源 PDF 名（归一后）→ 产物目录」建索引；文本层文档没有这个线索，走
**零外发文本层重提**（`force_deep=False, deep_fallback=False`，blocks 落
`evolve/scratch/`，绝不写 parse_out、绝不调云）。

只读：本模块不写库、不写 parse_out。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE = HERE / "evolve" / "artifact_index.json"
#: middle_locator 的三模式（单一所有者在那里，这里只用于**枚举**，不判语义）
PATTERNS = ("*_middle.json", "middle.json", "*_layout.json", "layout.json")


def parse_out_root() -> Path:
    from src.core.config import get_settings
    return Path(get_settings().data_dir) / "parse_out"


def norm_stem(name: str) -> str:
    """源文件名归一：NFKC + 去空白 + 去副本后缀 "(1)" + 小写。"""
    s = unicodedata.normalize("NFKC", name or "")
    s = re.sub(r"\.(pdf|PDF)$", "", s)
    s = re.sub(r"\s*\(\d+\)\s*$", "", s)
    s = re.sub(r"[\s　]+", "", s)
    return s.lower()


def _artifact_stem(fname: str) -> str:
    """从产物文件名反推源 PDF 名：`xxx_layout.json` → `xxx`。"""
    base = Path(fname).name
    for suf in ("_middle.json", "_layout.json", "middle.json", "layout.json"):
        if base.endswith(suf):
            base = base[: -len(suf)]
            break
    return base


def _land_key(key: str) -> str:
    """落位目录消毒名——**与 `vlm_ocr.land_dir` 同一口径**（单一所有者口径）。

    改这里必须同步改 `vlm_ocr.land_dir`，否则新语料产物定位立刻失效。
    """
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in key)[:80]


def _usable_dir(d: Path, root: Path) -> bool:
    """该目录能否作为**某部文档的**产物目录。

    必须挡掉三个陷阱：`parse_out` 根（空 doc_id 的假命中）、`.stash` 留档区
    （血泪教训：新旧产物同处一棵树会让评估对象不确定）、不存在的路径。
    """
    if d == root or d.name in ("", ".stash"):
        return False
    try:
        if not d.is_dir():
            return False
    except OSError:
        return False
    # 必须是 parse_out 的**直接子目录**（深一层的 mineru/… 不是文档产物目录）
    return d.parent == root


def build(verbose: bool = False) -> dict:
    """扫描 parse_out，建 `norm_stem → 最新产物目录` 索引并落缓存。"""
    root = parse_out_root()
    t0 = time.monotonic()
    idx: dict[str, dict] = {}
    dirs = 0
    hits = 0
    if root.is_dir():
        for d in root.iterdir():
            if not d.is_dir():
                continue
            dirs += 1
            for pat in PATTERNS:
                for f in d.rglob(pat):
                    hits += 1
                    key = norm_stem(_artifact_stem(f.name))
                    if not key:
                        continue
                    mt = f.stat().st_mtime
                    cur = idx.get(key)
                    if cur is None or mt > cur["mtime"]:
                        # 产物目录用文件所在目录（deep 路径消费 auto/ 目录）
                        idx[key] = {"dir": str(f.parent), "mtime": mt,
                                    "file": f.name, "doc_dir": d.name}
    out = {
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "root": str(root),
        "parse_out_dirs": dirs,
        "artifact_files": hits,
        "keys": len(idx),
        "wall_s": round(time.monotonic() - t0, 2),
        "index": idx,
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"[index] parse_out 目录 {dirs} · 产物文件 {hits} · 稳定键 {len(idx)} "
              f"· {out['wall_s']}s → {CACHE}")
    return out


def load() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return build()


def ambiguous_stems(docs: list[dict]) -> set[str]:
    """语料内**不唯一**的归一化源文件名（撞键）→ 索引对这些键不可信。

    2026-09-15 实测：6 部法律文档的源文件都叫 `source.pdf`，稳定键全部撞成
    `source` → 6 部都解析到**同一个**产物目录，仪器读到的是别人的内容
    （《民法典》因此被误报"塌缩 1065→22"）。这类键必须弃用，改走该文档
    **自己的 PDF** 做文本层重提（身份确定、零外发）。
    """
    from collections import Counter
    c = Counter(norm_stem(Path(d.get("file_path") or "").stem) for d in docs)
    return {k for k, v in c.items() if v > 1}


def resolve(doc: dict, index: dict | None = None,
            ambiguous: set[str] | None = None) -> dict:
    """把一部文档解析到「产物目录」：doc_id 直取 → 稳定键 → 文本层兜底。

    doc: {"doc_id","standard_no","file_path"}
    返回 {"kind": "auto|deep|scratch|gap", "dir": Path|None, "why": str,
          "certain": bool}   # certain=False 表示身份不可证 → 不得据此判塌缩
    """
    idx = (index or load())["index"]
    amb = ambiguous or set()
    root = parse_out_root()
    pdf = Path(doc.get("file_path") or "")
    if not pdf.exists() and pdf.suffix == "":
        pdf = Path(str(pdf) + ".pdf")

    # 1) doc_id 直取（重导后常失效，但仍然先试——最快且身份确定）
    #    **空 doc_id 必须跳过**：`root / ""` == root，而 root.is_dir() 恒为真 →
    #    会把一切文档"解析"到整个 parse_out 根目录、读到全体产物（实测踩过：
    #    新语料未入库、doc_id 为空时 doctor 报 auto=231 全是这个假命中）。
    did = str(doc.get("doc_id") or "")
    if did and _usable_dir(root / did, root):
        return {"kind": "auto", "dir": root / did, "why": "parse_out/<doc_id>",
                "certain": True}

    # 1b) 落位目录消毒名（`vlm_ocr.land_dir` 口径）——**未入库语料**的产物目录
    #     就长这样（`parse_out/<消毒的std_no>/`），而索引的 `norm_stem` 与之
    #     不同形，故必须单独试一次，否则新语料永远定位不到自己的产物。
    std = str(doc.get("std_no") or "")
    if std:
        cand = root / _land_key(std)
        if _usable_dir(cand, root):
            return {"kind": "auto", "dir": cand, "why": "landing:<消毒std_no>",
                    "certain": True}

    # 2) 稳定键（源 PDF 名归一）——**撞键即弃用**（否则读到别人的内容）
    if pdf.exists():
        key = norm_stem(pdf.stem)
        if key and key not in amb:
            rec = idx.get(key)
            if rec:
                return {"kind": "auto", "dir": Path(rec["dir"]),
                        "why": f"stem-index:{rec['file'][:40]}", "certain": True}
        elif key in amb:
            return {"kind": "scratch", "dir": pdf,
                    "why": f"撞键({key})→改用本文档 PDF 文本层重提",
                    "certain": True}

    # 3) 文本层兜底（零外发：force_deep=False + deep_fallback=False）
    if pdf.exists():
        return {"kind": "scratch", "dir": pdf, "why": "textlayer-reread",
                "certain": True}
    return {"kind": "gap", "dir": None, "why": "无产物且源 PDF 不存在",
            "certain": False}


def resolve_to_parse_dir(doc: dict, index: dict | None = None,
                         scratch_root: Path | None = None,
                         ambiguous: set[str] | None = None) -> dict:
    """同 resolve，但把 scratch（文本层兜底）落成实际 blocks。

    返回 {"dir": Path|None, "kind": str, "why": str, "certain": bool}
    """
    r = resolve(doc, index, ambiguous)
    if r["kind"] != "scratch":
        return r
    from src.core.ingestion.mineru_adapter import parse_pdf_with_mineru
    base = scratch_root or (HERE / "evolve" / "scratch" / norm_stem(Path(r["dir"]).stem))
    base.mkdir(parents=True, exist_ok=True)
    try:
        parse_pdf_with_mineru(Path(r["dir"]), base, force_deep=False,
                              deep_fallback=False)
    except Exception as e:  # noqa: BLE001
        return {"kind": "gap", "dir": None, "why": f"文本层重提失败 {type(e).__name__}"}
    return {"kind": "blocks", "dir": base, "why": r["why"]}


def main() -> None:
    build(verbose=True)


if __name__ == "__main__":
    main()
