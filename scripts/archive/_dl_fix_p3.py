# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.debug_loop_driver import record_fail, record_issue, status  # noqa: E402

record_fail("GB/T1003-2016",
            r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1003-2016 家用和类似用途三相插头插座 型式、基本参数和尺寸.pdf",
            1,
            note="逐页核对发现：图5-9 未注入渲染(figure_html=0)——fitz 文本层路径无图像对象+图注入通道未接入→保字但丢图=排版不完美")
record_issue("C-图未注入(fitz路径)", "GB/T1003-2016", "...",
             "文本层(fitz)路径未注入图5-9(及表格图示)：fitz blocks 无图像对象，figure_locator/figure_html 未接入 fitz 路径。系'文本层→fitz保真'切换的副作用(保字但丢图)，需在 fitz 路径接入 figure_locator 图注入。")
status()
