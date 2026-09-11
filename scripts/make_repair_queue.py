# -*- coding: utf-8 -*-
r"""修复队列生成器：从 DB 找出条款坍缩文档（≤1 条或无 normal 条款），
过滤 results.jsonl 生成 repair_queue.jsonl，供 campaign_driver -Jsonl 复用。

用法（修复批次开始前运行）：
    python scripts/make_repair_queue.py
输出：
    D:\AI\work space\标准\体检结果\repair_queue.jsonl
    控制台打印坏文档统计。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import get_settings  # noqa: E402
from src.core.storage.sqlite_db import get_db_connection  # noqa: E402

RESULTS = Path(r"D:\AI\work space\标准\体检结果\results.jsonl")
OUT = Path(r"D:\AI\work space\标准\体检结果\repair_queue.jsonl")


def main() -> int:
    conn = get_db_connection()
    # 坏文档判定 1：clause_revision 总数 ≤1，或 normal 条款数为 0（只有前置/附录）
    rows = conn.execute(
        "SELECT d.doc_id, d.standard_no, d.standard_name,"
        "       COALESCE(c.n, 0) AS n_total, COALESCE(c.n_norm, 0) AS n_norm"
        " FROM doc_meta d"
        " LEFT JOIN (SELECT doc_id, COUNT(*) AS n,"
        "                    SUM(CASE WHEN content_type='normal' THEN 1 ELSE 0 END) AS n_norm"
        "            FROM clause_revision GROUP BY doc_id) c ON c.doc_id = d.doc_id"
        " WHERE COALESCE(c.n, 0) <= 1 OR COALESCE(c.n_norm, 0) = 0"
    ).fetchall()
    broken = {r["standard_no"]: r["doc_id"] for r in rows}
    n_collapse = len(broken)
    # 坏文档判定 2（E8 闸门 2026-08-28）：表格数值污染——normal 条款号首段
    # 为 0 或 ≥100（真实 GB 标准章号 ∈1..60）。
    polluted: dict[str, str] = {}
    for r in conn.execute(
        "SELECT doc_id, clause_number FROM clause_revision"
        " WHERE content_type='normal'"
    ):
        first = (r["clause_number"] or "").split(".", 1)[0]
        if first.isdigit() and (int(first) == 0 or int(first) >= 100):
            polluted[r["doc_id"]] = r["doc_id"]
    # 坏文档判定 3（E9 乱码 2026-08-28）：正文乱码字符占比 >15%（cid 错位字体
    # 第三形态：拉丁扩展/泰米尔/Ext-A），需转 OCR 重做。
    import re as _re
    _GARBAGE_RUN = _re.compile(r"([^\x00-\x7f\u4e00-\u9fff\u3000-\u303f\uff00-\uffef])\1{11,}")

    def _garbage_ratio(text: str) -> float:
        if not text:
            return 0.0
        weird = sum(1 for ch in text if not (ch.isascii() or 0x4E00 <= ord(ch) <= 0x9FFF
                                             or 0x3000 <= ord(ch) <= 0x303F
                                             or 0xFF00 <= ord(ch) <= 0xFFEF
                                             or ord(ch) in (0x00B7, 0x00D7, 0x00B0, 0x00AE,
                                                            0x2013, 0x2014, 0x2015, 0x2018,
                                                            0x2019, 0x201C, 0x201D, 0x2022,
                                                            0x2026, 0x2122)))
        return weird / len(text)

    for r in conn.execute(
        "SELECT doc_id, GROUP_CONCAT(SUBSTR(content_text,1,400), '') AS blob "
        "FROM clause_revision WHERE content_type='normal' GROUP BY doc_id"
    ).fetchall():
        blob = r["blob"] or ""
        if len(blob) >= 100 and (_garbage_ratio(blob) > 0.15 or _GARBAGE_RUN.search(blob)):
            polluted[r["doc_id"]] = r["doc_id"]
            continue
        # 判据四（E9b，GB/T 35210.1-2023 实测）：cid 错位第四形态——汉字被映射
        # 为 ASCII 拉丁/标点（"34.567.589.:;) a)*<'*!'…），无怪字符无长跑。
        # 中文国标正文 CJK 占比 <5%（blob ≥300 字）即判乱码；
        # 数字位错位（!"#$%&'()* 占比 >5%）为同族信号。
        if len(blob) >= 300:
            cjk = sum(1 for ch in blob[:6000] if "\u4e00" <= ch <= "\u9fff")
            shift = sum(1 for ch in blob[:6000] if 0x21 <= ord(ch) <= 0x2A)
            head = blob[:6000]
            if cjk / len(head) < 0.05 or shift / len(head) > 0.05:
                polluted[r["doc_id"]] = r["doc_id"]
    if polluted:
        marks = ",".join("?" * len(polluted))
        for r in conn.execute(
            f"SELECT doc_id, standard_no FROM doc_meta WHERE doc_id IN ({marks})",
            tuple(polluted),
        ):
            broken.setdefault(r["standard_no"], r["doc_id"])
    print(f"DB 坏文档：坍缩 {n_collapse} 个 + E8数值污染/E9乱码 {len(polluted)} 个"
          f" = 合计去重 {len(broken)} 个")

    if not RESULTS.exists():
        print(f"缺少队列源文件：{RESULTS}")
        return 1
    kept, total = 0, 0
    with OUT.open("w", encoding="utf-8") as out:
        for line in RESULTS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            total += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("standard_no") in broken:
                out.write(line + "\n")
                kept += 1
    matched = len(broken) - (len(broken) - kept)
    print(f"repair_queue.jsonl：{kept} 条（源 {total} 条；DB 坏文档中 {matched} 个有对应队列记录）")
    no_pdf = [k for k in broken if k not in {
        json.loads(l).get("standard_no") for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()
    }]
    if no_pdf:
        print(f"⚠ {len(no_pdf)} 个坏文档无队列记录（本地缺 PDF 或标准号不一致），示例：{no_pdf[:5]}")
    print(f"修复批次启动：pwsh -File scripts\\campaign_driver.ps1 -Jsonl \"{OUT}\" -StartSkip 0 -SliceSize 1000 -EndCap {kept} -ProgressLog <log>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
