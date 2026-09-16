# -*- coding: utf-8 -*-
"""新语料（未入库文档）的只读文档清单（2026-09-15 立）。

**为什么需要它**：用户指令「之前一直在重复做的 260 部不要用了，免得过拟合，
用别的文档」。而 `evolve.doc_list()` 只列**库内** `doc_meta` —— 全新的 231 部
工作集文档尚未入库，循环因此看不见它们，侦察与轮次都无从下手。

本模块从 `evolve/fresh_corpus_work.json`（`build_fresh_corpus.py` 产出）构造
与 `evolve.doc_list()` **同形**的记录，使 `evaluate_doc` / `scout` / `eval`
无需改动即可评估新语料：

    {"i", "doc_id"（空）, "std_no", "std_name", "file_path", "file_hash"}

- `std_no` 用**源 PDF 名**（与语料一致、跨轮稳定；doc_id 会重发，不适用）；
- `doc_id` 留空 → `artifact_index.resolve` 跳过 doc_id 直取，走
  `norm_stem → parse_out/<消毒名>/` 稳定键（**正是新语料产物的落位方式**）；
- `file_hash` 用内容哈希（前 16 位）——跨轮身份比对用。

只读：不写库、不动 parse_out、不调云。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

WORK_LIST = HERE / "evolve" / "fresh_corpus_work.json"
HOLDOUT = HERE / "evolve" / "holdout.json"


def work_list() -> Path:
    """当前工作集清单。

    `KS_CORPUS_LIST` 可指向别处（分批推进用：`next_batch.py` 产出的
    `work_batch*.json`）。默认仍是首批 231 部——**留出集始终不动**，
    故各批的留出集判定可横向比较。
    """
    env = (os.environ.get("KS_CORPUS_LIST") or "").strip()
    if not env:
        return WORK_LIST
    p = Path(env)
    return p if p.is_absolute() else (HERE / p)


def _load(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _file_hash(p: Path) -> str:
    """内容哈希（前 16 位）。大文件按块读，避免整本 141G 语料爆内存。"""
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
    except Exception:  # noqa: BLE001
        return ""
    return h.hexdigest()[:16]


def docs_from_list(list_file: Path | None = None,
                   only: set[str] | None = None) -> list[dict]:
    """清单文件 → 文档记录列表（与 `evolve.doc_list()` 同形）。

    `only`：只要这些标准号（留出集验证用）。
    """
    obj = _load(list_file or work_list())
    out: list[dict] = []
    for p in obj.get("paths") or []:
        pdf = Path(p)
        std = pdf.stem
        if only is not None and std not in only:
            continue
        out.append({"i": len(out) + 1, "doc_id": "", "std_no": std,
                    "std_name": std, "file_path": str(pdf),
                    "file_hash": _file_hash(pdf) if pdf.exists() else ""})
    return out


def work_docs() -> list[dict]:
    return docs_from_list(work_list())


def holdout_docs() -> list[dict]:
    """留出集文档（新语料留出集：`holdout.json` 的 paths）。"""
    return docs_from_list(HOLDOUT)


def backend_of(doc: dict) -> str:
    """该文档产物的通道（`hybrid`/`vlm` = VLM；`textlayer` = fitz 直取）。

    读产物 JSON **尾部** 4KB 取 `_backend`——字段在文件末尾，读头部取不到
    （会恒返回 unknown；血泪教训）。
    """
    import artifact_index as AI
    r = AI.resolve(doc)
    if not r.get("dir"):
        return "gap"
    d = Path(r["dir"])
    cands = list(d.glob("blocks.json")) + list(d.rglob("*_middle.json")) \
        + list(d.rglob("*_layout.json"))
    for f in cands:
        try:
            size = f.stat().st_size
            with open(f, "rb") as fh:
                if size > 4096:
                    fh.seek(size - 4096)
                tail = fh.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        import re
        m = re.search(r'"_backend"\s*:\s*"([a-z\-]+)"', tail)
        if m:
            return m.group(1)
    return "unknown"


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="新语料只读文档清单")
    ap.add_argument("--holdout", action="store_true", help="列出留出集而非工作集")
    ap.add_argument("--limit", type=int, default=5)
    a = ap.parse_args()
    docs = holdout_docs() if a.holdout else work_docs()
    print(f"{'留出集' if a.holdout else '工作集'} {len(docs)} 部")
    for d in docs[:a.limit]:
        print(f"  {d['std_no'][:52]:<54} hash={d['file_hash'] or '?'}")


if __name__ == "__main__":
    main()
