# -*- coding: utf-8 -*-
"""把审计/自动对账发现但未登记的真实缺失，补进 known_issues.json。"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
camp = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "debug_loop"
ki = json.loads((camp / "known_issues.json").read_text(encoding="utf-8"))
now = datetime.now().isoformat(timespec="seconds")

def add(t, std, detail):
    ki["issues"].append({"type": t, "standard": std, "detail": detail, "updated_at": now})

add("C-公式符号缺失", "GB/T1.1-2020",
    "自动对账(fitz原PDF vs 库content)发现：公式/符号在库文本缺失 [_ ´ ÷ ^ ̄]——组合尖帽/上划线/除号/幂号/下划线等未保留(数学公式符号丢失)，之前未登记。")
add("C-公式符号缺失", "GB/T1028-2018",
    "自动对账发现：公式/符号在库缺失 [_ ´ ± ÷ ^ ̄]——(±, 组合重音, 除号等)，且 prev_p11(≡p12-26)数值页与 orig_p11 计算表数值对不上，未登记。")
add("C-公式符号缺失", "GB/T1029-2021",
    "自动对账(此前被standard_no空格key静默跳过，已修并补跑)发现：公式/符号缺失 [_ ´ ÷ ^ ̄]；99页仅采样10屏(manifest声明)，却记 PASS rounds=1——覆盖不足。")
add("C-图/表题注缺失(待复核)", "GB/T1000-2016",
    "自动对账：图A.1/A.2/A.3、表B.1 疑缺(图题注'图A.\\n1'在PDF、库content/markdown/figure_html无)——可能为拆行假阳性，需复核；且预览prev_p7(图8/9)与orig_p7(表1/2)页序错位。")
(camp / "known_issues.json").write_text(
    json.dumps(ki, ensure_ascii=False, indent=2), encoding="utf-8")
print("registered missing-content issues. total issue types:", len({i['type'] for i in ki['issues']}))
