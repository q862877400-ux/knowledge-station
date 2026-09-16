"""OCR 折行清洗公共模块测试（2026-08-23）。"""
from src.core.text_utils import normalize_wraps


def test_join_plain_wrap():
    """普通折行（CJK 直连）→ 拼接。"""
    assert normalize_wraps("有毒气体及氧\n气浓度") == "有毒气体及氧气浓度"


def test_keep_para_boundary():
    """句末标点 + 下一行是编号/条款 → 保留段落断行。"""
    s = "作业前应清除现场可燃物。\n5.2.1 动火作业应有专人监护"
    assert normalize_wraps(s) == s


def test_ascii_space():
    """字母数字跨界拼接补空格；数字-中文直连不补。"""
    assert normalize_wraps("0.3m\n0.6m") == "0.3m 0.6m"
    assert normalize_wraps("0.3m\n至 0.6m") == "0.3m至 0.6m"


def test_idempotent():
    """幂等：已清洗文本再执行无变化。"""
    s = "作业现场应配置移动式气体检测报警仪，连续检测受限空间内可燃气体、有毒气体及氧气浓度，并 2 h 记录 1次。"
    assert normalize_wraps(s) == s
    once = normalize_wraps("有毒气体及氧\n气浓度，并 2 h 记录 1次。")
    assert normalize_wraps(once) == once


def test_empty_and_none():
    assert normalize_wraps("") == ""
    assert normalize_wraps(None) == ""


# ========== katex_sym_html（2026-08-29 式中 hat/bar 符号 → KaTeX span）==========
from src.core.text_utils import katex_sym_html, weave_meaning_marks  # noqa: E402


def test_katex_hat_and_bar():
    """说明行 ^Ci→\\hat{C}_{i}、C̄i→\\bar{C}_{i}；普通 Ci 不动。"""
    h = ("<p>式中:^Ci———样品i近红外光谱法预测值; Ci———样品i标准值;"
         " C\u0304i———样品i的平均值。</p>")
    out = katex_sym_html(h)
    assert 'data-tex="\\hat{C}_{i}"' in out
    assert 'data-tex="\\bar{C}_{i}"' in out
    assert out.count("katex-sym") == 2


def test_katex_body_zero_touch():
    """正文段（无 ——— 说明行）e^x 零误伤。"""
    h = "<p>衰减服从 e^x 模型。</p>"
    assert katex_sym_html(h) == h


def test_katex_idempotent():
    """幂等：已处理段不再嵌套。"""
    h = "<p>式中: C\u0304i———样品i的平均值。</p>"
    once = katex_sym_html(h)
    assert katex_sym_html(once) == once


def test_katex_weave_pipeline():
    """weave → katex 全链路：34406 3.7 原文形态。"""
    t = ("R=√(1-∑(^Ci-Ci)2/∑(Ci-Ci)2)(1)式中:^Ci———样品i近红外光谱法预测值;"
         " Ci———样品i标准值; Ci———样品i的平均值。")
    html = "<p>" + weave_meaning_marks(t) + "</p>"
    out = katex_sym_html(html)
    assert 'data-tex="\\hat{C}_{i}"' in out and 'data-tex="\\bar{C}_{i}"' in out


# ========== 入库元数据标准化（2026-08-29）：效力层级/标准类型推导 ==========
from src.core.ingestion.pipeline import _hier_from_no, _std_type  # noqa: E402


def test_hier_from_no():
    """标准号 → 效力层级：GB/T、GB/Z 推导；法规 fallback 不受影响。"""
    assert _hier_from_no("GB/T 34406-2017") == "GB/T"
    assert _hier_from_no("GB／T 34406-2017") == "GB/T"      # 全角／
    assert _hier_from_no("GB/Z 25000.1-2021") == "GB/Z"
    assert _hier_from_no("GB 25596-2010") == "GB"
    assert _hier_from_no("DB11/T 1000-2020") == "DB"
    assert _hier_from_no("食品安全法", fallback="法律") == "法律"


def test_std_type_by_hierarchy():
    """层级 → standard_type：推荐性/指导性/强制。"""
    assert _std_type("GB/T") == "recommended"
    assert _std_type("GB/Z") == "guiding"
    assert _std_type("GB") == "mandatory"


