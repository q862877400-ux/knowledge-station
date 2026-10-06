"""看清 MinerU **4.0** 的 `middle_json` 结构 —— 判断"能不能加一层兼容"还是"必须换解析"。

## 背景（本轮实测）
 `pipeline.load_middle_items` 读的是 `mj.get("pdf_info", [])` —— 那是 **MinerU 3.4 的键**。
 4.0 的 middle_json 顶层是 `['metadata','extensions','pages','is_full_document','schema','schema_version']`
 ⇒ **没有 `pdf_info`** ⇒ `.get(..., [])` 给空列表 ⇒ **静默返回 0 条、不报错**。

本脚本只读，回答：
 ① 一本标准里**到底有哪些产物文件**（也许有比 middle_json 更合适的入口，如 `structured_content.json`）；
 ② 4.0 的 `pages` 里**每个元素是什么结构**（能不能映射到 3.4 的 `pdf_info[i]`）；
 ③ `structured_content.json` 的结构（是否本来就接近"阅读顺序条目"）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\28-mineru40-structure.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "mineru40-structure.json"
GB_ROOT = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
SUFFIX = ".mineru-4.0.10-vlm"


def keytree(o, depth=0, maxd=3):
    """缩略打印结构：键 → 类型 / 列表长度。"""
    pad = "  " * depth
    if isinstance(o, dict):
        for k, v in list(o.items())[:14]:
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}: {type(v).__name__}" + (f"[{len(v)}]" if isinstance(v, list) else ""))
                if depth < maxd:
                    keytree(v[0] if isinstance(v, list) and v else v, depth + 1, maxd)
            else:
                s = str(v)
                print(f"{pad}{k}: {type(v).__name__} = {s[:60]}")
    elif isinstance(o, list):
        print(f"{pad}[list len={len(o)}]")
        if o and depth < maxd:
            keytree(o[0], depth + 1, maxd)


def main() -> int:
    dirs = [d for d in GB_ROOT.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)]
    if not dirs:
        print("⛔ 没找到 MinerU 产物目录")
        return 1
    d = dirs[0]
    print(f"样板目录：{d.name}\n")

    files = sorted(p for p in d.rglob("*") if p.is_file())
    print("=== ① 产物文件清单 ===")
    for p in files[:20]:
        print(f"    {p.relative_to(d)}   {p.stat().st_size/1024:.1f} KB")
    top_files = [p for p in files if p.parent == d]
    print(f"    （根下文件 {len(top_files)} 个；images/ 下 {len(files)-len(top_files)} 张）\n")

    out = {"sample_dir": d.name, "files": [str(p.relative_to(d)) for p in files[:30]]}

    for name in ("middle_json.json", "structured_content.json"):
        p = d / name
        if not p.exists():
            continue
        raw = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        print(f"=== ②③ {name} 结构（前 3 层）===")
        keytree(raw, 0, 3)
        print()
        out[name + "_keys"] = list(raw.keys()) if isinstance(raw, dict) else f"list[{len(raw)}]"
        if isinstance(raw, dict) and "pages" in raw and raw["pages"]:
            pg = raw["pages"][0]
            out["pages0_keys"] = list(pg.keys()) if isinstance(pg, dict) else type(pg).__name__
            print(f"    pages[0] 的键 = {out['pages0_keys']}")
            if isinstance(pg, dict):
                for k, v in list(pg.items())[:10]:
                    if isinstance(v, list) and v:
                        print(f"      pages[0].{k}[0] 键 = "
                              f"{list(v[0].keys()) if isinstance(v[0], dict) else type(v[0]).__name__}")
        if isinstance(raw, list) and raw:
            out["list0_keys"] = list(raw[0].keys()) if isinstance(raw[0], dict) else type(raw[0]).__name__
            print(f"    列表首元素的键 = {out['list0_keys']}")
        print()

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
