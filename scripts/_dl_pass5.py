# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.debug_loop_driver import record_pass, status  # noqa: E402

record_pass("GB/T10-2013",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 10-2013 沉头方颈螺栓.pdf",
            1)
stop = status()
print("STOP_MET:", stop)