# ========== 国标排版还原三件套（2026-08-30，GB/T 34406 §4/§5 实测）==========
from src.core.text_utils import (  # noqa: E402
    pua_bond_dash_html, space_clause_numbers_html, sup_unit_exponents_html)


def test_pua_bond_dash():
    """PUA 键横线 → em dash：34406 §4 原文形态；乱码行零误伤。"""
    h = "<p>利用珍珠粉有机质中\ue5c6CH、\ue5c6NH、\ue5c6OH等化学基团</p>"
    out = pua_bond_dash_html(h)
    assert "中—CH、—NH、—OH等" in out
    # 反例：字母夹心（乱码文本层）、单字母后继、Symbol 串、正常汉语
    assert pua_bond_dash_html("<p>F\ue011F()</p>") == "<p>F\ue011F()</p>"
    assert pua_bond_dash_html("<p>犖\ue011K（2</p>") == "<p>犖\ue011K（2</p>"
    assert pua_bond_dash_html("<p>\uf03dH W</p>") == "<p>\uf03dH W</p>"
    assert pua_bond_dash_html("<p>依法查封扣押</p>") == "<p>依法查封扣押</p>"


def test_sup_unit_exponents():
    """单位负指数 → <sup> 上标：cm-1 波数形态；编号连字符零误伤。"""
    h = "<p>扫描范围包括4000cm-1~10000cm-1,分辨率优于8cm-1。</p>"
    out = sup_unit_exponents_html(h)
    assert "4000cm<sup>-1</sup>~10000cm<sup>-1</sup>" in out
    assert "8cm<sup>-1</sup>。" in out
    # 反例：图/表编号连字符、非数字指数、非白名单单位
    assert sup_unit_exponents_html("<p>见图A-1与表B-2</p>") == "<p>见图A-1与表B-2</p>"
    assert sup_unit_exponents_html("<p>cm-abc 样例</p>") == "<p>cm-abc 样例</p>"
    assert sup_unit_exponents_html("<p>Xy-1 变量</p>") == "<p>Xy-1 变量</p>"


def test_space_clause_numbers():
    """段首条款编号补空格：4原理→4 原理；非编号/已空格零误伤。"""
    h = "<p>4原理利用珍珠粉有机质</p><p class=\"tbl-cap\">5仪器与设备</p>"
    out = space_clause_numbers_html(h)
    assert "<p>4 原理利用珍珠粉" in out
    assert "<p class=\"tbl-cap\">5 仪器与设备</p>" in out
    # 反例：数值开头正文（>2 位 / 编号后非汉字）、已空格幂等
    assert space_clause_numbers_html("<p>2026年起施行</p>") == "<p>2026年起施行</p>"
    assert space_clause_numbers_html("<p>0.5mol试料</p>") == "<p>0.5mol试料</p>"
    once = space_clause_numbers_html("<p>4 原理</p>")
    assert space_clause_numbers_html(once) == once


def test_ingest_trio_text():
    """入库路三件套（纯文本形态，GB/T 34406 §4 原文）：—/cm⁻¹/编号空格 + 幂等。"""
    from src.core.text_utils import (
        space_clause_numbers_text, sup_unit_exponents_text)
    t = ("4原理利用珍珠粉有机质中\ue5c6CH、\ue5c6NH、\ue5c6OH等化学基团\n"
         "扫描范围包括4000cm-1~10000cm-1,分辨率优于8cm-1。")
    out = space_clause_numbers_text(sup_unit_exponents_text(pua_bond_dash_html(t)))
    assert "4 原理利用珍珠粉" in out
    assert "中—CH、—NH、—OH等" in out
    assert "4000cm\u207b\u00b9~10000cm\u207b\u00b9" in out
    assert "8cm\u207b\u00b9。" in out
    again = space_clause_numbers_text(sup_unit_exponents_text(pua_bond_dash_html(out)))
    assert again == out  # 幂等


def test_exit_ingest_form_converged():
    """形态收敛：入库路产出的干净形态过出口重放零变化（新旧文档渲染同形）。"""
    h1 = "<p>4 原理利用珍珠粉有机质中—CH、—NH、—OH等化学基团</p>"
    assert space_clause_numbers_html(h1) == h1
    h2 = "<p>扫描范围包括4000cm\u207b\u00b9~10000cm\u207b\u00b9。</p>"
    assert sup_unit_exponents_html(h2) == h2


