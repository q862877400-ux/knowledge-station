# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.debug_loop_driver import record_fail, status  # noqa: E402

# 修正：GB/T 10000-2023 附录图 A.3-A.5 空白（图缺失）= 排版不一致 = 不完美 → fail（reset consecutive）
record_fail("GB/T10000-2023",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 10000-2023 中国成年人人体尺寸.pdf",
            1,
            note="扫描件附录图 A.3/A.4/A.5 空白(图对象未注入渲染)——C-扫描件图呈现空白，内容/术语保真但排版图缺失=不完美，待修图通道")
status()
