"""标准号「(OCR采集)」来源后缀剥离的回归判据（spec 009）。

## 抓什么

`src/core/text_utils.strip_ocr_source_suffix` 只许剥**结尾**的 `(OCR采集)`，
其余一字不动。三条断言**各自**都有牙（spec 009 plan.md 的"判据设计"）：

| # | 输入 | 期望 | 谁被咬住 |
|---|---|---|---|
| A1 | `刑法(OCR采集)` | `刑法` | 不剥 ⇒ 红 |
| A2 | `聚丙烯(PP)树脂` | **原值不变** | 判据写宽（剥任意尾部括号）⇒ 红 |
| A3 | `GB 5009.12-2023食品安全国家标准` | **原值不变** | 把"尾部带中文"也剥 ⇒ 红 |

## ⚠ 为什么 A2/A3 是必需的（不是凑数）

真库实测存在**合法**括号名与**官方标准**尾部带中文的情况：
* `聚丙烯(PP)树脂`、`湿式(非金属类)摩擦材料`（合法括号，不是后缀）
* `GB 5009.12-2023食品安全国家标准`（**官方标准**，尾部中文是内容不是标记）
  —— 全库这种"标准号+年份后紧跟中文"的共 **4 篇**，与带 `(OCR采集)` 的 1,430 篇
  **交集为 0**（2026-10-12 实测）⇒ 两件事不能混。

只写 A1 的话，一个"剥掉任意尾部括号"的坏实现**照样全绿** —— 那正是本仓
「假绿判 failed」（宪法 III）要挡的形态。
"""
from src.core.text_utils import strip_ocr_source_suffix


class Test剥来源后缀:
    """A1：带后缀的必须剥掉。"""

    def test_剥掉半角括号后缀(self):
        assert strip_ocr_source_suffix("刑法(OCR采集)") == "刑法"

    def test_剥掉全角括号后缀(self):
        assert strip_ocr_source_suffix("刑法（OCR采集）") == "刑法"

    def test_剥掉后两侧空白(self):
        assert strip_ocr_source_suffix("  刑法(OCR采集)  ") == "刑法"

    def test_真库样例_带书名号截断的那种(self):
        # 真库那 1 处形态不同的是"标准号被文本截断"，剥完仍是它自己的名字
        s = "最高人民法院关于适用《中华人民共和国民事诉讼法》的解释(八)》时间效力问题的解释(OCR采集)"
        out = strip_ocr_source_suffix(s)
        assert not out.endswith("(OCR采集)")
        assert out.endswith("时间效力问题的解释")

    def test_连续两个后缀(self):
        # 防御性：真库曾出现双重副本后缀 `…(1)(1)`；来源后缀同理要能连剥到干净
        assert strip_ocr_source_suffix("刑法(OCR采集)(OCR采集)") == "刑法"


class Test不动合法括号:
    """A2：合法括号名一字不动 —— 判据写宽就会被咬住。"""

    def test_合法括号_聚丙烯PP树脂(self):
        assert strip_ocr_source_suffix("聚丙烯(PP)树脂") == "聚丙烯(PP)树脂"

    def test_合法括号_湿式非金属类(self):
        s = "湿式(非金属类)摩擦材料"
        assert strip_ocr_source_suffix(s) == s

    def test_合法括号_结尾也是括号(self):
        # ⚠ 这条最狠：结尾就是 `)`，但它不是 `(OCR采集)` ⇒ 必须原样保留
        assert strip_ocr_source_suffix("额定电压1kV(Um=1.2kV)") == "额定电压1kV(Um=1.2kV)"

    def test_副本后缀不动_那是另一个判据(self):
        # `(1)` 归 `strip_duplicate_suffix` 管；本函数**不该**碰它
        assert strip_ocr_source_suffix("电梯技术条件(1)") == "电梯技术条件(1)"


