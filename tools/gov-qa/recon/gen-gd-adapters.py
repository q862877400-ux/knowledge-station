"""从 gd-dept-domains-probed.json 机械生成广东厅局薄壳适配器 + 重写 ADAPTERS 登记表。

规则：
 · 只生成探测命中且 total>0 的域名（total=0 的空台不建）；
 · key = "gd-<dom>"；文件名 adapters/gd_<dom>.py；
 · 已有适配器的 7 个域名（yjgl/gdee/hrss/td/wsjkw/eea/drc）跳过；
 · `__init__.py` 的 ADAPTERS 里 gd-* 行整体重生成（其他行原样保留）。
生成物是机械的（同一模板），回头改引擎一处、37 个壳全部生效。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADAPTERS_DIR = HERE.parent / "adapters"
PROBED = HERE / "gd-dept-domains-probed.json"

#: 已有薄壳的域名 → 现有 key（跳过生成，避免重复）
EXISTING = {
    "yjgl": "gd-yj", "gdee": "gd-st", "hrss": "gd-hr", "td": "gd-jt",
    "wsjkw": "gd-ws", "eea": "gd-jy", "drc": "gd-fg",
}

TEMPLATE = '''"""适配器：**{name}**（广东 hdjlpt 同款平台）。

2026-10-07 探测年窗 total={total}（recon/gd-dept-domains-probed.json）。
引擎见 `_gd_hdjlpt_common.py`；生成器 `recon/gen-gd-adapters.py`（勿手改本壳）。
"""
from __future__ import annotations

from adapters._gd_hdjlpt_common import harvest_gd

SITE = {{
    "key": "{key}",
    "name": "{name}",
    "kind": "api",
    "level": "province",
    "entry": "{base}/hdjlpt?via=pc",
    "status": "ok",
    "note": "hdjlpt letter/pubList；探测年窗 total={total}",
}}

BASE = "{base}"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该单位留言选登（问题+答复全文）。"""
    return harvest_gd(fetch, SITE=SITE, BASE=BASE, limit=limit)
'''


def main() -> int:
    rows = json.loads(PROBED.read_text(encoding="utf-8"))
    hits = [r for r in rows
            if r.get("total") is not None and r["total"] > 0
            and r["dom"] not in EXISTING]
    print(f"待生成 {len(hits)} 个（跳过已有 {len(EXISTING)} 个）")

    gd_lines = []
    for r in hits:
        dom, name, key = r["dom"], r["name"], f"gd-{r['dom']}"
        path = ADAPTERS_DIR / f"gd_{dom}.py"
        path.write_text(
            TEMPLATE.format(name=name, key=key, total=r["total"], base=r["base"]),
            encoding="utf-8")
        gd_lines.append(f'    "{key}": "adapters.gd_{dom}",  # {name}（年窗 {r["total"]}）')
        print(f"  + {key} <- {name} ({r['total']}/年窗)")

    # 重写 __init__.py 的 ADAPTERS：非 gd-* 行保留原序；已有 7 厅行重插；新壳追加
    init = ADAPTERS_DIR / "__init__.py"
    text = init.read_text(encoding="utf-8")
    m = re.search(r"(ADAPTERS: dict\[str, str\] = \{\n)(.*?)(\n\})", text, re.S)
    assert m, "ADAPTERS 块没找到"
    body = m.group(2)
    non_gd = [ln for ln in body.splitlines() if not re.match(r'\s*"gd-', ln)]
    existing_lines = [
        f'    "{key}": "adapters.{mod}",  # （已有薄壳，勿重复生成）'
        for dom, key in EXISTING.items()
        for mod in ["gd_sthj", "gd_yjgl", "gd_hrss", "gd_jt",
                    "gd_wsjkw", "gd_eea", "gd_drc"]
        if {"yjgl": "gd_yjgl", "gdee": "gd_sthj", "hrss": "gd_hrss",
            "td": "gd_jt", "wsjkw": "gd_wsjkw", "eea": "gd_eea",
            "drc": "gd_drc"}[dom] == mod
    ]
    existing_map = {"yjgl": "gd_yjgl", "gdee": "gd_sthj", "hrss": "gd_hrss",
                    "td": "gd_jt", "wsjkw": "gd_wsjkw", "eea": "gd_eea",
                    "drc": "gd_drc"}
    existing_lines = [f'    "{EXISTING[dom]}": "adapters.{mod}",'
                      f'  # （已有薄壳，勿重复生成）'
                      for dom, mod in existing_map.items()]
    new_block = (m.group(1) + "\n".join(non_gd).rstrip() + "\n"
                 + "\n".join(existing_lines) + "\n"
                 + "\n".join(gd_lines) + m.group(3))
    new_text = text[:m.start()] + new_block + text[m.end():]
    init.write_text(new_text, encoding="utf-8")
    print(f"[gen] __init__.py 已更新（新 gd 行 {len(gd_lines)} + 已有 {len(existing_lines)}）")

    # 冒烟：import 检查
    import subprocess
    import sys
    r = subprocess.run(
        [str(HERE.parent.parent.parent / ".venv" / "Scripts" / "python.exe"),
         "-c", "import sys; sys.path.insert(0, r'" + str(ADAPTERS_DIR.parent) + "');"
               "import adapters; print(sorted(adapters.ADAPTERS))"],
        capture_output=True, text=True)
    print(r.stdout or r.stderr)
    return 0 if r.returncode == 0 else 1


if __name__ == "__main__":
    main()
