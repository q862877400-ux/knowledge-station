"""已知缺口（2026-09-17 实测，**故意用 strict xfail 钉住**）：水印剥离的 step ② 会
把"表格末格 = 裸数字 + 被引用标准号"误判成行尾页眉而删掉。

`src/core/text_utils.py` 的 `strip_watermark_lines` step ② 用 `_RE_WM_HEADER_TAIL`
收口"被 `pypdf_backfill` 的 `" ".join(buf)` 拍进行尾的页眉"（形如
`'…执行。 5 GB/T 10029—2010'`）。判别特征只有"前导页码"，而**表格末格**恰好也是
`<裸数字> <标准号>`（如材料表里的 `20 GB/T699—2015`、字段表里的 `10 GB/T917—2009`）。

实测口径（清洗前快照 `snap_01M2NMCW9S5H0EVR45BVSHG9ND.db`，19,981 条 content_text 补丁）：
  - step ② 命中的 `页码+标准号` 尾巴共 **2,910** 处；
  - 其中 **2,904** 处的标准号 = **该文档自己的**标准号 → 确是页眉，删得对；
  - **6** 处引用的是**别的**标准 → 疑似真实表格内容，涉及 **3 个条款**。
  - 生产库现状：这 4 条候选补丁**都还在**（内容未丢）——即**没有实际损坏**，
    但**再跑一次 `scripts/repair_patch_watermarks.py --apply` 就会删掉它们**
    （dry-run 当前报 "将清洗 4 条"，正是这 4 处）。

为什么现在不修（**明确未做**）：正确修法是**把上下文喂进来**，即让调用方传入
该文档自己的标准号，step ② 只删标准号与之相符的尾巴 —— `pypdf_backfill` 与
修复脚本都知道这个信息。这需要给 `strip_watermark_lines` 加参数并改两处调用方。
三条**已试并否决**的纯文本启发式（本会话实测）：
  1. "文本自带页眉证据才收口" → 会漏掉 2,910 处真页眉（它们没有 Aspose 水印）；
  2. "该标准号在文内出现 ≥2 次才算页眉" → 条款只覆盖一页时不成立；
  3. "尾巴前必须是句末标点" → 判据过粗，实测大量真页眉前不是句号。

本文件用 `strict=True`：**修好之后这些用例会 XPASS，从而变成 FAILED**，
强制后来者删掉 xfail 标记（而不是让缺口悄悄留在"已知失败"里）。
"""
import pytest

from src.core.text_utils import strip_watermark_lines

# 4 条实测输入（取自生产库，均已确认当前未被删）
CASES = [
    (
        "锅炉材料表末格",
        "5.2 材料 锅炉主要受压元件材料按表2规定执行。 表 2 锅炉主要受压元件材料 "
        "零件名称 推荐材料名称 推荐材料牌号 标准编号 筒体、管板(封头)、炉胆 承压设备用钢板 "
        "Q245R、Q345R GB/T713.2—2023 烟管、水管、牵条管 无缝钢管 20 钢级410 GB/T3087—2022 "
        "GB/T5312—2009 牵条 优质碳素结构钢 20 GB/T699—2015",
        "GB/T699—2015",
    ),
    (
        "村镇属性表末格",
        "8.14 公路沿线村镇 公路沿线村镇属性结构见表24。 表 24 字段名 类型 宽度 (单位:字节) "
        "值域或说明 村镇代码 字符型 6 GB/T10114 村镇名称 字符型 20 中文名称 路线代码 字符型 "
        "10 GB/T917—2009",
        "GB/T917—2009",
    ),
    (
        "交通标志属性表末格",
        "8.9.1 交通标志属性结构见表9。 表 9 字段名 类型 宽度 (单位:字节) 值域或说明 "
        "交通标志代码 字符型 6 JT/T132—2003 交通标志名称 字符型 20 中文名称 路线代码 "
        "字符型 10 GB/T917—2009 桩号 数值型(小数点后三位) 8 交通标志构造 字符型 1 "
        "JT/T132—2003 标志支持方式 字符型 1 JT/T132—2003",
        "JT/T132—2003",
    ),
    (
        "环境条件表末格",
        "6.1 产品应用环境条件的分类及其代码 按照环境条件标准,选择产品的应用环境条件是确定"
        "产品环境适应性的一个捷径。 表 9 产品应用环境条件类型 序号 应用环境条件类型 数字代码 "
        "国家标准 备注 1 运输 1 GB/T4798.1—2005 2 贮存 2 GB/T4798.2—2008 3 有气候防护场所"
        "固定使用 3 GB/T47 4 地面车辆使用 5 GB/T4798.5—2007",
        "GB/T4798.5—2007",
    ),
]


@pytest.mark.xfail(strict=True, reason="已知缺口：表格末格被误判为行尾页眉（见本文件 docstring）")
@pytest.mark.parametrize("label,text,needle", CASES, ids=[c[0] for c in CASES])
def test_table_last_cell_must_survive(label, text, needle):
    out = strip_watermark_lines(text)
    # ⚠ 必须断言"结尾"而不是"包含"：同一个标准号在表内可能**出现多次**
    #   （如交通标志表里 JT/T132—2003 出现 3 次），只判包含会在尾格被删后仍然 XPASS。
    assert out.rstrip().endswith(needle), f"{label}：表格末格的标准号被误删"


@pytest.mark.parametrize("label,text,needle", CASES, ids=[c[0] for c in CASES])
def test_same_document_header_is_still_removed(label, text, needle):
    """反向护栏（**必须通过**）：同一函数对**自家标准号**的页眉仍要删干净。

    这条钉住"修缺口时不能把真页眉一起放过"——上面 4 条修好后，本用例必须仍绿。
    """
    own = "GB/T 28788-2012"          # 上述 4 条文本所属文档自己的标准号
    # 页眉形态：页码 + 自家标准号，贴在行尾
    text_with_own_header = text + f" 7 {own}"
    out = strip_watermark_lines(text_with_own_header)
    assert f"7 {own}" not in out
    assert out.rstrip().endswith(needle), "自家页眉被剥时不得连带删掉正文/表格内容"
