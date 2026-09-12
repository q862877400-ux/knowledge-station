# -*- coding: utf-8 -*-
"""把全量验证结论追加到 final_report.md。"""
import os
from pathlib import Path

camp = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "debug_loop"
fp = camp / "final_report.md"
verify = """

## 八、合入前全量验证结论（2026-09-02）
- 全量 `pytest -q`：**520 passed + 2 failed + 3 skipped**（8 warnings）
- `npx tsc --noEmit`：**0 错误**
- **与改动前基线完全一致**（改动前即 520 + 2 预存 fail + 3 skip），**零回归**；
- 2 个 failed 为**预先存在**的 `tests/test_table_binding.py`（`test_caption_number_must_not_steal_chapter_clauses`、`test_reference_wins_over_physical_position`），与表绑定(C2)逻辑相关，**非本次 6 处 ingestion 改动引入**，建议作为独立项单独审查。

> 结论：本次「正常入库识别流程」6 处通用修复**已验证无回归**，可合入。
"""
with open(fp, "a", encoding="utf-8") as f:
    f.write(verify)
print("appended verify; final_report.md lines:", len(fp.read_text(encoding="utf-8").splitlines()))
