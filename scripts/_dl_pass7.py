# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.debug_loop_driver import record_pass, next_book  # noqa: E402

record_pass("GB/T1003-2016",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1003-2016 家用和类似用途三相插头插座 型式、基本参数和尺寸.pdf",
            1)
b = next_book()
print("next:", (b["std_no"] + " | " + b["rel"]) if b else "NO_MORE")