# ---------------------------------------------------------------------------
# 公式编号引导点线（dot-leader 所有者层，2026-09-15 第二轮）
# ---------------------------------------------------------------------------
def test_strip_formula_leader_label_inner_space():
    """缺陷证据：VLM 把 'C.3' 识别成 'C. 3'，编号捕获紧排 → 整条不匹配、点线原样落库。

    实测 GB/T 1094.6-2011 '……(C. 3'、GB/T 15543-2008 '……(A. 1'。
    """
    from src.core.text_utils import strip_formula_leader
    assert "……" not in strip_formula_leader("L rₑₐc = X/2 f ……(C. 3")
    assert "……" not in strip_formula_leader("……(A. 1")
    assert "……" not in strip_formula_leader("………( A. 2")


def test_strip_formula_leader_bare_threshold_aligned():
    """裸点线阈值与检测器对齐：6 个 ASCII 点即剥（原 7 点 → 差一处就漏网）。

    实测 GB/T 12326-2008 '………( A. 2' 剥后残留 6 点，正好卡在 6/7 的缝里。
    """
    from src.core.text_utils import strip_formula_leader
    assert "......" not in strip_formula_leader("x ......( A. 2")
    assert "." not in strip_formula_leader("x ......")
    # 反向对照：小于阈值不视为引线
    assert strip_formula_leader("a....b") == "a....b"


def test_strip_formula_leader_reverse_controls():
    """反向对照（修复纪律要求）：正文合法形态必须存活，不许被引导线规则误伤。"""
    from src.core.text_utils import strip_formula_leader
    for keep in [
        "13.1 燃具旋塞阀及其他燃气手动阀 …… 11",   # 目录行：点线+页码是正常排版
        "F = m a …… 与式(A.1)相同",                # 正文省略号后接引用
        "正文省略号……继续",                        # 两字省略号是正常标点
        "Δ LₚA = LₚA (S T) - LₚA (B)",            # 公式本体的空格必须保留
        "(见 4.3 a) 的说明",                       # 普通括号内容不碰
    ]:
        assert strip_formula_leader(keep) == keep, keep


def test_strip_formula_leader_idempotent():
    """幂等：清洗后文本不再命中两条规则。"""
    from src.core.text_utils import strip_formula_leader
    for src in ["……………( 1 式中：", "Z = r ……(D.7)", "x ......( A. 2",
                "13.1 燃具 …… 11"]:
        once = strip_formula_leader(src)
        assert strip_formula_leader(once) == once, src


def test_clean_clause_text_is_single_owner():
    """`clean_clause_text` = 入库与评估共用的**唯一**清洗次序。

    缺陷背景：清洗链原先是 pipeline 入库处的一行嵌套调用，评估器
    （evolve.evaluate_doc）对产物原文跑判据、从不经过它 → 清洗器修好的类
    判据照旧报、留出集永远判不通过。抽出后两处必须逐例同结果。
    """
    from src.core.ingestion.pipeline import strip_figure_legend_segment
    from src.core.text_utils import (clean_clause_text, normalize_label_comma,
                                     normalize_pua_separators,
                                     space_clause_numbers_text,
                                     strip_formula_leader,
                                     sup_unit_exponents_text)
    cases = [
        "……………( 1 式中：",
        "13.1 燃具旋塞阀及其他燃气手动阀 …… 11",
        "L rₑₐc = X/2 f ……(C. 3",
        "2009\ue01103\ue01116发布",
        "扫描范围包括4000cm-1~10000cm-1。",
        "普通正文，无任何需清洗形态。",
    ]
    for c in cases:
        legacy = space_clause_numbers_text(sup_unit_exponents_text(
            normalize_label_comma(strip_figure_legend_segment(
                strip_formula_leader(normalize_pua_separators(c))))))
        assert clean_clause_text(c, legend_stripper=strip_figure_legend_segment) \
            == legacy, c


