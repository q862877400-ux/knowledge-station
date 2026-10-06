"""MinerU 4.0 `blocks` 的**块类型与块内容**明细 —— 做兼容层要用到的最后一块拼图。

已知（上一步实测）4.0 与 3.4 的对应关系：
 `pages` ↔ `pdf_info` · `pages[i].blocks` ↔ `pdf_info[i].para_blocks` ·
 页尺寸在 `extensions.docvortex_layout.pages[i].width_pt/height_pt` · 块内容在 `content`。

本脚本量：
 ① **块类型有哪些、各多少**（`header`/`text`/`table`/`image`… 4.0 的枚举是什么）；
 ② **表格块**长什么样（`content` 里有没有 html？3.4 是在 `spans[].html`）；
 ③ **文本块**的 `content` 是字符串还是对象列表（3.4 是 `lines[].spans[].content`）；
 ④ 对照：3.4 时代的解析器要找的 `table_caption`/`table_body` 在 4.0 里对应什么。

只读源目录。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\29-mineru40-blocks.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "mineru40-blocks.json"
GB_ROOT = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
SUFFIX = ".mineru-4.0.10-vlm"


def main() -> int:
    dirs = [d for d in GB_ROOT.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)][:30]
    types = Counter()
    inner_types = Counter()
    samples = {}
    tbl_sample = None
    n_pages = 0
    for d in dirs:
        p = d / "middle_json.json"
        if not p.exists():
            continue
        raw = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        for pg in raw.get("pages", []):
            n_pages += 1
            for b in pg.get("blocks", []):
                t = b.get("type")
                types[t] += 1
                c = b.get("content")
                if isinstance(c, list):
                    for it in c[:3]:
                        if isinstance(it, dict):
                            inner_types[it.get("type")] += 1
                if t not in samples:
                    samples[t] = {k: (v if not isinstance(v, (list, dict)) else
                                      (f"{type(v).__name__}[{len(v)}]")) for k, v in b.items()}
                if t in ("table", "image") and tbl_sample is None:
                    cc = b.get("content")
                    if isinstance(cc, list):
                        for it in cc:
                            if isinstance(it, dict) and str(it.get("content", ""))[:1] == "<":
                                tbl_sample = {"dir": d.name[:50], "type": t, "inner": it}
                                break
    print(f"[blk] 扫了 {len(dirs)} 本 / {n_pages} 页")
    print(f"\n[blk] 块类型分布：")
    for k, v in types.most_common():
        print(f"    {k!r:16s} {v:6d}   样例字段：{samples.get(k)}")
    print(f"\n[blk] content 内层类型分布：{dict(inner_types.most_common(10))}")
    if tbl_sample:
        s = json.dumps(tbl_sample, ensure_ascii=False)[:900]
        print(f"\n[blk] 表格/图片块样例（找 html）：\n{s}")
    else:
        print("\n[blk] ⚠ 没找到带 html 的表格块（3.4 是在 spans[].html；4.0 可能换成别的形态）")

    OUT.write_text(json.dumps({
        "why": "MinerU 4.0 的块类型与块内容明细（做 3.4 兼容层用）",
        "dirs_scanned": len(dirs), "pages": n_pages,
        "block_types": dict(types), "inner_types": dict(inner_types),
        "block_samples": samples, "table_sample": tbl_sample,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
