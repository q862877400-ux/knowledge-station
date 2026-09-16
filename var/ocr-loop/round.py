"""OCR 循环任务·工具2：一轮完整循环 = pick → 入库 → OCR 质检 → 台账记录。
用法：python var/ocr-loop/round.py [--pick-json next_pick.json] [--no-ingest]"""
import sys, io, os, json, sqlite3, argparse, time, re
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 原地改，勿包新 wrapper
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
VARDIR = ROOT / "var" / "ocr-loop"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"


def pick() -> dict:
    p = VARDIR / "next_pick.json"
    if not p.exists():
        raise SystemExit("先跑 pick_next.py")
    return json.loads(p.read_text(encoding="utf-8"))


def parse_std_no(stem: str) -> tuple[str, str] | None:
    """文件名 → (标准号, 名称)；提取不到返回 None。

    2026-09-15 修（实测事故）：正则只认 '-'/'—'，不认全角连字符 '－'(U+FF0D)，
    遇 'GB／T 12325－2008 …' 匹配失败 → 退化成「整段文件名当标准号」入库，
    污染 doc_meta（doc_01M2F54NM9GRZWX8W9KAY7HQZV 实证）。现在：
    ① 先把全角／与三种连字符变体归一；② 去掉下载副本后缀 '(1)'；
    ③ 提取不到就返回 None —— 调用方**拒绝入库**（宁缺勿污染）。
    """
    s = stem.replace("／", "/").replace("－", "-").replace("—", "-").replace("–", "-")
    # 年份可两位（老标准 GB/T 12998-91）或四位（GB/T 10002.1-2023）
    m = re.match(r"(GB(?:/T|/Z)?)\s*([\d.]+)\s*-\s*(\d{2}|\d{4})(?![\d.])", s, re.I)
    if not m:
        return None
    hier = m.group(1).upper()
    year = m.group(3)
    if len(year) == 2:                          # 两位数年份 → 四位（GB 惯例 19xx/20xx）
        year = ("19" + year) if int(year) >= 30 else ("20" + year)
    std_no = f"{hier} {m.group(2)}-{year}"
    name = s[m.end():].strip()
    name = re.sub(r"\s*\(\d+\)\s*$", "", name)      # 下载副本后缀 '(1)'
    name = re.sub(r"\s*正式版\s*$", "", name).strip()
    return std_no, (name or std_no)


def ingest(pk: dict) -> dict:
    from src.core.ingestion.pipeline import run_full_ingest
    stem = pk["stem"]
    parsed = parse_std_no(stem)
    if parsed is None:
        print(f"[ingest] 跳过：文件名提取不出标准号 → {stem[:60]}")
        return {"status": "unparsed_number", "_wall_s": 0.0,
                "message": f"文件名提取不出标准号（不入库，防污染 doc_meta）: {stem[:60]}"}
    std_no, name = parsed
    print(f"[ingest] {std_no} | {name}")
    t0 = time.monotonic()
    try:
        r = run_full_ingest(Path(pk["pick"]), std_no, name)
    except Exception as e:  # noqa: BLE001 — 与 bulk.py 同契约：异常转 failed 记录
        r = {"status": "error", "message": f"{type(e).__name__}: {str(e)[:200]}"}
    r["_wall_s"] = round(time.monotonic() - t0, 1)
    return r


def doc_id_of(stem: str) -> str | None:
    parsed = parse_std_no(stem)
    std_no = parsed[0] if parsed else stem
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = conn.execute("SELECT doc_id, standard_no FROM doc_meta").fetchall()
    conn.close()
    tgt = std_no.replace(" ", "")
    for did, no in rows:
        if (no or "").replace(" ", "") == tgt:
            return did
    return None


def qc(doc_id: str) -> dict:
    """OCR 质检：条款级 ocr_confidence 分布 + 低置信条款抽样。
    2026-09-14 轮次 13 起：只统计 content_type='normal' 正文条款——前置说明
    （封面/前言，R65 设计仅参与全文检索）的封面美术字低分是真实识别难度
    但非条款正文质量，污染分位口径（10058/10060/10322.9 三文档实证）。"""
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT clause_revision_id, clause_number, content_text, ocr_confidence, "
        "content_type FROM clause_revision WHERE doc_id=? ORDER BY clause_number",
        (doc_id,)).fetchall()
    body = [r for r in rows if r["content_type"] == "normal"]
    pre = [r for r in rows if r["content_type"] == "前置说明"]
    n = len(body)
    confs = [r["ocr_confidence"] for r in body if r["ocr_confidence"] is not None]
    low = [r for r in body if (r["ocr_confidence"] or 1.0) < 0.85]
    out = {
        "doc_id": doc_id, "clauses": n, "preface_clauses": len(pre),
        "conf_dist": {
            "min": round(min(confs), 4) if confs else None,
            "p50": round(sorted(confs)[len(confs)//2], 4) if confs else None,
            "p95": round(sorted(confs)[int(len(confs)*.05)], 4) if confs else None,
            "low(<0.85)": len(low),
        },
        "low_samples": [
            {"clause": r["clause_number"], "conf": r["ocr_confidence"],
             "head": (r["content_text"] or "")[:240]} for r in low[:8]],
    }
    conn.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ingest", action="store_true")
    args = ap.parse_args()
    pk = pick()
    if args.no_ingest:
        qc_only(pk)
        return
    r = ingest(pk)
    print(f"[ingest] status={r.get('status')} wall={r.get('_wall_s')}s "
          f"doc_id={r.get('doc_id', '?')}")
    # 图形符号类（10001.x 全图标页）与超时类不进 OCR 循环质检池——挑文本型标准
    if r.get("status") not in ("ok", "duplicate"):
        record(pk, r, None)
        mark_tried(pk, note=f"ingest:{r.get('message', '')[:80]}")
        return
    did = r.get("doc_id") or doc_id_of(pk["stem"])
    q = qc(did)
    print(json.dumps(q, ensure_ascii=False, indent=1)[:1500])
    record(pk, r, q)
    mark_tried(pk)


def qc_only(pk):
    did = doc_id_of(pk["stem"])
    print("doc:", did)
    q = qc(did)
    print(json.dumps(q, ensure_ascii=False, indent=1)[:1500])


def mark_tried(pk, note=""):
    tp = VARDIR / "tried.json"
    tried = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else []
    key = re.sub(r"\s+", "", pk["stem"].upper())
    if key not in [re.sub(r"\s+", "", t.upper()) for t in tried]:
        tried.append(pk["stem"])
    tp.write_text(json.dumps(tried, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[tried] {pk['stem']} {note}")


def record(pk, ingest_r, q):
    """台账：var/ocr-loop/ledger.jsonl 逐行 append（成功/失败都记）+ 问题类分类。
    2026-09-15：接入 classify（问题类自动打标），使跨文档同类计数可自动累计。"""
    from classify import classify_qc
    classes = classify_qc(q) if q else {}
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stem": pk["stem"], "status": ingest_r.get("status"),
        "wall_s": ingest_r.get("_wall_s"),
        "message": (ingest_r.get("message") or "")[:120],
        "qc": q,
        "classes": classes,
    }
    with open(VARDIR / "ledger.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print("[ledger] appended", classes or "")


if __name__ == "__main__":
    main()