def test_clean_clause_text_shape_invariants():
    """行数与长度不变形、空输入安全、幂等——入库靠行号定位页界，字形不得改行数。"""
    from src.core.ingestion.pipeline import strip_figure_legend_segment
    from src.core.text_utils import clean_clause_text
    src = "4原理利用珍珠粉\n扫描范围包括4000cm-1~10000cm-1。\n……………( 1 式中："
    out = clean_clause_text(src, legend_stripper=strip_figure_legend_segment)
    assert out.count("\n") == src.count("\n")
    assert clean_clause_text(None) == ""
    assert clean_clause_text("") == ""
    assert clean_clause_text(out, legend_stripper=strip_figure_legend_segment) == out


# ---------------------------------------------------------------------------
# 站点水印行剥离（2026-09-15 新语料实测 38/231 部 = 16%）
# ---------------------------------------------------------------------------
def test_strip_watermark_lines_removes_pirate_site_headers():
    """盗版站水印行整行删除（裸 URL 与"短标签+URL"两族）。

    缺陷证据（新语料 VLM 产物实测）：'网址 www.spc.net.cn'（23 处）、
    'http://www.spc.net.cn'、'http://www.bzcbs.com'、
    '龙牛网 www.longniu.com 下载'、'网址: www.spc.net.cn'。
    """
    from src.core.text_utils import strip_watermark_lines
    for wm in ["网址 www.spc.net.cn", "http://www.spc.net.cn",
               "龙牛网 www.longniu.com 下载", "网址: www.spc.net.cn",
               "www.gb168.cn", "http://www.bzcbs.com",
               "中国标准出版社出版 网址 www.spc.net.cn"]:
        assert strip_watermark_lines(wm).strip() == "", wm


def test_strip_watermark_lines_keeps_real_citations():
    """**反向对照（关键）**：正文里的合法 URL 与参考文献引用必须一字不动。

    判据靠"剥掉 URL 后的残留长度"区分——水印的残留是 '网址'/'下载' 这类短标签，
    引用的残留是实质文字。
    """
    from src.core.text_utils import strip_watermark_lines
    for keep in [
        # W3C 命名空间（技术内容，删了正文就缺内容）
        "本附录使用 SOAP 1.2 规范 [¹] 进行定义和描述。SOAP 规范定义的 XML 元素"
        "命名空间为 http://www.w3.org/2003/05/soap-envelope，前缀为",
        # 参考文献引用
        "[1] SOAP Version 1.2 Part 1: Messaging Framework (Second Edition), "
        "http://www.w3.org/TR/soap12/",
        "[13] 2011年和2012年中国区域电网平均二氧化碳排放因子."
        "http://www.ccchina.org.cn/archiver/ccchinacn/UpFile/Files/Default",
        "[4] 卡内基梅隆大学软件工程研究所《CMMI 开发模型 2.0 版》, 2018, "
        "www.sei.cmu.edu/cmmi.",
        # 普通条款（**最危险的误删目标**：判据放宽成裸域名就会把这些整行删掉）
        "4 范围 本标准适用于压力容器",
        "2.1 较大婴儿",
        "3.1 婴幼儿谷物辅助食品",
    ]:
        assert strip_watermark_lines(keep) == keep, keep


def test_strip_watermark_lines_rejects_bare_domain_pattern():
    """**回归护栏**：判据不得放宽为裸域名，否则普通条款被误判成 URL。

    实测教训：把 URL 正则写成 `[A-Za-z0-9\\-]+(\\.[A-Za-z0-9\\-]+)+`
    （点号后允许裸域名）后，'2.1 较大婴儿'、'3.1 婴幼儿谷物辅助食品' 全部被当成
    域名 → **误删 10025 行**。故必须有 `www.` 或 `scheme://`。
    """
    from src.core.text_utils import _RE_WM_URL2
    assert _RE_WM_URL2.search("网址 www.spc.net.cn")
    assert _RE_WM_URL2.search("http://www.bzcbs.com")
    for safe in ["2.1 较大婴儿", "3.1 婴幼儿谷物辅助食品", "4.1 原料要求",
                 "5.2.3 试验方法", "表 A.1 试验条件"]:
        assert not _RE_WM_URL2.search(safe), safe


