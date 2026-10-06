"""**原型**：把 MinerU 4.0 的 `middle_json` 适配成 3.4 的形状，喂给**现有的** `load_middle_items`。

## 为什么是这个做法（业主 2026-10-07 的线索 + 本轮实测）
业主提示："这种后处理原先 KS 已经做了很多了，但是那时候 MinerU 还是 3.4 版本不是现在用的 4.0"。
实测证实：
 · 既有后处理**很全**（`_CHAPTER_CLAUSE` 章头、`_CLAUSE_APPENDIX` 附录号、防误切闸门、目录/索引过滤、
   "还原 MinerU 吞点 41→4.1"）—— **逻辑本身没问题**；
 · 但 `load_middle_items` 读的是 `mj.get("pdf_info", [])`（**3.4 的键**），而 4.0 顶层是 `pages`
   ⇒ `.get(..., [])` 给空列表 ⇒ **静默返回 0 条、不报错**（实测 5/5 本 items=0）。
 ⇒ **该补的不是切分器，是输入形状**。本脚本只写一层**转换**，切分器一行不改。

## 映射（3.4 ⇐ 4.0）
 `pdf_info`            ⇐ `pages`
 `page_size`           ⇐ `extensions.docvortex_layout.pages[i].width_pt/height_pt`
 `para_blocks`         ⇐ `pages[i].blocks`
 `blocks`（子块）       ⇐ `block.content`（列表）
 文本块 `lines[].spans[]` ⇐ `content[]`：`text`→`text` 型 span；`equation_inline`→`inline_equation`
 `paragraph_title`/`doc_title` → 3.4 的 `title`（切分器据此判 `kind='title'`）
 `table`  → 子块 `table_caption` + `table_body`（**4.0 的 `table_body.content` 直接就是 HTML**）
 `image`  → 子块 `image_caption` + `image_body`（span 带 `image_path`）
 `chart`  → 3.4 chart 块（子块文本作题注）
 `equation` → 文本块，内放一个 `interline_equation` span（走既有的 latex→可读文本）
 `header`/`footer`/`page_number`/`page_footnote` → 放进 `discarded_blocks`（3.4 里本就不读 ⇒ 等效跳过）

**只读源目录；不连库、不写库。**

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\30-adapter-prototype.py --n 40
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "adapter-prototype.json"
sys.path.insert(0, str(ROOT))
GB_ROOT = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
SUFFIX = ".mineru-4.0.10-vlm"

DISCARD = {"header", "footer", "page_number", "page_footnote"}
TITLE = {"paragraph_title", "doc_title", "title"}


def _as_text(c) -> str:
    """4.0 的 `content` 有时是字符串、有时是对象列表 ⇒ 统一取文本。"""
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(_as_text(x) for x in c if x is not None)
    if isinstance(c, dict):
        return _as_text(c.get("content"))
    return ""


def _spans_of(items) -> list[dict]:
    """4.0 的 content 列表 → 3.4 的 `lines[].spans[]`。"""
    spans = []
    if isinstance(items, str):
        items = [{"type": "text", "content": items}]
    for it in items or []:
        if not isinstance(it, dict):
            continue
        t = it.get("type")
        # ⚠ 4.0 的 `content` 会**嵌套**（内容本身又是一个列表）——
        #   实测 GB 39800.8-2024 触发 `TypeError: sequence item 0: expected str, list found`
        #   （`"".join(parts)` 收到 list）。统一用 `_as_text` 展平。
        c = _as_text(it.get("content"))
        if t in ("text", None) and c:
            spans.append({"type": "text", "content": c})
        elif t in ("equation_inline", "interline_equation") and c:
            spans.append({"type": "inline_equation", "content": c})
    return spans


def _text_block(btype_34: str, b: dict) -> dict:
    return {"type": btype_34, "bbox": b.get("bbox") or [],
            "lines": [{"bbox": b.get("bbox") or [], "spans": _spans_of(b.get("content"))}]}


def convert(mj: dict) -> dict:
    layout = (((mj.get("extensions") or {}).get("docvortex_layout") or {}).get("pages")) or []
    size_by_idx = {}
    for k, p in enumerate(layout):
        idx = p.get("page_idx", k)
        size_by_idx[idx] = [float(p.get("width_pt") or 595.0), float(p.get("height_pt") or 841.0)]

    pdf_info, discarded = [], []
    for k, pg in enumerate(mj.get("pages") or []):
        pidx = pg.get("page_idx", k)
        para, disc = [], []
        for b in pg.get("blocks") or []:
            t = b.get("type")
            if t in DISCARD:
                disc.append({"type": t, "bbox": b.get("bbox") or []})
                continue
            if t == "table":
                cap, html = "", None
                for it in b.get("content") or []:
                    if not isinstance(it, dict):
                        continue
                    if it.get("type") == "table_caption":
                        cap = _as_text(it.get("content"))
                    elif it.get("type") == "table_body":
                        c = it.get("content")
                        if isinstance(c, str) and c.strip().startswith("<"):
                            html = c
                subs = []
                if cap:
                    subs.append({"type": "table_caption",
                                 "lines": [{"spans": [{"type": "text", "content": cap}]}]})
                if html:
                    subs.append({"type": "table_body",
                                 "lines": [{"spans": [{"type": "table", "html": html}]}]})
                para.append({"type": "table", "bbox": b.get("bbox") or [], "blocks": subs})
            elif t == "image":
                cap, rel = "", None
                for it in b.get("content") or []:
                    if not isinstance(it, dict):
                        continue
                    if it.get("type") == "image_caption":
                        cap += _as_text(it.get("content"))
                    elif it.get("type") == "image_body":
                        rel = it.get("image_path") or _as_text(it.get("content"))
                subs = []
                if cap:
                    subs.append({"type": "image_caption",
                                 "lines": [{"spans": [{"type": "text", "content": cap}]}]})
                if rel:
                    subs.append({"type": "image_body",
                                 "lines": [{"spans": [{"image_path": rel}]}]})
                para.append({"type": "image", "bbox": b.get("bbox") or [], "blocks": subs})
            elif t == "chart":
                subs = []
                txt = " ".join(_as_text(it.get("content")) for it in (b.get("content") or [])
                               if isinstance(it, dict) and it.get("type") in ("chart_caption", "chart_footnote"))
                if txt.strip():
                    subs.append({"type": "chart_caption",
                                 "lines": [{"spans": [{"type": "text", "content": txt}]}]})
                para.append({"type": "chart", "bbox": b.get("bbox") or [], "blocks": subs})
            elif t == "equation":
                c = _as_text(b.get("content"))
                para.append({"type": "text", "bbox": b.get("bbox") or [],
                             "lines": [{"spans": [{"type": "interline_equation", "content": c}]}]})
            else:
                btype34 = "title" if t in TITLE else "text"
                blk = _text_block(btype34, b)
                if blk["lines"][0]["spans"]:
                    para.append(blk)
        pdf_info.append({"page_idx": pidx,
                         "page_size": size_by_idx.get(pidx, [595.0, 841.0]),
                         "para_blocks": para, "discarded_blocks": disc})
        discarded.extend(disc)
    return {"pdf_info": pdf_info, "_discarded_count": len(discarded)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    args = ap.parse_args()

    from src.core.ingestion.pipeline import load_middle_items, split_items_into_clauses

    dirs = [d for d in GB_ROOT.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)
            and (d / "middle_json.json").exists()]
    print(f"[proto] 有 middle_json 的国标 {len(dirs)} 本；本次取 {args.n}\n", flush=True)

    tmpdir = Path(tempfile.mkdtemp(prefix="ks-40adapt-"))
    rows, ok, zero = [], 0, 0
    for d in dirs[:args.n]:
        mj = json.loads((d / "middle_json.json").read_text(encoding="utf-8", errors="ignore"))
        conv = convert(mj)
        tf = tmpdir / (d.name[:60].replace(" ", "_") + ".json")
        tf.write_text(json.dumps(conv, ensure_ascii=False), encoding="utf-8")
        try:
            items, page_sizes = load_middle_items(tf)
            split = split_items_into_clauses(items)
            n_c = len(split)
            ok += 1
            zero += 1 if n_c == 0 else 0
            head = []
            for s in split[:6]:
                head.append(s[0] if isinstance(s, (list, tuple)) else getattr(s, "clause_number", "?"))
            rows.append({"dir": d.name[:54], "pages": len(conv["pdf_info"]),
                         "items": len(items), "clauses": n_c, "head": head})
            print(f"    {d.name[:46]:46s} 页 {len(conv['pdf_info']):3d}  items {len(items):4d}  "
                  f"⇒ **条款 {n_c:4d}**  号 {head}", flush=True)
        except Exception as e:                                              # noqa: BLE001
            rows.append({"dir": d.name[:54], "error": f"{type(e).__name__}: {e}",
                         "tb": traceback.format_exc()[-500:]})
            print(f"    {d.name[:46]:46s} ⛔ {type(e).__name__}: {str(e)[:70]}", flush=True)

    cls = [r["clauses"] for r in rows if "clauses" in r]
    n = max(1, len(cls))
    print(f"\n[proto] 成功 {ok}/{len(dirs[:args.n])}；**切出 0 条 {zero}/{n} = {zero/n:.0%}**")
    if cls:
        print(f"[proto] 条款数：中位 {int(st.median(cls))} / 最小 {min(cls)} / 最大 {max(cls)} / 合计 {sum(cls)}")
        for thr in (1, 10, 50, 100):
            k = sum(1 for c in cls if c >= thr)
            print(f"        条款数 ≥ {thr:3d} 的本数：{k}/{n} ({k/n:.0%})")

    OUT.write_text(json.dumps({
        "why": "原型：把 MinerU 4.0 middle_json 适配成 3.4 形状，喂现有 load_middle_items + split_items_into_clauses",
        "root_cause": ("load_middle_items 读 mj.get('pdf_info', [])（3.4 键），4.0 顶层是 'pages' "
                       "⇒ .get(...,[]) 给空列表 ⇒ 静默 0 条（实测 5/5 本 items=0）"),
        "docs": len(dirs[:args.n]), "success": ok, "zero_clause": zero,
        "clause_stats": {"median": int(st.median(cls)) if cls else None,
                         "min": min(cls) if cls else None, "max": max(cls) if cls else None,
                         "total": sum(cls) if cls else None},
        "rows": rows,
        "boundary": ["原型只做形状转换，未改切分器；未连库、未写库。",
                     "转换的正确性由『条款数是否合理 + 条款号是否像样』间接判断，尚未逐条人工核。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
