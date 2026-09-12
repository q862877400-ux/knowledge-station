# -*- coding: utf-8 -*-
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from scripts.debug_loop_driver import record_pass, _ISSUES, _dump  # noqa: E402

record_pass("GB/T1028-2018",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1028-2018 工业余能资源评价方法.pdf",
            1)

# 纠正：C-英文术语空格粘连 误登记（GB/T1028 英文有正常空格，说明 GB/T1008/1019 无空格是原文/字体，非 fitz 通用缺陷）
camp = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "debug_loop"
ki = json.loads(_ISSUES.read_text(encoding="utf-8"))
ki["issues"] = [i for i in ki["issues"] if i["type"] != "C-英文术语空格粘连"]
_ISSUES.write_text(json.dumps(ki, ensure_ascii=False, indent=2), encoding="utf-8")
now = datetime.now().isoformat(timespec="seconds")
with open(camp / "debug_log.txt", "a", encoding="utf-8") as f:
    f.write("[%s] GB/T1028-2018 通过；纠正 C-英文术语空格粘连为误登记(GB/T1028 英文有正常空格，非 fitz 通用)。\n" % now)
print("corrected & pass GB/T1028-2018")