# ---------------------------------------------------------------------------
# 第二/三族水印：无 URL 的**工具水印**与**页眉**（2026-09-16）
#
# 缺陷证据（生产库实测，非构造）：19,981 条 content_text 补丁中 14,906 条（74.6%）
# 含盗版站页脚/页眉，而**原文 0 条** → 由 `pypdf_backfill` 越界抽取引入。
# 该回填把条款号到页尾之间的一切都吃进 buf（`pypdf_backfill.py:60` 的"下一条款"
# 判据不认 `表3`/`附录A`），再用 `" ".join(buf)` 拍成**单行** → 水印不在自己行上，
# "整行删除"判据够不着。既有两个用例覆盖不到这一族，故单列。
_ASPOSE_FOOTER = ("Evaluation Only. Created with Aspose.PDF. "
                  "Copyright 2002-2025 Aspose Pty Ltd.")


def test_strip_watermark_lines_removes_aspose_tool_watermark():
    """工具水印（无 URL）必须清除——旧守卫只认 URL 载体，使整族漏网。"""
    from src.core.text_utils import strip_watermark_lines
    for wm in [
        _ASPOSE_FOOTER,
        "Created with Aspose.PDF",
        # 生产库实际形态：页眉（页码+标准号）+ 工具水印挤在同一单行里
        f"5 GB/T 10029—2010 {_ASPOSE_FOOTER}",
        # 页眉本身独立成行（`_RE_WM_HEADER` 的 `^…$` 形态）
        "5 GB/T 10029—2010",
    ]:
        out = strip_watermark_lines(wm)
        assert "Aspose" not in out, wm
        assert "GB/T 10029" not in out, (wm, out)
        assert out.strip() == "", (wm, out)


def test_strip_watermark_lines_drops_header_tail_but_keeps_body_intact():
    """**行尾页眉**（不锚行首）必须剥掉，且正文一字不动。

    单行化正文把页眉拍在长行尾部（`'…执行。 5 GB/T 10029—2010'`），此时
    `^…$` 形态的 `_RE_WM_HEADER` 够不着，靠 `_RE_WM_HEADER_TAIL` 收口。
    **前导页码是必须的、不是可选的**：本用例同族的反向对照
    （`'应符合 GB/T 10029—2010'`，见 keeps_standard_refs_in_body）抓出过一次放宽事故
    ——把页码写成可选后，行尾只有一个标准号引用的正文被整段删掉。
    """
    from src.core.text_utils import strip_watermark_lines
    out = strip_watermark_lines(
        "…其他测定结果应进行综合特征判定,按 GB/T18654.1的规定执行。 5 GB/T 10029—2010")
    assert "GB/T 10029" not in out, out
    # 正文（含正文内的标准号引用 GB/T18654.1）一字不动
    assert out == "…其他测定结果应进行综合特征判定,按 GB/T18654.1的规定执行。", out


def test_strip_watermark_lines_aspose_strips_inline_but_keeps_body():
    """**关键**：水印被拍进长单行中间时，只删水印、**正文一字不动**。

    实测口径：生产库 12,614 条命中的长度差**恒为 -78**（正是该水印串长度）
    —— 若误删正文会出现 -200 量级的差值。
    """
    from src.core.text_utils import strip_watermark_lines
    body = ("能够扩增出大小分别为820bp和360bp的两个标志带。其他测定结果应进行"
            "综合特征判定,按 GB/T18654.1的规定执行。")
    out = strip_watermark_lines(f"{body} 5 GB/T 10029—2010 {_ASPOSE_FOOTER}")
    assert out == body, out


def test_strip_watermark_lines_keeps_standard_refs_in_body():
    """**反向对照（关键）**：正文里的标准号引用/表数据不得被当成页眉删掉。

    页眉判据要求"行首页码 + 标准号"或"行尾标准号"，故下面这些必须存活——
    其中前两条是"页眉式引用句"，最容易被误伤。
    """
    from src.core.text_utils import strip_watermark_lines
    for keep in [
        "按 GB/T 18654.1 的规定执行。",
        "见表 5 GB/T 10029—2010 的规定",
        "应符合 GB/T 10029—2010",
        "板、封头 承压设备用钢板 Q245R、Q345R GB/T713.2—2023 炉管、弯头 无缝钢管",
        "摘 要 本文件按照GB/T1.1—2020《标准化工作导则》的规定起草。",
        "5.2.3 试验方法",
    ]:
        assert strip_watermark_lines(keep) == keep, keep


