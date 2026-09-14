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
