# -*- coding: utf-8 -*-
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from scripts.debug_loop_driver import record_pass, _ISSUES, next_book  # noqa: E402

record_pass("GB/T1029-2021",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1029-2021 三相同步电机试验方法.pdf",
            1)

# 登记修正：C-型号框/图注呈现 可能非缺口（GB/T1029 公式/图注渲染正常，印证 _inject_figs/公式通道正常）
ki = json.loads(_ISSUES.read_text(encoding="utf-8"))
for i in ki["issues"]:
    if i["type"] == "C-型号框/图注呈现":
        i["detail"] = ("GB/T 1000-2016 4.2 型号框 [1]..[6]+图2/4/6/7 呈现为 (1)(2)/(3)(4)+图注——经 GB/T 1029-2021 公式/图注渲染正常印证，"
                       "_inject_figs/公式通道正常；型号框为文本层提取形态(方框[]→(1)括号)，非注入缺口。待核渲染。")
        i["updated_at"] = datetime.now().isoformat(timespec="seconds")
_ISSUES.write_text(json.dumps(ki, ensure_ascii=False, indent=2), encoding="utf-8")

b = next_book()
print("next:", (b["std_no"] + " | " + b["rel"]) if b else "NO_MORE")
