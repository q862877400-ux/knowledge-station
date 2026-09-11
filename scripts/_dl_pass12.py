# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.debug_loop_driver import record_pass, record_issue, status  # noqa: E402

record_pass("GB/T1031-2009",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1031-2009 产品几何技术规范（GPS） 表面结构 轮廓法 表面粗糙度参数及其数值.pdf",
            1)
record_issue("C-表格数值误切(边缘)", "GB/T1031-2009", "...",
             "表值 6.3 残留被 _CLAUSE_GB 误切(rest 非空/_TABULAR_REST 未全挡)；主要表值 12.5/1.6/3.2 已由 _plausible_clause_head rest-空-拒 修复(条款数 47→22)。边缘残留")
stop = status()
print("STOP_MET:", stop)