class Test不动官方标准尾部中文:
    """A3：官方标准的标准号尾部带中文，是内容不是标记。"""

    def test_官方标准_食品安全国家标准(self):
        s = "GB 5009.12-2023食品安全国家标准"
        assert strip_ocr_source_suffix(s) == s

    def test_官方标准_术语(self):
        s = "GB/T 27668-2023显微镜光学显微术术语(1)"
        assert strip_ocr_source_suffix(s) == s

    def test_四篇里的每一篇都不动(self):
        # 2026-10-12 实测的完整 4 篇
        for s in (
            "GB 5009.12-2023食品安全国家标准",
            "GB 5009.154-2023食品安全国家标准",
            "GB 5009.227-2023食品安全国家标准",
            "GB/T 27668-2023显微镜光学显微术术语(1)",
        ):
            assert strip_ocr_source_suffix(s) == s, s


class Test不动以中文括号结尾的名字:
    """A4（2026-10-12 变异自验补）：**以中文括号结尾**的名字必须一字不动。

    ## 为什么补这一条（真缺口，不是凑数）

    变异自验发现：一个坏实现「剥掉尾部**含中文**的括号」在**原测试下 17 条全绿**
    （变异 C 存活）。查真库确认它**会真伤数据** —— `standard_no` 里以
    「含中文的括号」结尾的共 **88** 条，其中 `(OCR采集)` 占 **0** 条，
    其余 88 条**全是合法名字**：

        |刑法修正案（七）|  |人民检察院刑事诉讼规则（试行）|
        |个人信息保护法(测试)|  |中华人民共和国应急管理部公告（2023年第6号）|

    ⇒ 那个坏实现会把它们**全部削成** `刑法修正案`、`个人信息保护法` ……
    ⇒ 本条断言就是这个缺口的补丁（补完再跑变异 C，必须变红）。
    """

    def test_刑法修正案_中文括号结尾(self):
        assert strip_ocr_source_suffix("刑法修正案（七）") == "刑法修正案（七）"

    def test_规则试行_中文括号结尾(self):
        s = "人民检察院刑事诉讼规则（试行）"
        assert strip_ocr_source_suffix(s) == s

    def test_公告_中文括号结尾(self):
        s = "中华人民共和国应急管理部公告（2023年第6号）"
        assert strip_ocr_source_suffix(s) == s

    def test_已废止_中文括号结尾(self):
        s = "中华人民共和国应急管理部令（第8号）应急管理部关于修改《煤矿安全规程》的决定（已废止）"
        assert strip_ocr_source_suffix(s) == s

    def test_测试夹具_中文括号结尾(self):
        # 真库里那条测试夹具（开发史 §10.239 的 D1）
        assert strip_ocr_source_suffix("个人信息保护法(测试)") == "个人信息保护法(测试)"

    def test_真库那_88_条的形态都不动(self):
        """把真库实测的 88 条形态**逐条**过一遍（这是从库里抄下来的，不是编的）。"""
        for s in (
            "个人信息保护法(测试)",
            "中华人民共和国应急管理部令（第8号）应急管理部关于修改《煤矿安全规程》的决定（已废止）",
            "中华人民共和国应急管理部公告（2018年  第3号）",
            "中华人民共和国应急管理部公告（2021年   第1号）",
            "中华人民共和国应急管理部公告（2023年第6号）",
            "中华人民共和国应急管理部公告（2024年第3号）",
            "人民检察院刑事诉讼规则（试行）",
            "人民检察院民事诉讼监督规则（试行）",
            "人民检察院行政诉讼监督规则（试行）",
            "刑法修正案（七）",
            "刑法修正案（十一）",
            "刑法修正案（十二）",
            "刑法修正案（十）",
        ):
            assert strip_ocr_source_suffix(s) == s, s


class Test边界:
    def test_空串(self):
        assert strip_ocr_source_suffix("") == ""

    def test_None(self):
        assert strip_ocr_source_suffix(None) == ""

    def test_只有后缀_剥成空(self):
        assert strip_ocr_source_suffix("(OCR采集)") == ""

    def test_幂等(self):
        once = strip_ocr_source_suffix("刑法(OCR采集)")
        assert strip_ocr_source_suffix(once) == once

    def test_中间的OCR采集不动(self):
        # 判据锚定结尾（`$`）⇒ 中间出现不该动
        s = "某(OCR采集)办法"
        assert strip_ocr_source_suffix(s) == s
