# -*- coding: utf-8 -*-
"""单文档入库试跑：判定 `run_full_ingest` 会不会**复用本循环的产物**。

**为什么先跑 1 部**：`run_full_ingest(pdf, ..., reuse_parse=True)` 的注释说它复用
的是「**既有文档**＝同 file_hash 或同 standard_no」的产物——那**不是**我们循环产出的
`parse_out/_land_key(std_no)`。若它找不到我们的产物，就会**重新解析**（deep 模式
单部可达 900s 超时）→ 对 8,484 部下重手等于白跑一遍、且可能重复入库。
故先用**最小的一部**试跑，看返回 status 再决定。

只跑 1 部；`force_deep=False`（避免 900s 深解析）、`reuse_parse=True`。
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "var" / "ocr-loop"))

MAN = ROOT / "var" / "ocr-loop" / "evolve" / "ingest_manifest.json"
m = json.loads(MAN.read_text(encoding="utf-8"))
items = m["items"]
print(f"manifest 可入库条目: {len(items)}")

# 挑最小页数的一部（pages 已知）
cand = sorted([i for i in items if i.get("pages")],
              key=lambda x: int(x["pages"]))[0]
print(f"试跑对象: {cand['std_no']}  pages={cand['pages']}")
print(f"  产物目录: {cand['product_dir']}")

# 找源 PDF（按 std_no 匹配语料）
import next_batch as NB  # noqa: E402
target = cand["std_no"]
pdf = None
for p in NB.CORPUS.rglob("*.pdf"):
    if p.stem == target:
        pdf = p
        break
if pdf is None:
    print("❗ 语料里找不到该 PDF，放弃试跑")
    sys.exit(1)
print(f" 源 PDF  : {pdf}")

from src.core.ingestion.pipeline import run_full_ingest  # noqa: E402

parts = target.split(" ", 1)
std_no = parts[0]
std_name = parts[1] if len(parts) > 1 else std_no
print(f"\n调用 run_full_ingest(standard_no={std_no!r}, force_deep=False, reuse_parse=True) …")
res = run_full_ingest(Path(pdf), std_no, std_name,
                      force_deep=False, reuse_parse=True)
print("\n=== 返回 ===")
print(json.dumps(res, ensure_ascii=False, indent=1, default=str)[:1500])
