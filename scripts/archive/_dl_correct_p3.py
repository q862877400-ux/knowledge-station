# -*- coding: utf-8 -*-
"""纠正 GB/T 1003-2016：渲染图/表实际正常，撤销误判的 fail，删除误登记的 C-图未注入。"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from scripts.debug_loop_driver import record_pass  # noqa: E402
from scripts.debug_loop_driver import _PASSED, _ISSUES, _dump  # noqa: E402

camp = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "debug_loop"
now = datetime.now().isoformat(timespec="seconds")

# 1) 撤销误判 fail → 改回通过
record_pass("GB/T1003-2016",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1003-2016 家用和类似用途三相插头插座 型式、基本参数和尺寸.pdf",
            1)

# 2) 删除误登记的 C-图未注入(fitz路径)；修正 C-扫描件图呈现空白 说明（渲染 _inject_figs 通道未核，非必然缺口）
ki = json.loads(_ISSUES.read_text(encoding="utf-8"))
ki["issues"] = [i for i in ki["issues"] if i["type"] != "C-图未注入(fitz路径)"]
for i in ki["issues"]:
    if i["type"] == "C-扫描件图呈现空白":
        i["detail"] = ("扫描件附录图 A.3-A.5 在某屏呈空白——但图走 _inject_figs(content ^图N→/figure)通道，"
                       "figure_html=0 属入库资产通道非必需；是否真缺失需核渲染页(而非只查列)，待核。此前登记基于误解。")
        i["updated_at"] = now
_ISSUES.write_text(json.dumps(ki, ensure_ascii=False, indent=2), encoding="utf-8")

# 记录纠正到 debug_log
with open(camp / "debug_log.txt", "a", encoding="utf-8") as f:
    f.write("[%s] 纠正：GB/T1003-2016 渲染图9/图10+表数据完整，实为通过(非图缺口)；撤误判 fail，删误登记 C-图未注入(fitz路径)。教训：核图须看渲染页(_inject_figs)，勿只查 figure_html 列。\n" % now)

print("corrected: GB/T1003-2016 -> PASS, removed C-图未注入(fitz路径), updated C-扫描件图呈现空白(待核)")
