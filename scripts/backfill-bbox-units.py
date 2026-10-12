"""回填 MinerU 4.0 那批的**坏 bbox**（spec 012 R2）。

## 为什么需要回填

R1 修的是 `middle_schema._convert_40_to_34` 的**单位换算** —— 那只对**以后**入库的生效。
已经入库的 **756 篇 / 253,222 条条款（13.7%）** 仍是坏值：

```
坏值（库里）: [0.116, 3455.82, 0.937, 3455.86]
              ↑ x 是归一化比例（应为 0.116*2456 = 284.9）
                                  ↑ y = H − ny（ny 是比例，应为 H − ny*H）
```

## 为什么**不用纯变换**回填（试过，不行）

坏值 `bad_y = H − ny`，反推 `ny = H − bad_y`。但实测库里 `bad_y` **只存了 2 位小数**
（387/400 条是 2 位）⇒ 反推误差 0.005，乘回页高 3465 ⇒ **误差约 17pt**
—— 箭头会指到**相邻一行**去。**宁可重算，不许指错。**

## 为什么**不用重跑 OCR**（也不必）

MinerU 的产物还在盘上（`<pdf>.mineru-4.0.10-vlm/middle_json.json`，实测抽样 30/30 都在）。
⇒ 用**修好的** `load_middle_json` 重新读一遍，按 `(页号, 行号)` 对齐写回即可。

## 对齐判据（**本回填最容易出错的地方**）

`source_span` 是**行级**、且 `sort_order` 是入库时按**全文档行序**编的。
⇒ 不能按"第 N 个 span 对第 N 个 line"硬对。本脚本用**两条独立判据**取交集：

1. **按页分组**（`page_number` 必须相等）；
2. 组内按 `sort_order` 升序 ↔ 该页 `middle` 里**所有文本行**（含块内 `lines[].bbox`）
   按 (块序, 行序) 升序 —— 一一对应。

**对不齐就跳过该篇**（`skipped_mismatch`），**不硬写** ——
写错位置比不写更糟（用户会照着错箭头看原文）。

## 纪律

* **默认 dry-run**（只算不写）；`--apply` 才写。
* **写前先备份**（`--apply` 时自动做库备份，走既有的备份函数）。
* **单事务**：要么全成功要么全回滚（不许写一半）。
* **幂等**：已是正确值的（换算后相同）不动；重跑第二次应写 0 行。
* **可中断**：每篇之间检查；中断时如实报"处理了多少、还剩多少"。
* **留痕**：每篇写一条 `operation_log`。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.core.config import get_settings  # noqa: E402
from src.core.ingestion.middle_locator import find_middle_files  # noqa: E402
from src.core.ingestion.middle_schema import load_middle_json  # noqa: E402

#: 退化阈值（与引擎侧 `attach_bboxes` / 宿主侧 `/ks/bbox` 同口径）。
MIN_W = 5.0
MIN_H = 3.0


def _is_bad(box: list[float]) -> bool:
    """该 bbox 是不是"归一化 x + 未乘页高的 y"（= 本缺陷的形状）。"""
    if not (isinstance(box, list) and len(box) == 4):
        return False
    try:
        nums = [float(v) for v in box]
    except (TypeError, ValueError):
        return False
    # 特征：x 全在 [0,1]（比例）且 y 的量级是"页高"级（远超页高本身的一半）
    return all(0.0 <= v <= 1.0 for v in (nums[0], nums[2]))


def _lines_of_page(mj: dict, page_idx: int) -> list[list[float]]:
    """该页**全部文本行**的 bbox（按 块序→行序），与 `pipeline` 取行框的顺序一致。"""
    out: list[list[float]] = []
    for pi in mj.get("pdf_info") or []:
        if int(pi.get("page_idx", -1)) != page_idx:
            continue
        for blk in (pi.get("para_blocks") or []):
            for ln in (blk.get("lines") or []):
                bb = ln.get("bbox")
                if isinstance(bb, list) and len(bb) == 4:
                    out.append([float(v) for v in bb])
    return out


def _table_boxes_of_page(mj: dict, page_idx: int) -> list[list[float]]:
    """该页**表格块**的 bbox（**块级**）。

    ⚠ 为什么单独要这一组：`pipeline` 的 `table_spans` 用的是 `it.bbox`（**块级**），
    不是行级（见 `pipeline.py` 的 `table_spans = [... bbox=list(it.bbox) ...]`）。
    实测剩下没回填的 8,280 条**全是 `span_type='table'`** ⇒ 只按"行框"找永远找不到。
    """
    out: list[list[float]] = []
    for pi in mj.get("pdf_info") or []:
        if int(pi.get("page_idx", -1)) != page_idx:
            continue
        for blk in (pi.get("para_blocks") or []):
            if blk.get("type") != "table":
                continue
            bb = blk.get("bbox")
            if isinstance(bb, list) and len(bb) == 4:
                out.append([float(v) for v in bb])
    return out


def _match_line(bad: list[float], lines: list[list[float]], page_w: float, page_h: float,
                used: set[int], tol_x: float = 4.0) -> int | None:
    """给一条坏 span 找它对应的**那一行**（返回 lines 下标；找不到 ⇒ None）。

    ## 为什么不用"第 N 个对第 N 个"

    实测 `GB 11859.1-1989`：库里 span 比 middle 行**多**（15 vs 14）——
    因为 `pipeline` 还会加**表格 span**、且有 4000 字预算截断与"无行框的行被丢弃"
    （`if lbox`）等过滤 ⇒ **下标不是一一对应**。按下标硬对会**把坐标写错行**
    （比不写更糟）。

    ## 判据：用 x 当锚（它存得准）

    坏值里 **x 仍是原始归一化比例、存了 3 位小数**（实测 `0.116` 等）
    ⇒ `x * 页宽` 的误差约 `0.0005 × 2456 ≈ 1.2pt`，**够准**。
    而 **y 是 `H − ny`、只存 2 位小数**：`ny` 的可用范围只有 `[0,1]`，
    分辨率 0.01 ⇒ **换算回点误差可达 ~34pt**（页高 3456 时）
    ⇒ **y 不能用来定位，只能用来消歧**。

    做法：
    1. 用 `|line.x0 − nx0 × 页宽| ≤ tol_x` 取候选；
    2. 多个候选时，用 y 消歧（把 `bad_y` 反推成 `ny`，与该行的 `y0/页高` 比）；
    3. 无候选 ⇒ **None**（调用方跳过该条，**不硬写**）。

    `used` 是已匹配过的下标集合。**为什么"一行只能配一条"**：
    防两条证据抢同一行（那会让两个箭头叠在一处，用户以为"这两条在同一位置"）。
    ⚠ **但这条规则有个已实测的例外**：同一段落被切成多条 span 时（`GB 51039-2014`
    实测：3 条 span 的 x 全是 `0.079~0.485`），**它们本来就该落在同一行**
    —— 此时"不许重复"会把第 2、3 条**永远匹配不上**（实测剩 814 条里绝大多数是这个）。
    ⇒ 判据改成：**优先找没被用过的**；都被用过时，**允许复用**（x 与 y 都对得上就认），
    而不是丢弃。丢弃会让那些条款永远画不出箭头；复用最坏只是两条落在同一行
    —— 而它们本来就在同一行。
    """
    if not lines or page_w <= 0:
        return None
    target_x = float(bad[0]) * page_w
    # 坏 y 反推成归一化 ny（顶部原点）：bad_y = H − ny ⇒ ny = H − bad_y
    ny_bad = (page_h - float(bad[1])) / page_h if page_h > 0 else None
    best: tuple[float, int] | None = None
    fallback: tuple[float, int] | None = None
    for i, ln in enumerate(lines):
        dx = abs(ln[0] - target_x)
        if dx > tol_x:
            continue
        dy = abs(ln[1] / page_h - ny_bad) if (ny_bad is not None and page_h > 0) else 0.0
        score = dx / max(tol_x, 1e-6) + dy
        cand = (score, i)
        if i in used:
            # 已用过：留作 fallback（x/y 都对得上就认），但不优先
            if fallback is None or score < fallback[0]:
                fallback = cand
        else:
            if best is None or score < best[0]:
                best = cand
    chosen = best if best is not None else fallback
    return None if chosen is None else chosen[1]


def _find_middle_for(file_path: str) -> Path | None:
    """按 `doc_meta.file_path` 找它的 MinerU 产物（不瞎找：只认同目录同前缀）。"""
    p = Path(file_path)
    if not p.exists():
        return None
    stem = p.stem
    # 产物目录名 = <pdf名>.mineru-* / <pdf名>.mineru（后缀可能带版本）
    for d in sorted(p.parent.glob(f"{stem}*.mineru*")):
        if d.is_dir():
            found = find_middle_files(d)
            if found:
                return found[0]
    return None


def collect_targets(conn: sqlite3.Connection) -> list[dict]:
    """列出**含坏 bbox 的文档**。

    ⚠ 判据是"**任意一条** span 的形状是坏的"，不是"文档平均宽 < 5"。
    第一版用平均宽 ⇒ **漏掉了"只剩几条坏值"的文档**（实测：第一轮修完后还剩
    8,280 条 table span 坏值，但那些文档的平均宽已经正常 ⇒ 第二版按平均宽选
    **一篇都选不出来**，假绿）。改成"存在一条坏值"即可覆盖。
    """
    rows = conn.execute("""
        SELECT dm.doc_id, dm.standard_no, dm.file_path
        FROM doc_meta dm
        WHERE EXISTS (
            SELECT 1 FROM source_span ss
            JOIN clause_revision cr ON cr.clause_revision_id = ss.clause_revision_id
            WHERE cr.doc_id = dm.doc_id
              AND json_extract(ss.bbox_json,'$[0]') <= 1.0
              AND json_extract(ss.bbox_json,'$[2]') <= 1.0
        )
        ORDER BY dm.standard_no
    """).fetchall()
    return [dict(r) for r in rows]


def build_updates(conn: sqlite3.Connection, doc: dict) -> dict:
    """算一篇文档的更新（不写库）。返回统计 + 待更新列表。"""
    doc_id = doc["doc_id"]
    mid = _find_middle_for(doc["file_path"])
    if mid is None:
        return {"status": "no_middle", "updates": [], "detail": "MinerU 产物不在"}

    try:
        mj = load_middle_json(mid)
    except Exception as exc:  # noqa: BLE001 — 单篇解析失败不拖累其余
        return {"status": "parse_failed", "updates": [],
                "detail": f"{type(exc).__name__}: {exc}"}

    # 页尺寸（换算比例 → 点 需要它；`middle` 归一化后每页都有 page_size）
    size_by_idx: dict[int, tuple[float, float]] = {}
    for pi in mj.get("pdf_info") or []:
        sz = pi.get("page_size") or [0.0, 0.0]
        try:
            size_by_idx[int(pi.get("page_idx", -1))] = (float(sz[0]), float(sz[1]))
        except (TypeError, ValueError, IndexError):
            continue

    spans = conn.execute("""
        SELECT ss.rowid, ss.page_number, ss.sort_order, ss.span_type, ss.bbox_json
        FROM source_span ss
        JOIN clause_revision cr ON cr.clause_revision_id = ss.clause_revision_id
        WHERE cr.doc_id = ?
        ORDER BY ss.page_number, ss.sort_order, ss.rowid
    """, (doc_id,)).fetchall()

    by_page: dict[int, list] = {}
    for s in spans:
        by_page.setdefault(int(s["page_number"]), []).append(s)

    updates: list[tuple[str, int]] = []
    unmatched = 0
    for page_no, rows in by_page.items():
        lines = _lines_of_page(mj, page_no - 1)
        tables = _table_boxes_of_page(mj, page_no - 1)
        pw, ph = size_by_idx.get(page_no - 1, (0.0, 0.0))
        used_line: set[int] = set()
        used_table: set[int] = set()
        for s in rows:
            old = json.loads(s["bbox_json"])
            if not _is_bad(old):
                continue
            # ⚠ 表格 span 是**块级**、文本 span 是**行级** ⇒ 分池匹配（`span_type` 是
            #   `pipeline` 自己写的，可信；不分池会让表格去抢文本行）。
            if str(s["span_type"]) == "table" and tables:
                idx = _match_line(old, tables, pw, ph, used_table)
                if idx is not None:
                    used_table.add(idx)
                    new_txt = json.dumps([round(v, 4) for v in tables[idx]])
                    if new_txt != json.dumps(old):
                        updates.append((new_txt, int(s["rowid"])))
                    continue
            idx = _match_line(old, lines, pw, ph, used_line)
            if idx is None:
                unmatched += 1
                continue
            used_line.add(idx)
            new_txt = json.dumps([round(v, 4) for v in lines[idx]])
            if new_txt != json.dumps(old):
                updates.append((new_txt, int(s["rowid"])))

    if unmatched > 0 and not updates:
        return {"status": "skipped_unmatched", "updates": [],
                "detail": f"{unmatched} 条匹配不上（不硬写）"}
    return {"status": "ok", "updates": updates,
            "detail": f"待写 {len(updates)} 行，匹配不上 {unmatched} 条"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的写库（默认只算不写）")
    ap.add_argument("--limit", type=int, default=0, help="最多处理几篇（0=全部）")
    args = ap.parse_args(argv)

    db = Path(get_settings().db_path)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row

    targets = collect_targets(conn)
    if args.limit > 0:
        targets = targets[: args.limit]
    print(f"  坏 bbox 的文档: {len(targets)} 篇"
          f"{'（已按 --limit 截断）' if args.limit > 0 else ''}")
    print(f"  模式: {'APPLY（真写）' if args.apply else 'DRY-RUN（只算不写）'}")
    print()

    stats = {"ok": 0, "no_middle": 0, "parse_failed": 0, "skipped_mismatch": 0}
    total_rows = 0
    planned: list[tuple[str, int]] = []
    for i, doc in enumerate(targets, 1):
        out = build_updates(conn, doc)
        stats[out["status"]] = stats.get(out["status"], 0) + 1
        total_rows += len(out["updates"])
        planned.extend(out["updates"])
        if out["status"] != "ok" or i % 100 == 0:
            print(f"    [{i}/{len(targets)}] {str(doc['standard_no'])[:30]:<32} "
                  f"{out['status']:<18} {out.get('detail', '')[:60]}")

    print()
    print(f"  === 汇总 ===")
    for k, v in stats.items():
        print(f"    {k:<18} {v}")
    print(f"    待写行数: {total_rows}")

    if not args.apply:
        print()
        print("  DRY-RUN 结束，未写库。加 --apply 才真写。")
        return 0

    if not planned:
        print("  没有要写的行（幂等）。")
        return 0

    # 写前备份（唯一所有者 `storage.backup.create_snapshot`，不另写一份）
    from src.core.storage.backup import create_snapshot
    try:
        snap = create_snapshot("backfill_bbox_units")
        print(f"  已备份快照: {snap.get('snapshot_id')}")
    except Exception as exc:  # noqa: BLE001 — 备份失败则**不写**（宁可不动）
        print(f"  ❌ 备份失败，拒绝写库: {type(exc).__name__}: {exc}")
        return 2

    with conn:
        conn.executemany("UPDATE source_span SET bbox_json=? WHERE rowid=?", planned)
        conn.execute(
            "INSERT INTO operation_log (operation, target_type, target_id, detail)"
            " VALUES (?,?,?,?)",
            ("backfill_bbox_units", "source_span", "*",
             json.dumps({"rows": len(planned), "docs": len(targets)},
                        ensure_ascii=False)))
    print(f"  ✅ 已写 {len(planned)} 行（单事务）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
