"""批量重入库（reingest）：对库内所有有 PDF 原件的标准类文档，
用当前最新管线重新解析入库（含行内公式修复/折行清洗/CCS 自动查询等全部改进）。

用途：管线升级后一次性修复存量数据——新进文件走正常入库自动享受同样质量。
- 保留原 standard_no/名称/分类标签（domain_tags 含 CCS 不重复查）
- 旧文档在新文档就绪后自动删除（收藏/批注绑 clause_key 自动延续）
- 跳过 law-text 直灌文档（无 PDF 原件）与 file_path 已失效的文档

用法：.venv/Scripts/python scripts/reingest_all.py [--dry-run]
"""
import sys
import io
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\AI\work space\zcode")

from src.core.storage.sqlite_db import get_db_connection


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只列出将重入库的文档")
    args = ap.parse_args()

    from src.core.ingestion.pipeline import run_full_ingest
    import json

    conn = get_db_connection()
    rows = conn.execute(
        "SELECT doc_id, standard_no, standard_name, doc_type, domain_tags, file_path"
        " FROM doc_meta WHERE doc_type='standard' ORDER BY standard_no").fetchall()

    targets = []
    for r in rows:
        fp = r["file_path"] or ""
        if not fp or fp.startswith("law-text"):
            continue
        from pathlib import Path
        if not Path(fp).exists():
            print(f"跳过（PDF 不存在）: {r['standard_no']} -> {fp}")
            continue
        try:
            tags = json.loads(r["domain_tags"] or "[]")
        except Exception:
            tags = []
        targets.append((r["doc_id"], r["standard_no"], r["standard_name"], tags, fp))

    print(f"待重入库: {len(targets)} 个文档\n")
    if args.dry_run:
        for did, no, name, _, fp in targets:
            print(f"  {no} | {name} | {fp}")
        return 0

    ok = fail = 0
    for did, std, name, tags, fp in targets:
        print(f"→ 重入库 {std} ...", flush=True)
        try:
            from pathlib import Path
            out = run_full_ingest(
                Path(fp), std, name, doc_type="standard",
                domain_tags=tags, legal_hierarchy="GB", reingest=True)
            status = out.get("status")
            if status == "ok":
                ok += 1
                print(f"   ✅ {status} clauses={out.get('total_clauses')} "
                      f"replaced={out.get('replaced_doc_id')}")
            else:
                fail += 1
                print(f"   ❌ {status}: {out.get('message', '')[:80]}")
        except Exception as e:
            fail += 1
            print(f"   ❌ 异常: {str(e)[:100]}")

    print(f"\n完成: 成功 {ok} / 失败 {fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
