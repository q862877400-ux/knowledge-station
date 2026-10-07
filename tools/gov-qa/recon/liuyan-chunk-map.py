"""从 app.js 的 webpack chunk 映射里取「地方领导页」懒加载 chunk 的真实文件名。"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE / "liuyan-js" / "app.3e85d355fec434cc9994.js"

WANT = ["5e170665", "04749eab", "177d6de2", "27afe662", "91a8796a", "e6e8762e"]


def main() -> int:
    t = APP.read_text(encoding="utf-8", errors="replace")
    # 形如 {5e170665:"2a793a25",04749eab:"f9ae1b9b5055a5f4d23e",...}
    best: dict[str, str] = {}
    for m in re.finditer(r"\{((?:\s*\"?[0-9a-f]{8}\"?\s*:\s*\"[0-9a-f]{8,20}\"\s*,?){5,})\}", t):
        pairs = re.findall(r"\"?([0-9a-f]{8})\"?\s*:\s*\"([0-9a-f]{8,20})\"", m.group(1))
        if len(pairs) > len(best):
            best = dict(pairs)
    print("chunk 映射条数:", len(best))
    for k in WANT:
        print(f"  {k} -> {best.get(k)}")
    (HERE / "liuyan-chunk-map.json").write_text(
        json.dumps(best, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    main()