def test_strip_watermark_lines_aspose_idempotent():
    """幂等：重复清洗结果不变（清洗链可重入的前提）。"""
    from src.core.text_utils import strip_watermark_lines
    once = strip_watermark_lines(f"正文一\n5 GB/T 10029—2010 {_ASPOSE_FOOTER}\n正文二")
    assert once == "正文一\n正文二", once
    assert strip_watermark_lines(once) == once


def test_clean_clause_text_strips_watermark_in_chain():
    """水印剥离已接入清洗链（`clean_clause_text`），入库与评估同源生效。"""
    from src.core.text_utils import clean_clause_text
    out = clean_clause_text("4 范围\n网址 www.spc.net.cn\n本标准适用于压力容器。")
    assert "www.spc.net.cn" not in out
    assert "本标准适用于压力容器。" in out
    assert "4 范围" in out


# ---------------------------------------------------------------------------
# PUA 装饰类剥离（2026-09-15 新语料复测，pua-residue 13 部 → 3 部）
# ---------------------------------------------------------------------------
def test_pua_decor_stripped_to_space():
    """装饰类 PUA（项目符号/表格分隔/版权页位标）→ 空格。

    缺陷证据（新语料 231 部实测，均取自 `pua-residue` 判据的命中原文）：
    '\\n\ue5f9研究报告\\n\ue5f9概念设计'（项目符号）、
    'R1\ue6e6\ue6f3\\nNPT1\ue6e6\ue6f3'（表头分隔）、
    '版权专有 侵权必究\\n\ue012\\n书号:155066·1-57616'（版权页位标）。
    反向对照：直接 fitz 读源 PDF 即得这些 PUA → **文本层原生**，非管线引入，
    故只剥离、不映射（映射无真值依据）。
    """
    from src.core.text_utils import normalize_pua_separators as f
    assert "\ue5f9" not in f("\ue5f9研究报告")
    assert f("\ue5f9研究报告") == " 研究报告"
    assert f("R1\ue6e6\ue6f3") == "R1  "
    assert f("—\n\ue5cf\ue5cf\n电力") == "—\n  \n电力"
    assert f("—\n\ue79f\n9") == "—\n \n9"
    assert "\ue012" not in f("版权专有 侵权必究\n\ue012\n书号:1")


def test_pua_meaningful_codepoints_survive():
    """**反向对照（关键）**：有语义、但拿不到确定真值的码点必须原样保留。

    理由：猜映射就是造假数据；留着至少还能被 `pua-residue` 判据抓到、
    等待识别层（VLM 像素 OCR）取回真字。实测：
    - U+E3E4/U+E2C5/U+E54F 人名缺字——'郭锐、张\ue3e4\ue3e4、马洪杰'（真值应为某字）
    - U+E03C 公式位——'r2\ue03cQ=Q0-r2'（疑似减号，不确定）
    若把它们也映射掉，缺字会静默消失（比留着 PUA 更糟）。
    """
    from src.core.text_utils import normalize_pua_separators as f
    for keep in ["郭锐、张\ue3e4\ue3e4、马洪杰",
                 "尚国\ue2c5、钱永刚",
                 "GuillevicP,G\ue54fttscheF",
                 "r2\ue03cQ=Q0-r2"]:
        assert f(keep) == keep, keep


def test_pua_separator_original_cases_intact():
    """首轮两个分隔符码点的原有行为不得回归。

    注：U+E011 的还原规则是「数字↔数字 → '-'，其余 → 空格」，故
    'Kennard\\ue011Stone' 得到**空格**（原作注释写作 '真值 Kennard-Stone'
    只是举例说明该位置是分隔符，规则本身对字母侧不产 '-'）——测试按**实际规则**
    断言，不按注释里的举例，避免把注释笔误固化成回归。
    """
    from src.core.text_utils import normalize_pua_separators as f
    assert f("2009\ue01103\ue01116发布") == "2009-03-16发布"
    assert f("Kennard\ue011Stone算法") == "Kennard Stone算法"
    assert f("内径为\ue78876+2/0mm") == "内径为 76+2/0mm"
    # 无 PUA 的文本零变化（快速路径也不得改动）
    assert f("4 原理利用珍珠粉") == "4 原理利用珍珠粉"
    assert f(None) == ""
