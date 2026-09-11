# -*- coding: utf-8 -*-
"""初始化 debug_loop 战役状态（数据区 %APPDATA%/KnowledgeStation/debug_loop）。"""
import json
import os
from pathlib import Path

camp = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "debug_loop"
camp.mkdir(parents=True, exist_ok=True)

init = {
    "known_issues.json": {"issues": [], "three_strikes": [], "passes": []},
    "passed_manifest.json": {"passed": [], "consecutive": 0, "last_status": "init"},
    "state.json": {"cursor_index": 0, "current_pdf": None, "rounds": [],
                   "started_at": None},
    "debug_log.txt": "# KnowledgeStation 排版校验 Debug Loop log\n",
}
for name, payload in init.items():
    p = camp / name
    if not p.exists():
        if name.endswith(".json"):
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                         encoding="utf-8")
        else:
            p.write_text(payload, encoding="utf-8")
    print(f"  {name}: {p}")
print("campaign dir:", camp)
