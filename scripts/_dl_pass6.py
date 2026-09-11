# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.debug_loop_driver import record_pass, record_issue, next_book  # noqa: E402

record_pass("GB/T10000-2023",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 10000-2023 中国成年人人体尺寸.pdf",
            1)
record_issue("C-扫描件图呈现空白", "GB/T10000-2023", "...",
             "扫描件附录图 A.3/A.4/A.5 呈空白：图对象(asset)未完整注入渲染(图注有、图缺失)。扫描件图通道短板(figure/asset)，内容(序号/术语/图注)保真")
b = next_book()
print("next:", (b["std_no"] + " | " + b["rel"]) if b else "NO_MORE")
