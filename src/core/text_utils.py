"""OCR 文本清洗公共模块（2026-08-23 整合）。

normalize_wraps：OCR 折行拼接——MinerU 把 PDF 一行在版面上的折行硬切成 \n，
本函数按规则合并：单换行拼接（CJK 直连、字母数字补空格）；仅当「句末标点 + 下一行是
编号/表/注/第X条/图」才保留段落断行。

latex_to_text / clean_eq_tags：MinerU 行内公式 <eq>LaTeX</eq> → 可读 Unicode 文本
（h_w/m 等），入库即转换，卡片/WPS/编辑器全链路一致。

用途（单一来源，消除多处复制）：
  1) 入库管线：content_text 落库前清洗 + 表格 html 的 <eq> 转换
  2) 显示层兜底（幂等：已清洗的再拼无变化）
  3) WPS 导出前
"""
from __future__ import annotations

import re
import unicodedata

_PARA_START_RE = re.compile(
    r"^(\d{1,2}(\.\d+)*\s*[、．.]?|（[一二三四五六七八九十]+）|"
    r"[一二三四五六七八九十]+、|表\d+|附录|注[:：]?|"
    r"第[一二三四五六七八九十]+[章条节]|图\d+)")
_SENT_END_RE = re.compile(r"[。！？；：]$")
_ASCII_RE = re.compile(r"[A-Za-z0-9]")

_SUB_SCRIPTS = str.maketrans(
    "0123456789aeiouxhklmnpst",
    "₀₁₂₃₄₅₆₇₈₉ₐₑᵢₒᵤₓₕₖₗₘₙₚₛₜ")
_SUP_SCRIPTS = str.maketrans(
    "0123456789aeiouxhklmnprsty",
    "⁰¹²³⁴⁵⁶⁷⁸⁹ᵃᵉⁱᵒᵘˣʰᵏˡᵐⁿᵖʳˢᵗʸ")

_LATEX_SYMBOLS = {
    # 长变体优先（\leqslant 必须先于 \le 替换，否则被前缀吞掉）
    "\\leqslant": "≤", "\\geqslant": "≥",
    "\\leq": "≤", "\\geq": "≥", "\\neq": "≠", "\\times": "×",
    "\\div": "÷", "\\pm": "±", "\\cdot": "·", "\\approx": "≈",
    "\\rightarrow": "→", "\\infty": "∞", "\\circ": "°", "\\sqrt": "√",
    "\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "~": " ",
    # 2026-09-01 增补（GB/T 24276 24 条独立公式实测缺漏）：
    "\\Delta": "Δ", "\\delta": "δ", "\\bullet": "•", "\\colon": ":",
    "\\textmu": "µ", "\\kappa": "κ", "\\lambda": "λ", "\\mu": "µ",
    "\\rho": "ρ", "\\sigma": "σ", "\\tau": "τ", "\\omega": "ω",
    # 2026-09-15 函数名命令（收敛循环第 5 轮）：通用剥离器 `\\[A-Za-z]+` 会把
    # `\min` 整词删掉 → 公式语义丢失（实测 'z = \min(z,200)' 变 'z = (z,200)'，
    # GB/T 10095.2-2023 E.1）。数学函数名有可读文本，必须映射而非删除。
    "\\min": "min", "\\max": "max", "\\log": "log", "\\ln": "ln",
    "\\exp": "exp", "\\sin": "sin", "\\cos": "cos", "\\tan": "tan",
    "\\arctan": "arctan", "\\arcsin": "arcsin", "\\arccos": "arccos",
    "\\lim": "lim", "\\sup": "sup", "\\inf": "inf", "\\det": "det",
    "\\gcd": "gcd", "\\mod": "mod",
}

# 词边界单遍符号替换：长键优先 + (?![A-Za-z]) 防前缀误吃（\pm 不吃 \pmb）
_SYM_RE = re.compile("|".join(
    re.escape(k) + r"(?![A-Za-z])"
    for k in sorted((k for k in _LATEX_SYMBOLS if k.startswith("\\")),
                    key=len, reverse=True)))

#: MinerU 剥反斜杠后残留的"符号+命令名"形态（实测 DB 里是 ≤slant 而非 \leqslant）
_LEAKED_SYMBOLS = (
    ("≤slant", "≤"), ("≥slant", "≥"), ("≤slant ", "≤ "), ("≥slant ", "≥ "),
)

# ---------------------------------------------------------------------------
# PUA 错位字体归一化（2026-08-29，GB/T 34406-2017 实测，语料级通用修复）
# ---------------------------------------------------------------------------
# 大量 GBT 双层扫描 PDF 的文本层是"形近 CJK 替代"字体 hack：
# 'GB/T'→'犌犅／犜'、'Identification'→'犐犱犲狀狋犻犳犻犮犪狋犻狅狀'（犬部形近字 U+72xx-73xx），
# 数字 '0'-'9' 被整体平移为 '!'-'*'（0x21-0x2A），另有全角数字/标点。
# 此类文本层"存在但不可切分"——过去只能整本转像素 OCR（占 GPU/云配额）。
# 映射是确定的：归一化后即可按正常文本层秒级入库，全库同类文档一并受益。
_PUA_LATIN_MAP = {
    '犃': 'A', '犅': 'B', '犆': 'C', '犇': 'D', '犈': 'E', '犉': 'F', '犌': 'G', '犎': 'H',
    '犐': 'I', '犑': 'J', '犓': 'K', '犔': 'L', '犕': 'M', '犖': 'N', '犗': 'O', '犘': 'P',
    '犙': 'Q', '犚': 'R', '犛': 'S', '犜': 'T', '犝': 'U', '犞': 'V', '犠': 'W', '犡': 'X',
    '犢': 'Y', '犣': 'Z',
    '犪': 'a', '犫': 'b', '犮': 'c', '犱': 'd', '犲': 'e', '犳': 'f', '犵': 'g', '犺': 'h',
    '犻': 'i', '犼': 'j', '犽': 'k', '犾': 'l', '犿': 'm', '狀': 'n', '狅': 'o', '狆': 'p',
    '狇': 'q', '狉': 'r', '狊': 's', '狋': 't', '狌': 'u', '狏': 'v', '狑': 'w', '狓': 'x',
    '狔': 'y', '狕': 'z',
    # 2026-08-29 二次实测（GB/T 34406 公式区）：根号 √ (U+221A) 的形近 PUA 替身。
    # '槡' 是"桑"的生僻异体，正文出现概率≈0，映射安全。
    '槡': '√',
}

#: 盗版标准站页眉水印 URL token（GB/T 34406 每页页眉 "www.bzfxw.com" 实测）。
#: 仅在「剥后空/行首行尾」语义下使用，行中 URL 不动，正文合法引用不受影响。
_RE_WM_URL = re.compile(r"www\.[A-Za-z0-9\-]+\.(?:com|cn|net|org)", re.I)
#: 水印行剥 URL 后允许残留的页码形态（≤4 位数字/罗马，NFKC 前后两种罗马形态都收）
_RE_WM_PAGENO = re.compile(r"[IVXivx\dⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]{1,4}")
#: 公式编号引导点线：'…………（1）' NFKC 后连排 ASCII 点。
#: 阈值 7：strip_block_noise 在归一化（NFKC）之后调用，正文 2 字省略号
#: '……' → NFKC = 6 个点，必须存活；引导线 ≥3 个 '…' = ≥9 点才剥。
_RE_FORMULA_DOTS = re.compile(r"\.{7,}")
#: 公式编号引导点线（U+2026 形态，2026-09-15 全库审计 dot-leader 44 部达线）。
#: 两条规则按序应用：
#: ① 点线 + 编号：**无论点数**（GB 引导线常短至 '……(7)'）→ 归一 ' (N)'，
#:    顺带补全缺右括号（'( 1'→'(1)'）；
#: ② 裸点线：≥7 ASCII 点 或 ≥3 个 '…'——**阈值与检测器 audit_text.dot-leader
#:    对齐**（该判据为 `…{3,}`）：正文省略号最多 2 个（'……'）必须存活，
#:    3 个及以上即为引线。此前清洗器只删 ≥4 个而检测器 3 个就报 →
#:    「检测器报缺陷、所有者层却不清洗」的口径错位（VLM 下 GB/T 10029-2010 实测）。
#:
#: 2026-09-15（VLM 通道下复测，dot-leader 仍达线）：编号捕获原为**纯数字**
#: `(\d{1,3})`，漏掉**附录字母号**——VLM 实测 '……( A.1'、'……( B.1'、'……( C.2'
#: 原样落库（GB/T 15945-2008 附录B、GB/T 10029-2010 A.1、GB/T 10002.2-2023 B.1.1）。
#: 扩为「可选字母 + 可选点 + 数字(+点数字)」：'A.1' / 'D.7' / '1' 全部覆盖。
#:
#: 2026-09-15（第二轮复测，**标签内部空格**）：VLM 会把 'C.3' 识别成 'C. 3'，
#: 而编号捕获是紧排的 `[A-Za-z]?\.?\d{1,3}` → 空格一处即整条不匹配，点线原样
#: 落库（GB/T 1094.6-2011 '……(C. 3'、GB/T 15543-2008 '……(A. 1'、GB/T 12326-2008
#: '………( A. 2' 实测）。故各 token 之间允许可选空格：'C. 3' / 'A. 2' / 'D . 7' 均收。
#: **只放宽空格，不放宽字符类**——避免把正文括号内容误当编号。
_RE_FORMULA_LEADER = re.compile(
    r"(?:\.{2,}|…+)\s*[（(]\s*([A-Za-z]?\.?\s?\d{1,3}(?:\s?\.\s?\d{1,3})?)\s*[)）]?")
#: 裸点线阈值：与检测器 `audit_text.CHECKS['dot-leader']` 的 `\.{6,}` 对齐
#: （原为 `\.{7,}`——检测器 6 点即报、所有者 7 点才剥，差一处就是漏网；
#: 实测 GB/T 12326-2008 '………( A. 2' 剥后残留 6 个 ASCII 点正好卡在缝里）。
_RE_FORMULA_LEADER_BARE = re.compile(r"(?:\.{6,}|[…]{3,})")


def strip_formula_leader(text: str | None) -> str:
    r"""公式编号引导点线清洗（幂等）：'……………( 1 / 式中：' → ' (1) / 式中：'。

    背景（2026-09-15 全库文本审计，dot-leader 类 44 部文档 167 条达线）：
    公式编号前的引导点线在文本层是 U+2026 连排，而既有 `_RE_FORMULA_DOTS`
    只认 NFKC 后的 ASCII 点（`\.{7,}`）且未被内容清洗链调用 → 点线原样落库
    （'W / = / P / S / × V1 / V2 / ....................'）。
    本函数是该形态的规范所有者：剥点线 + 补全编号右括号。

    幂等：清洗后文本不再命中两条规则。
    """
    if not text or ("…" not in text and "." not in text):
        return text or ""
    out = _RE_FORMULA_LEADER.sub(lambda m: f" ({m.group(1)})", text)
    return _RE_FORMULA_LEADER_BARE.sub(" ", out)


def normalize_pua_latin(text: str | None) -> str:
    """PUA 错位字体文本层 → 可切分文本（幂等；只在 pua_mangled 判真的文档上调用）。

    三步：① 犬部形近 CJK → 拉丁字母（'犌犅／犜'→'GB/T'，'槡'→'√'）；
    ② 0x21-0x2A → '0'-'9'（字符码整体平移还原）；③ NFKC 折叠全角数字/标点。
    正常文档不会被调用本函数；归一化后调用方须复验 mangled 判定，
    仍乱则回退像素 OCR（保守回退零数据风险）。
    """
    if not text:
        return ""
    out = []
    for ch in text:
        o = ord(ch)
        if ch in _PUA_LATIN_MAP:
            out.append(_PUA_LATIN_MAP[ch])
        elif 0x21 <= o <= 0x2A:
            out.append(chr(o + 15))
        else:
            out.append(ch)
    s = "".join(out)
    # 2026-09-02 修复 GB/T 34406 式(1)(2)式中 Ĉᵢ 帽子丢失：全角 ＾(U+FF3E)+拉丁 → 组合帽 X̂(U+0302)。
    # 仅在 NFKC 前用全角 ＾ 判定(ASCII 幂号 ^ 不受影响)；C̄ 上划线为视觉字形(文本层无字符)待 OCR 兜底。
    s = re.sub("＾([A-Za-z])", lambda m: m.group(1) + "\u0302", s)
    return unicodedata.normalize("NFKC", s)


def normalize_pua_separators(text: str | None) -> str:
    """PUA「分隔符类 / 装饰类」字符处理（2026-09-15 立，当天二次扩容）。

    背景：部分国标 PDF 的文字层把**分隔符/装饰符**画成私用区字形，提取后成为
    不可见垃圾字符。**这些码点是 PDF 文本层原生的**（反向对照：直接 fitz 读源
    PDF 即得 PUA，非我方管线引入），属源数据缺字形，故一律**不猜语义映射**。

    两类分开处置（关键区别：能否从上下文无歧义推出真值）：

    ① **分隔符类**——按左右上下文可无歧义还原（2 码点，2026-09-15 首轮实测）：
       - U+E011：日期/人名分隔位——'2009\\ue01103\\ue01116发布'（真值 2009-03-16）、
         'Kennard\\ue011Stone算法'（真值 Kennard-Stone）
       - U+E788：数值前空格位——'内径为\\ue78876+2/0mm'（真值 内径为 76+2/0mm）
       规则：数字↔数字 → '-'；其余 → 空格。

    ② **装饰类**——**无真值、只能剥离**（6 码点，新语料 231 部复测新增）：
       这些是项目符号、表格分隔、版权页位标，视觉上不代表任何字符；
       映射为空会**并字**（'\ue5f9研究报告' → '研究报告' 尚可，但相邻数字会粘连），
       故统一映射为**空格**（保词界、不造假数据）。
       - U+E5F9 项目符号（'\\n\ue5f9研究报告\\n\ue5f9概念设计'）
       - U+E79F 项目符号（'—\\n\ue79f\\n9\\n5\\n0'）
       - U+E5CF 表格空值分隔（'—\\n\ue5cf\ue5cf\\n电力\\nkW·h'）
       - U+E6E6/U+E6F3 表头分隔（'R1\ue6e6\ue6f3\\nNPT1\ue6e6\ue6f3'）
       - U+E012 版权页/书号位标（'版权专有 侵权必究\\n\ue012\\n书号:'）

    **仍然只报告、不映射**（拿不到确定真值，猜就是造假数据）：
       U+E3E4 / U+E2C5 / U+E54F —— 人名缺字（'张\ue3e4\ue3e4、马洪杰'）；
       U+E03C —— 公式位（'r2\ue03cQ=Q0-r2'，可能是减号，但不确定）。
    这些由 `pua-residue` 判据持续上报，等待识别层（VLM 像素 OCR）取回真字。
    """
    if not text:
        return ""
    has_sep = any(c in _PUA_SEP_CHARS for c in text)
    has_dec = any(c in _PUA_DECOR_CHARS for c in text)
    if not (has_sep or has_dec):
        return text
    out: list[str] = []
    n = len(text)
    for i, ch in enumerate(text):
        if ch in _PUA_DECOR_CHARS:
            out.append(" ")
        elif ch in _PUA_SEP_CHARS:
            left = text[i - 1] if i else ""
            right = text[i + 1] if i + 1 < n else ""
            out.append("-" if (left.isdigit() and right.isdigit()) else " ")
        else:
            out.append(ch)
    return "".join(out)


#: 分隔符类私用区字符（实测两码点；逐个判定左右上下文，不用正则防相邻漏判）
_PUA_SEP_CHARS = "\ue011\ue788"

#: 装饰类私用区字符（无真值可还原，统一映射空格）。
#: 逐码点均来自实测证据，**不允许**把"看起来像"的码点加进来：
#: 加错会把缺字形的人名/公式数字悄悄吃掉（比留着 PUA 更糟——留着至少还能被
#: `pua-residue` 判据抓到）。
_PUA_DECOR_CHARS = "\ue012\ue5cf\ue5f9\ue6e6\ue6f3\ue79f"


def strip_block_noise(text: str | None) -> str:
    """行级通用噪音清洗（2026-08-29，GB/T 34406 实测，语料级；幂等）。

    ① 整行即水印（URL ± 页码 ± 点线，剥后为空）→ 删行——盗版标准站每页页眉
    'www.bzfxw.com' 独立行实测；行中 URL 一律不动（正文合法引用零风险）。
    ② 剥公式编号引导点线（'…………………………（1）' NFKC 后连排 ≥4 点；
    正文省略号 '……' 至多 2 个 → NFKC 后 '...' 不命中）。
    """
    if not text:
        return ""
    out: list[str] = []
    for ln in text.split("\n"):
        # 整行即水印：剥 URL 后仅剩空白或页码 → 删行
        if _RE_WM_URL.search(ln):
            rest = _RE_WM_URL.sub("", ln).strip()
            if not rest or _RE_WM_PAGENO.fullmatch(rest):
                continue
        ln = _RE_FORMULA_DOTS.sub(" ", ln)
        if ln.strip():
            out.append(ln)
    return "\n".join(out)


def reflow_sqrt_formulas(text: str | None) -> str:
    """根号套分式的行序重排（2026-08-29，GB/T 34406 式(1)(2) 实测，语料级）。

    PDF 文本层把「√ 覆盖整个分式」的二维结构压成线性行序：分子行（含等号，
    如 'R=1-∑(^Ci-Ci)2'）、分母行（如 '∑(Ci-Ci)2' 或 'm'）、根号字形独立成行
    且排在最后。直接压平即成 'R=1-∑(...)2∑(...)2√'——根号悬尾，读者看不出
    管辖范围（用户实测反馈"根号没了"）。本函数重排为数学读序
    'R=√(分子/分母)'。

    触发条件（保守，逐例可人工复核）：'√' 独立成行，且其前紧邻 ≥1 行公式行
    （无中文句读、非点线），向上回溯至含 '=' 的等式行收束；等式左部保持
    原位，分子/分母以 '/' 连接置于 √() 内。无等式行、遇中文标点、√ 行中
    出现（非独立行）一律不动——正常叙述零风险。
    """
    if not text or "√" not in text:
        return text or ""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i]
        if ln.strip() == "√":
            # 向上回溯收集连续公式行，直到含 '=' 的等式行（含）
            j = i - 1
            buf: list[str] = []
            while j >= 0:
                cand = lines[j].strip()
                if not cand or cand == "√" or _RE_FORMULA_DOTS.search(cand):
                    break
                if re.search(r"[。；，、：]", cand):
                    break
                buf.append(cand)
                if "=" in cand:
                    break
                j -= 1
            if len(buf) >= 2 and "=" in buf[-1]:
                m = re.match(r"^([^=]+=)(.+)$", buf[-1])
                if m:
                    left, num = m.group(1), m.group(2).strip()
                    den = "/".join(reversed(buf[:-1]))
                    del out[-len(buf):]
                    out.append(f"{left}√({num}/{den})")
                    i += 1
                    continue
        out.append(ln)
        i += 1
    return "\n".join(out)


def normalize_math_symbols(text: str | None) -> str:
    """纯文本里的 LaTeX 命令泄漏 → Unicode 符号（幂等；入库/显示层兜底）。

    背景（2026-08-26）：MinerU 把 ≤ 写成 ``\\leqslant`` 直接落在 content_text 纯文本
    （如 GB 30871-2022 9.1 "40t ≤slant m ≤slant 100t"），卡片显示 "≤slant"。
    ``latex_to_text`` 只处理 <eq> 包裹的公式，纯文本泄漏需本函数兜底。
    """
    if not text:
        return ""
    t = text
    for pat, sym in _LATEX_SYMBOLS.items():
        t = t.replace(pat, sym)
    # MinerU 剥反斜杠的泄漏形态（≤slant / ≥slant，实测 GB 30871-2022 9.1）
    for pat, sym in _LEAKED_SYMBOLS:
        t = t.replace(pat, sym)
    # 数字上标/下标泄漏（m^{2} / h_{w}）→ Unicode 上下标
    t = re.sub(r"\^\s*\{(\d+)\}", lambda m: m.group(1).translate(_SUP_SCRIPTS), t)
    t = re.sub(r"_\s*\{(\d+)\}", lambda m: m.group(1).translate(_SUB_SCRIPTS), t)
    # 残留裸命令（\xyz）与花括号清掉
    t = re.sub(r"\\[A-Za-z]+", "", t)
    t = t.replace("{", "").replace("}", "")
    # 2026-09-02 保留公式/量纲符号（GB/T 1.1/1028/1029 自动对账实测缺失）：
    # 组合重音(尖帽´ U+00B4/上划线¯ U+00AF/combining)、除号 ÷、正负号 ±、幂 ^、下划线 _，
    # 以及组合用 U+0300-U+0304（后续 NFKC 折叠为预组合），明确不剥，避免公式/量纲符号丢失。
    t = re.sub(r"([\u00B4\u00AF\u00F7\u00B1^_\u0300-\u0304])", r"\1", t)
    return t


#: '数字被劈开 + 单位'（单位锚定）。第二组 1-4 位；合并条件（防误合并，
#: 见 _glue_split_values）：首组为单个数字，或次组以 0 开头（'10 00 µ'→1000 µ）。
#: 实测反例保护：'图 23 60 Hz'（图号 23 + 频率 60 Hz）首组两位、次组不以 0 开头 → 不合并。
_RE_SPLIT_VALUE = re.compile(
    r"(?<![\d.])(\d{1,2})\s+(\d{1,4})(\s*)(?="
    r"(?:µ|μ|mm|cm|kg|mg|g|ms|min|mL|mol|mmol|kV|kHz|kPa|MPa|kW|kJ"
    r"|m|s|h|L|V|A|N|Pa|Hz|W|J|℃|°C|%|Ω|r/min)(?![A-Za-z]))")

#: 已知 2 字母单位/符号（空格形态 → 合并）：'m m'→'mm'、'c m'→'cm'、'k g'→'kg'、
#: 'k V'→'kV'、'p H'→'pH'。**白名单而非通用 2 字母规则**——'F = m a'（变量乘积）
#: 与 'm m' 同形，通用规则必然误伤；白名单只认真实单位。
_TWO_LETTER_UNITS = frozenset({
    "mm", "cm", "km", "dm", "nm", "kg", "mg", "kV", "mV", "mA", "kW", "kJ", "Hz",
    "Pa", "mL", "kN", "ms", "ns", "pH", "kW", "dL", "µL", "μg", "µg", "µA", "µV",
    # 2026-09-15 收敛循环第 7 轮：'in'（英寸，实测 GB/T 10238-2015 9.2.4.2
    # '±1 / 16 i n' 真值 1/16 in）。变量乘积（'m a'）仍不在白名单 → 不受影响。
    "in",
})

#: 公式内两类**行级**劈开（收敛循环第 7 轮，spaced-run 39 部实测）：
#:  ① `1 . 0`（数字-点-数字，点因紧贴 CJK 未与数字同段：'尺寸应测量1 . 0 mm'）
#:  ② `0.5U N` / `P 1 E`（下标字母/数字被空格拆开：'0.5U N'、'P 1 E'）
#: 都是**无歧义**形态（前后必有数字锚定或混合字母数字），故可在行级先粘；
#: 反向保护：'F = m a'（纯字母乘积）与 '2 m'（合法数值+单位间隔）不在此列。
_RE_GLUE_DOT_SPLIT = re.compile(r"(?<=\d)[ \t]+[.][ \t]+(?=\d)")
#: 点号**单侧**带空格的劈开：'0. 3484'（点后空格）/'0 .3484'（点前空格）。
#: 实测 GB/T 13277.3-2015 5.1.2 'ρ = 0. 3484 × ( p b - 0. 378 p v )/T'。
_RE_GLUE_DOT_ONE_SIDE = re.compile(r"(?<=\d)[.][ \t]+(?=\d)|(?<=\d)[ \t]+[.](?=\d)")
#: 紧贴标点/括号/运算元的数字对被空格拆开：'(1 8 - γ)'、'过5 0 p C'、'2 3 ° C'。
#: 关键限定：数字对**前面必须紧贴一个非空白非字母数字字符**（括号/中文/运算符），
#: 这样 '表 5 0'（空格分隔的独立数字）不会被误粘。实测 GB/T 15371-2023 6.4
#: '16 n c /(1 8 - γ)'、GB/T 1094.3-2017 11.3.5 '超过5 0 p C'、
#: GB/T 14048.10-2016 9.2.1 '2 3 ° C ± 5 ° C'。
_RE_GLUE_ATTACHED_DIGIT_PAIR = re.compile(
    r"(?<=[^\sA-Za-z0-9])(\d)[ \t]+(\d)(?![\dA-Za-z])")
#: 字母-数字-字母（下标数字被拆）：'P 1 E' → 'P1E'，'T E , 0' 不在此列
_RE_GLUE_MIXED_RUN = re.compile(
    r"([A-Za-z])[ \t]+(\d)[ \t]+([A-Za-z])(?![A-Za-z])")
#: 数字后**两个连续单大写字母**（下标/缩写的字母对被拆）：'1.0 U N' → '1.0 UN'。
#: 要求**成对**：单个大写字母不粘（防把表格相邻单元 '2 B' 粘成 '2B'）。
_RE_GLUE_UPPER_PAIR = re.compile(
    r"(?<=\d)[ \t]+([A-Z])[ \t]+([A-Z])(?![A-Za-z])")


def _glue_formula_fragments(line: str) -> str:
    """行级粘合公式内无歧义的劈开形态（见上方常量注释）。"""
    if " " not in line and "\t" not in line:
        return line
    line = _RE_GLUE_DOT_SPLIT.sub(".", line)          # '1 . 0' → '1.0'（点是内容，不能吞）
    line = _RE_GLUE_DOT_ONE_SIDE.sub(".", line)       # '0. 3484' / '0 .3484' → '0.3484'
    line = _RE_GLUE_ATTACHED_DIGIT_PAIR.sub(r"\1\2", line)  # '(1 8' → '(18'
    line = _RE_GLUE_UPPER_PAIR.sub(r" \1\2", line)    # '1.0 U N' → '1.0 UN'
    line = _RE_GLUE_MIXED_RUN.sub(r"\1\2\3", line)    # 'P 1 E' → 'P1E'
    return line


def _glue_split_values(line: str) -> str:
    r"""数值被劈开的合并：'6 10 g'→'610 g'、'1 00 µ'→'100 µ'（单位锚定）。

    2026-09-15 全库文本审计发现：`glue_ocr_spaced_units` 的 token 级粘合只
    合并**单字符** token（'7 9'→'79'），而「数字 + 数字」多字符形态
    （'6 10'、'1 00'、'10 00'、'4 0'）不合并——实测 10 部文档 18 处（10541
    镀锌层附着量 '6 10 g / m ²' 真值 610 g/m²；11115 试样厚度 '6 50 µ m' 真值 650 µm）。

    合并条件（两条独立，宁少勿滥）：
      ① 首组为**单个数字**（'1 10 L'→110 L、'4 0 W'→40 W），或
      ② 次组**以 0 开头**（'10 00 µ'→1000 µ——独立数字不会以 0 开头）
    反例保护：'图 23 60 Hz'（图号 + 频率）首组两位且次组不以 0 开头 → 不合并。
    且必须**后随单位**（无单位锚定不猜，'第 6 10 章' 类复合编号不受扰）。
    """
    def _repl(m: re.Match) -> str:
        first, second = m.group(1), m.group(2)
        # ① 首组单个数字（'1 10 L'/'4 0 W'）；② 次组以 0 开头且 ≤2 位
        # （'10 00 µ'→1000 µ）。② 限 ≤2 位是为保护合法千分位 '12 000'（3 位）。
        if len(first) == 1 or (second.startswith("0") and len(second) <= 2):
            return f"{first}{second}{m.group(3)}"
        return m.group(0)
    return _RE_SPLIT_VALUE.sub(_repl, line)


def _glue_two_letter_units(line: str) -> str:
    r"""已知 2 字母单位去空格（'m m'→'mm'、'k g'→'kg'、'p H'→'pH'）。

    2026-09-15 残留修复：`_collapse_latex_spacing` 的字母段规则门槛 ≥3（为保护
    'F = m a' 变量乘积），于是 2 字母单位（mm/cm/kg/kV/pH）在 LaTeX 里残留空格
    ——全库审计 unit-midspace 17 部文档 33 处未降。改用**已知单位白名单**：
    拼接结果在表内才合并，'m a'/'c a' 等组合不在表内 → 变量乘积仍受保护。
    """
    def _repl(m: re.Match) -> str:
        joined = m.group(1) + m.group(2)
        if joined in _TWO_LETTER_UNITS:
            return joined + m.group(3)
        return m.group(0)
    return _RE_TWO_LETTER_SPLIT.sub(_repl, line)


#: 两个单字母之间的空格 + 其后紧跟词边界（拼接后查白名单决定是否合并）
_RE_TWO_LETTER_SPLIT = re.compile(
    r"(?<![A-Za-z])([A-Za-zµμ])\s+([A-Za-z])(?![A-Za-z])(\s?)")


def glue_ocr_spaced_units(text: str | None) -> str:
    """OCR 通道的保守粘合（2026-09-14，OCR 循环轮次 4/7/12 同类问题 3 次达线）。

    背景：ch_server OCR 对低分 span 的单位/数字逐字符拉开——实测 GB/T
    10058 "0 . 7 0 m / s ²0"、GB/T 10238 "± 2 0 0 r / * m i n" /
    "T = 7 8 . 2 + 2 0 . 0 2 B"（跨 3 文档同类累计 3 次，触发根因修复）。
    文本层路径的 glue_spaced_formulas 不覆盖此形态（点号不进 buf、跨型
    粘合对 OCR 噪声过激）。

    保守规则（与文本层 glue 的差异，全部来自 OCR 噪声实测形态）：
    - 数字段与字母段**分别粘、不跨型**（防 "s79" 类粘连——OCR 拉开段
      的型边界就是原词边界）；段间空格保留。
    - 数字段允许内嵌 '.'（小数：'7 8 . 2' → '78.2'——文本层 glue 不吃点）。
    - 段门槛均 ≥2（'m m'→'mm'/'7 9'→'79'。裸枚举 'A、B' 国标排版带
      顿号无空格；空格分隔枚举未见实测形态，误粘风险记录在案）。
    - **下标/上标/希腊字符进段**（2026-09-15 残留修复，轮次 22 实测
      GB/T 10593.2 'S ₑ = 1000 × ( C ₁ V ₁ - C ₀ V ₀ )'、'C ₛ ᵢ ₜ = α • v ₛ ᵢ ₙ d'：
      初版单字符集只有 ASCII，ASCII 单位治好了而下标型公式变量漏着）。
      与文本层 glue 的 subsup/greek 规则对齐；'m ³'→'m³'、'C ₛ ᵢ ₜ'→'Cₛᵢₜ'。
    - 幂等；正常行（无逐字符空格）零变化。
    """
    if not text or " " not in text:
        return text or ""
    out_lines: list[str] = []
    for line in text.split("\n"):
        line = _glue_split_values(line)      # 数值劈开（单位锚定）先合，再走 token 级
        out = []
        buf: list[str] = []
        cur: str | None = None   # 'n' | 'a' | 's'（下标/上标/希腊）
        has_script = False       # 段内含下标/上标 → 2 字母白名单规则不适用
        has_greek = False        # 段内含希腊/微符号 → 同上（'Δ t'→'Δt'）

        def _flush() -> None:
            nonlocal buf, cur, has_script, has_greek
            if buf and cur is not None and len(buf) >= 2:
                if cur == "a" and len(buf) == 2 and not (has_script or has_greek):
                    # 2 字母段只按**已知单位白名单**合并（'m m'→'mm'、'p H'→'pH'）；
                    # 非单位 2 字母段是「变量乘积」（'F = m a'），粘合会把公式
                    # 变量粘成一个词 —— 2026-09-15 与 latex 路径统一此契约。
                    # 下标/上标/希腊参与的段例外（贴附无歧义：'S ₑ'/'m ³'/'Δ t'）。
                    joined = "".join(buf)
                    if joined not in _TWO_LETTER_UNITS:
                        out.extend(buf)
                        buf = []
                        cur = None
                        has_script = has_greek = False
                        return
                out.append("".join(buf))
            else:
                out.extend(buf)
            buf = []
            cur = None
            has_script = has_greek = False

        for tok in line.split(" "):
            if _RE_OCR_SINGLE.match(tok):
                if _RE_OCR_SUBSUP.match(tok):
                    kind = "s"
                elif tok.isalpha():
                    kind = "a"
                else:
                    kind = "n"
                if _RE_OCR_SUBSUP.match(tok):
                    has_script = True
                elif _RE_OCR_GREEK.match(tok) or tok == "µ":
                    has_greek = True
                if cur is None:
                    cur, buf = kind, [tok]
                elif kind == "s":
                    buf.append(tok)        # 下标/上标总并入当前段（'m' + '³'）
                elif cur == "s":
                    # 段首下标遇字母/数字 → 断段（防 '₁V' 反序误粘）
                    _flush()
                    cur, buf = kind, [tok]
                elif cur == kind:
                    buf.append(tok)
                else:
                    _flush()               # 数字段↔字母段：型边界即词边界
                    cur, buf = kind, [tok]
            elif tok == "." and cur == "n":
                buf.append(tok)     # 数字段内小数点
            else:
                _flush()
                if tok:
                    out.append(tok)
        _flush()
        # 行级补粘必须在 **token 级之后**：'7 8 . 2' 要靠 token 级把 '7','8','.','2'
        # 合成 '78.2'；若行级先跑会把 ' . ' 提前定型成 '7 8.2' 反而挡住它
        # （2026-09-15 实测回归：test_glue_ocr_units 两条用例因此变红）。
        out_lines.append(_glue_formula_fragments(" ".join(t for t in out if t)))
    return "\n".join(out_lines)


_RE_OCR_SUBSUP = re.compile(r"^[₀-₉⁰-⁹¹²³ⁿᵢₛₜₑₓᵤᵥₐₒᵣᵦᵧₚₖₘₙᵈᵍᵗʰʲᵏˡᵐˢᵛʷʸᶻ]$")
_RE_OCR_GREEK = re.compile(r"^[\u0391-\u03c9\u00b5]$")
_RE_OCR_SINGLE = re.compile(
    r"^(?:[A-Za-z0-9]|[₀-₉⁰-⁹¹²³ⁿᵢₛₜₑₓᵤᵥₐₒᵣᵦᵧₚₖₘₙᵈᵍᵗʰʲᵏˡᵐˢᵛʷʸᶻ]|[\u0391-\u03c9\u00b5])$")


def glue_spaced_formulas(text: str | None) -> str:
    """修复"公式字母被拉开"：PDF 文本层逐字符定位 → 提取出 "C a O"、"Y ₂ O ₃"。

    规则（2026-08-28，实测 44% 可见档受影响）：按"格"处理——制表符是表格
    列边界，绝不跨格粘连；格内连续单字符 token 且含字母：
    ≥3 个 → 粘回（"C a O"→"CaO"、"N a ₂ C O ₃"→"Na₂CO₃"）；
    2 个且含上下标 → 粘回（"m ³"→"m³"——上下标只出现在公式/单位）；
    "2 h" 这类数字+单位（国标正确的空格排版）与纯数字列永不变动。
    已粘合文本幂等无变化。
    """
    if not text or " " not in text:
        return text or ""
    single = re.compile(
        r"^[A-Za-z0-9₀-₉⁰-⁹¹²³ａ-ｚＡ-Ｚ０-９\u0391-\u03c9]$")
    letter = re.compile(r"^[A-Za-zａ-ｚＡ-Ｚ\u0391-\u03c9]$")
    greek = re.compile(r"^[\u0391-\u03c9]$")
    subsup = re.compile(r"^[₀-₉⁰-⁹¹²³]$")
    out_lines: list[str] = []
    for line in text.split("\n"):
        cells = []
        for cell in line.split("\t"):
            res: list[str] = []
            buf: list[str] = []
            has_letter = False
            has_sub = False
            has_greek = False

            def _flush() -> None:
                nonlocal buf, has_letter, has_sub, has_greek
                # 2026-09-02 希腊变量粘合：'Δ t₁,₀'/'Δ t₀.₅' 公式变量被 OCR
                # 拉开（Δ t 2 token 无上下标此前不粘）→ 含希腊字母且 >=2 → 粘
                # （公式希腊变量，正文罕见）。
                if has_letter and (len(buf) >= 3 or (len(buf) >= 2 and has_sub)
                                   or (len(buf) >= 2 and has_greek)):
                    res.append("".join(buf))
                else:
                    res.extend(buf)
                buf = []
                has_letter = False
                has_sub = False
                has_greek = False

            for tok in cell.split(" "):
                if tok and single.match(tok):
                    buf.append(tok)
                    if letter.match(tok):
                        has_letter = True
                    if greek.match(tok):
                        has_greek = True
                    if subsup.match(tok):
                        has_sub = True
                else:
                    _flush()
                    if tok:
                        res.append(tok)
            _flush()
            cells.append(" ".join(res))
        out_lines.append("\t".join(cells))
    return "\n".join(out_lines)


#: 「式中」说明条目：量符号（拉丁 / fitz 罗马斜体伪字区 犃-犫）+ 破折号 + 描述。
#: 负向环视排除前随字母/伪字/已织入的 U+0304 —— RMSEP 的尾段 'EP'、'C̄i' 的
#'i'（前邻 U+0304）都不会被误当符号主体，幂等。
_RE_MEAN_ENTRY = re.compile(
    r"(?<![A-Za-z\u7283-\u72ee\u0304])"
    r"(?P<sym>\^?[A-Za-z\u7283-\u72ee][A-Za-z0-9\u7283-\u72ee]{0,2})"
    r"(?P<dash>———|───|——|──|—)"
    r"(?P<desc>[^；;\n。]{0,60})"
)


def weave_meaning_marks(text: str | None) -> str:
    """「式中」符号说明行的平均值 bar 织入（2026-08-29，语料级统计记法规则）。

    双层扫描 PDF 的平均值横线（量符号顶上的 bar）是矢量画线，文字层无对应
    字符——提取后 'Ci———样品i标准值' 与 'Ci———样品i平均值' 完全同形，
    读者与 LLM 均无法区分（GB/T 34406 3.7 用户实测反馈"ci 顶上的 - 没识别
    出来"）。织入规则（统计记法惯例，非文档特判）：仅「式中」说明段内，
    条目描述含「平均/均值」且量符号为 ≤3 字符简单量 → 主体字母后插组合
    macron（U+0304）：'Ci———样品i的平均值' → 'C̄i———样品i的平均值'。
    带帽符号（^Ci——帽与 bar 不共存）、多字母缩写（RMSEP）、无「平均」描述
    （犿———验证集样品数）一律不动；对已织入文本重复执行无变化（幂等）。
    """
    if not text or "式中" not in text:
        return text or ""
    segs = re.split(r"(式中[：:]?)", text)
    for i in range(1, len(segs) - 1, 2):  # 奇数位 = 「式中」标记，i+1 为说明段
        seg = segs[i + 1]

        def _weave(m: re.Match) -> str:
            sym, dash, desc = m.group("sym"), m.group("dash"), m.group("desc")
            if "平均" not in desc and "均值" not in desc:
                return m.group(0)
            if "^" in sym or "\u0304" in sym:
                return m.group(0)
            return sym[0] + "\u0304" + sym[1:] + dash + desc

        segs[i + 1] = _RE_MEAN_ENTRY.sub(_weave, seg)
    return "".join(segs)


def normalize_wraps(s: str | None) -> str:
    """OCR 折行拼接。幂等：对已拼接文本再执行无变化。

    2026-09-01 退役说明（排版需求反转）：_spans_text 修复假行界后，
    line 级 \n = 原文真实折行，是排版信号而非噪声——新入库/卡片出口/WPS
    出口均不再调用本函数（存量入库时已洗平，幂等性保证零回归）。
    函数保留：读时兜底与历史工具脚本仍可能引用。"""
    if not s:
        return ""
    s = glue_spaced_formulas(s)
    lines = [l.strip() for l in s.split("\n")]
    out: list[str] = []
    for l in lines:
        if not l:
            if out and out[-1] != "":
                out.append("")
            continue
        last = out[-1] if out else None
        if last and last != "":
            prev_ends = bool(_SENT_END_RE.search(last))
            this_para = bool(_PARA_START_RE.match(l))
            if prev_ends and this_para:
                out.append(l)
            else:
                need_space = bool(_ASCII_RE.search(last)) and bool(_ASCII_RE.match(l))
                out[-1] = last + (" " if need_space else "") + l
        else:
            out.append(l)
    return "\n".join(out)


def _find_brace_group(s: str, start: int) -> tuple[str | None, int]:
    r"""从 s[start]（应为 '{'）读平衡花括号组；返回 (内容, 结束下标)。

    \frac/\tag 参数解析用（2026-09-14，OCR 循环轮次 17 公式损伤根因）。
    """
    if start >= len(s) or s[start] != "{":
        m = re.match(r"\s*(\S)", s[start:])
        if not m:
            return None, start
        return m.group(1), start + len(m.group(0))
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
    return None, start


def _wrap_frac_operand(inner: str) -> str:
    r"""\frac 分子/分母含运算符（表达式）→ 括号保护，保语义可读。"""
    t = re.sub(r"\s+", " ", inner.strip())
    if re.search(r"[+\-−=]", t) and len(t.replace(" ", "")) > 2:
        return f"({t})"
    return t


def _convert_frac_tag(t: str) -> str:
    r"""\frac{A}{B} → 'A/B'（表达式加括号）；\tag{…} → 尾部编号（补右括号）。

    背景（2026-09-14，OCR 循环轮次 17，跨 3 文档同类 3 次达线 + 全库普查）：
    latex_to_text 此前无 \frac/\tag 处理——\frac 的分子分母被花括号剥除
    平铺串联（'T_Lmax-T_Lmin T_Lmax+T_Lmo'，**分数线语义丢失**，读者无法
    辨分子分母）；\tag 的编号点线（'………(2'）残留在正文且 MFR 常丢右括号。
    全库普查：parse_out 27,021 文档 213,946 公式 span 中 16,186 含 \frac、
    19,676 含 \tag（4,287 文档受影响）——面修复。

    必须在下标/上标转换（步骤 2/3）**之前**调用：frac 组读取依赖花括号。
    """
    # \frac 递归（嵌套 frac，20 层上限防极端深嵌套）
    for _ in range(20):
        idx = t.find("\\frac")
        if idx < 0:
            break
        j = idx + 5
        while j < len(t) and t[j].isspace():
            j += 1
        num, j2 = _find_brace_group(t, j)
        if num is None:
            t = t[:idx] + t[j:]
            continue
        k = j2
        while k < len(t) and t[k].isspace():
            k += 1
        den, k2 = _find_brace_group(t, k)
        if den is None:
            t = t[:idx] + t[j:]
            continue
        t = t[:idx] + _wrap_frac_operand(num) + "/" + _wrap_frac_operand(den) + t[k2:]

    # \tag{...} → 编号（'………(2'→'(2)'；纯数字/字母编号 → '(3)'；空 tag 消除）
    def _tag_repl(m: re.Match) -> str:
        inner = m.group(1).strip()
        num = re.search(r"(\([0-9A-Za-z.\-]*?)$", inner)
        if num:
            s = num.group(1)
            if not s.endswith(")"):
                s += ")"
            return " " + s
        if re.fullmatch(r"[0-9A-Za-z.\-]+", inner):
            return f" ({inner})"
        return " " + inner if inner else ""
    t = re.sub(r"\\tag\s*\{([^{}]*)\}", _tag_repl, t)
    return t


#: LaTeX 环境包装（`\begin{array}{rl}` / `\end{array}`，含可选列格式组）
_RE_TEX_ENV = re.compile(r"\\(?:begin|end)\s*\{[A-Za-z*]+\}\s*(?:\{[^{}]*\})*")
#: 裸露的 array 列格式残留：`array r l` / `array l z`（环境标记被上游或本函数
#: 的命令剥离器吃掉后，只剩 `array` + 列格式）。**首 token 限定 l/r/c**（LaTeX
#: 列格式符），防把 `array x y z = 5` 里的真变量吃掉（内容丢失比残留更糟）。
_RE_TEX_ARRAY_SPEC = re.compile(r"\barray\s+[lrc]\b(?:\s+[a-z]{1,2}\b){0,2}")
#: 行分隔：`\\`、`\&`、`\\ &`（array 的行结束符被截断成单反斜杠）都还原为换行
_RE_TEX_ROWBRK = re.compile(r"\\{1,2}\s*(?=&|$)", re.M)
#: 零宽/细空格命令（`\,` `\;` `\!` `\:`）→ 空格
_RE_TEX_THINSP = re.compile(r"\\[,;!:>]")


def _strip_latex_arrays(t: str) -> str:
    r"""LaTeX `array` 环境 → 可读文本（2026-09-15 收敛循环第 5 轮根因）。

    实测缺陷（GB/T 10095.2-2023 E.1/E.2，全库 45 部）：
    公式 `\begin{array}{rl} z &= \min(z,200) \\ &= \min(40,200) \\ &= 40
    \end{array}` 经 `latex_to_text` 后变成
    ``array l z = * min ( z , 200 ) \ & = * min ( 40 , 200 ) \ = 40``
    —— `array`、列格式、`&`、`\` 全部漏进条款正文（同时触发 spaced-run /
    ocr-wide-space-units / formula-flattened 三个类，是当前最大单点缺陷）。

    根因：通用命令剥离 `re.sub(r"\\[A-Za-z]+", "", s)` 把 `\begin`/`\end`
    当普通命令删掉，**却留下 `{array}{rl}` 的花括号内容与 `&`/`\\` 分隔符**。
    规范所有者就是本函数：环境语义必须在这里落地，而不是让下游猜。

    处理顺序（先语义后清理）：
      ① 行分隔 `\\`/`\&` → 换行（一行的推导拆成多行，不丢结构）
      ② 列分隔 `&` → 空格
      ③ 环境包装与裸露列格式 → 删
      ④ 细空格命令 → 空格
    """
    if "array" not in t and "\\" not in t and "&" not in t:
        return t
    t = _RE_TEX_ENV.sub(" ", t)
    t = _RE_TEX_ROWBRK.sub("\n", t)
    t = t.replace("\\\\", "\n")
    t = t.replace("&", " ")
    t = _RE_TEX_ARRAY_SPEC.sub(" ", t)
    t = _RE_TEX_THINSP.sub(" ", t)
    return t


#: 标签里的**逗号代点**（2026-09-15 收敛循环第 19/20 轮，punctuation-substitution）。
#: OCR 把标签中的点识别成逗号：公式号 '(D,8)'、表号 '表B,4'、图号 '图A,1'。
#: 实测 GB/T 16411-2023 D.1.2.3.3：正文引用 '(D.7)' 正常，而公式编号处出现 'D,8'。
#: 归一是**无歧义**的：`(大写字母 , 数字)` 与 `表/图 + 大写字母 , 数字` 都不是合法排版。
_RE_LABEL_COMMA_PAREN = re.compile(r"([（(]\s*[A-Z])\s*,\s*(?=\d)")
_RE_LABEL_COMMA_PREFIX = re.compile(r"([表图附录]\s*[A-Z])\s*,\s*(?=\d)")


def normalize_label_comma(text: str | None) -> str:
    r"""标签逗号代点归一：'(D,8)'→'(D.8)'、'表B,4'→'表B.4'。

    类名 `punctuation-substitution` 的本意形态；检测器（classify）在排除
    "单位符号/数字前缀"后只命中真形态（'D,8'），所有者层在此做实际清洗——
    避免"检测器报缺陷、清洗器不清洗"的口径错位。
    """
    t = text or ""
    if "," not in t:
        return t
    t = _RE_LABEL_COMMA_PAREN.sub(r"\1.", t)
    return _RE_LABEL_COMMA_PREFIX.sub(r"\1.", t)


def latex_to_text(latex: str) -> str:
    r"""MinerU <eq> LaTeX → 可读文本。
    例：'h _ { \mathrm { ~ w ~ } } / \mathrm { m }' → 'h w/m'
    （'h' 与 'w' 为 2 字母段，按变量乘积保护规则不合并；'
    'm i n'/'k P a' 类 ≥3 字母段合并且 'g / m' 去斜杠空格 → 'g/m'）

    2026-09-01 保真修复（GB/T 24276 24 条独立公式逐条实测）：
    ① 包裹命令扩容（\pmb/\bf/\mathbb/\textrm/…）并支持一层嵌套
       （\mathrm{\textmu} 此前剥不动）；
    ② 符号替换改词边界单遍正则——\pmb 不再被 \pm 前缀误吃成 '±b'；
    ③ 下标/上标组内容先过符号映射+剥命令再 translate——\circ/\textmu
       不再被逐字下标化残留 '\ₜₑₓₜₘᵤ'；
    ④ '\ '（LaTeX 显式空格）转空格，不再残留 '\ '。
    2026-09-15 逐字符空格归并（_collapse_latex_spacing，全库公式审计）：
    MinerU 对宽距字符逐字符输出空格（'6 1 0 g / m ²'），本函数在公式文本层
    归并（'610 g/m²'），比下游按行粘合更根本。
    2026-09-15 array 环境（_strip_latex_arrays，收敛循环第 5 轮）：
    `\begin{array}{rl}` 的列格式与 `&`/`\\` 不再漏进正文（45 部实测缺陷）。
    """
    t = _strip_latex_arrays(latex)
    # 1) 剥命令包裹：\mathrm{...} 等取其内容（支持一层嵌套，迭代处理）
    for _ in range(3):
        t2 = re.sub(
            r"\\(?:mathrm|text|textrm|mathbf|mathit|mathbb|mathsf|mathtt"
            r"|pmb|bf|boldsymbol)\s*\{((?:[^{}]|\{[^{}]*\})*)\}",
            r"\1", t)
        if t2 == t:
            break
        t = t2

    # 1.5) \frac → 'A/B' + \tag → 编号（2026-09-14 公式语义保真；必须在
    # 下标/上标转换前——frac 组读取依赖花括号）
    t = _convert_frac_tag(t)

    # 符号映射（词边界单遍）：长键优先 + (?![A-Za-z]) 防前缀误吃
    def _syms(s: str) -> str:
        s = _SYM_RE.sub(lambda m: _LATEX_SYMBOLS[m.group(0)], s)
        s = s.replace("~", " ").replace("\\ ", " ")
        return re.sub(r"\\[A-Za-z]+", "", s)

    # 2) 下标：_ { x } 或 _x → Unicode 下标（组内先剥命令/映射符号）
    def sub_repl(m):
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        return _syms(inner).translate(_SUB_SCRIPTS)
    t = re.sub(r"_\s*\{([^{}]*)\}|_\s*(\S)", sub_repl, t)
    # 3) 上标：^ { x } 或 ^x → Unicode 上标（同 2）
    def sup_repl(m):
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        return _syms(inner).translate(_SUP_SCRIPTS)
    t = re.sub(r"\^\s*\{([^{}]*)\}|\^\s*(\S)", sup_repl, t)
    # 4) 符号映射 + 清理残留命令与花括号
    t = _syms(t)
    t = t.replace("{", "").replace("}", "")
    t = re.sub(r"\s+", " ", t).strip()
    return _collapse_latex_spacing(t)


#: 逐字符空格：≥3 个单数字（'6 1 0'→'610'）——MinerU 对宽距数字逐字符输出
_RE_LATEX_DIGIT_RUN = re.compile(r"(?<![\d.])(\d(?: \d){2,})(?![\d.])")
#: 逐字符空格：≥3 个单字母（'m i n'→'min'/'k P a'→'kPa'）。
#: 门限定 ≥3 而非 ≥2 —— 2 字母段是「变量乘积」（'F = m a'）与单位（'m m'）的
#: 同形歧义，误合并会把公式变量粘成一个词，故保守不合并 2 字母段。
_RE_LATEX_LETTER_RUN = re.compile(r"(?<![A-Za-z\u0391-\u03c9])([A-Za-z\u0391-\u03c9](?: [A-Za-z\u0391-\u03c9]){2,})(?![A-Za-z\u0391-\u03c9])")
#: 单位斜杠两侧空格：'g / m'→'g/m'、'r / min'→'r/min'、'm / s'→'m/s'
_RE_LATEX_SLASH = re.compile(r"(?<=[A-Za-z\u0391-\u03c9²³])\s*/\s*(?=[A-Za-z\u0391-\u03c9])")
#: 字母后紧跟的上下标去空格：'m ²'→'m²'（上下标永远贴前字，无歧义）
_RE_LATEX_SCRIPT = re.compile(r"(?<=[A-Za-z\u0391-\u03c9])\s+(?=[\u00b2\u00b3\u2070-\u209c])")
#: 微符号前缀去空格：'µ m'→'µm'（µ 后必接单位字母）
_RE_LATEX_MICRO = re.compile(r"(?<=[\u00b5\u03bc])\s+(?=[A-Za-z])")
#: 下标后紧跟字母去空格：'K ₘ b'→'Kₘb'（GB 量符号记法下标贴前后字）
_RE_LATEX_SUBTAIL = re.compile(r"(?<=[\u2080-\u209c])\s+(?=[A-Za-z])")
#: 连续下标之间去空格：'T Lₘ ₐ ₓ'→'T Lₘₐₓ'（多字符下标是一体）
_RE_LATEX_SUBRUN = re.compile(r"(?<=[\u2080-\u209c])\s+(?=[\u2080-\u209c])")


def _collapse_latex_spacing(t: str) -> str:
    r"""LaTeX 转文本后的逐字符空格归并（2026-09-15，全库公式审计）。

    背景：MinerU 的 LaTeX 对宽距字符**逐字符输出空格**——实测 GB/T 10541
    `inline_equation` 原文 `6 1 0 ~ \mathrm { g / m ^ { 2 } }`（真值 610 g/m²）、
    GB/T 11115 `6 5 0 ~ \mu \mathrm { m } \pm 1 0 0 ~ \mu \mathrm { m }`（真值
    650 µm±100 µm）。此前 latex_to_text 只把连续空格折叠为一个，逐字符空格
    原样落库（'6 1 0 g / m ²'、'r / m i n'、'k P a'）——本函数是本形态的
    规范所有者（公式文本层），比在下游按行粘合更根本。

    规则（三条，均保守，全部来自实测形态）：
    - 数字段 ≥3 个单数字 → 合并（'6 1 0'→'610'）；**2 个不动**（'1/2 3' 的
      '2 3' 不应合并，防把分数后的独立数字粘进分母）
    - 字母段 ≥3 个单字母 → 合并（'m i n'→'min'、'k P a'→'kPa'）；2 个不动
      （'F = m a' 的变量乘积不得粘成 'ma'）
    - 字母/上下标与字母之间的斜杠去两侧空格（'g / m'→'g/m'、'r / min'→'r/min'）
    - 另复用单位锚定的数值劈开规则（'6 10 g'→'610 g'）
    """
    t = _RE_LATEX_DIGIT_RUN.sub(lambda m: m.group(1).replace(" ", ""), t)
    t = _RE_LATEX_LETTER_RUN.sub(lambda m: m.group(1).replace(" ", ""), t)
    # 已知 2 字母单位（白名单）：'m m'→'mm'、'k g'→'kg'；'m a' 不在表内 → 变量乘积受保护
    t = _glue_two_letter_units(t)
    # 贴附类空格（无歧义，逐条实测）：'m ²'→'m²' · 'µ m'→'µm' · 'K ₘ b'→'Kₘb'
    t = _RE_LATEX_SCRIPT.sub("", t)
    t = _RE_LATEX_MICRO.sub("", t)
    t = _RE_LATEX_SUBTAIL.sub("", t)
    t = _RE_LATEX_SUBRUN.sub("", t)
    t = _RE_LATEX_SLASH.sub("/", t)
    t = t.replace("\\%", "%")
    return _glue_split_values(t)


def clean_eq_tags(html: str | None) -> str:
    """把 content_markdown/content_html 里的 <eq>LaTeX</eq> 转成可读文本（其余标签保留）。"""
    if not html:
        return ""
    return re.sub(r"<eq>(.*?)</eq>", lambda m: latex_to_text(m.group(1)), html)


def html_unescape(s: str | None) -> str:
    """HTML 实体解码（&lt; → < 等）。WPS 导出/纯文本提取前必须做，否则显示字面 &lt;。"""
    if not s:
        return ""
    import html as _html
    return _html.unescape(s)


def strip_tags(s: str | None) -> str:
    """剥除 HTML 标签 + 解码实体（表格单元格 → 纯文本）。"""
    if not s:
        return ""
    t = re.sub(r"<[^>]+>", "", s)
    return html_unescape(t).strip()


#: 图题句形态（2026-08-29，GB/T 34406 附录A 实测，语料级）：
#: '图N<标题>图'——GB 图题以"图"字收尾。图题句 token（'A.1'/'判别分析'）
#: 与表题/表格格天然重叠 → 句级覆盖判定必误伤（实测 '图A.1判别分析相关图'
#: 被当表格句剔掉，图内嵌截图失去锚点）；图题句是必须保留的内容，白名单放行。
#: 2026-09-01 扩展（GB/T 24276 实测）：图题也可"拉丁变量符号"收尾——
#'图 4 不带通风口，有效散热面积A₁>1,25m²的外壳的温度分布系数c'（系数c）。
#: 图4/6/8 的系数表本身即图形内容，题注 token（'不带通风口'/'有效散热面积'/
#: '1,25'）与系数表列值天然重叠 → 覆盖判定必误杀；行丢则页界 run-start
#: [行,页] 随行陪葬（条款6 跨 10/13/15/17 页零分隔的真根因）。题名段放开
#: 到任意非句末字符（下标/单位/空格共存），收尾锚定为"图"或拉丁字母。
_FIG_CAPTION_LINE = re.compile(
    r"图\s*[0-9A-Z]+(?:\.[0-9A-Z]+)?\s*[^。！？；]{0,60}(?:图|[A-Za-z])")


def strip_embedded_table_text(text: str, table_md: str | None) -> str:
    """后端版 stripEmbeddedTable：正文里与表格重复的文字块剔除
    （MinerU 会把表格文字也抽进正文块 → 卡片"正文后再放一遍表格文字"的根因）。
    判定：一行中表格 token 的覆盖率高（该行几乎全由表格内容组成）→ 视为泄漏丢弃。"""
    t = text or ""
    md = table_md or ""
    if not md:
        return t.strip()
    tokens: set[str] = set()
    for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", md, re.S):
        c = strip_tags(cell).replace(" ", "")
        if len(c) >= 1 and c != "-":
            tokens.add(c)
    if not tokens:
        return t.strip()
    kept: list[str] = []
    for line in t.split("\n"):
        flat = line.replace(" ", "")
        if not flat:
            kept.append(line)
            continue
        if _FIG_CAPTION_LINE.fullmatch(line.strip()):
            kept.append(line)  # 图题行白名单：整行即图题（24276 形态无句末标点
            continue           # 拆不出句级 part，必须行级放行，页界不陪葬）
        hits = [tok for tok in tokens if tok in flat]
        overlap_len = sum(len(tok) for tok in hits)
        coverage = overlap_len / max(len(flat), 1)
        if coverage < 0.5 and len(hits) < 3:
            kept.append(line)
            continue
        # 2026-08-29：高粘连行做句级拆分——只丢表格句，保留非表格句。
        # 根因：GB 附录头/正文叙述与表格文字压平粘连成一行（"附录A<标题>见表A.1。表A.1…"），
        # 整行判定把非表格句一起陪葬；句级（。！？；分界）精确剔除。
        # 无标点粘连行（纯表格文字流）拆不出句 → 整 part 高覆盖 → 整行丢（保守回退）。
        parts = [p for p in re.split(r"(?<=[。！？；])", line) if p.strip()]
        if len(parts) > 1:
            saved = []
            for part in parts:
                pf = part.replace(" ", "")
                if not pf:
                    continue
                if _FIG_CAPTION_LINE.search(pf):
                    saved.append(part)  # 图题句白名单：token 与表格重叠是形近，非泄漏
                    continue
                ph = [tok for tok in tokens if tok in pf]
                pcov = sum(len(x) for x in ph) / max(len(pf), 1)
                if pcov < 0.5 and len(ph) < 3:
                    saved.append(part)
            if saved:
                kept.append("".join(saved))
            # 全 part 均为表格句 → 整行丢
            continue
    return "\n".join(kept).strip()


# ========== KaTeX 符号渲染（2026-08-29 用户点名"特殊符号用专门的插件"）==========
# 说明条目行里的 ^Ci（帽，矢量画线文字层无字符只剩 ^ 记号）与 C̄i（weave 织入
# 的组合 macron）转 <span class="katex-sym" data-tex="…">原token</span>——
# content_text 不动（编辑保存/LLM 证据零污染），前端 katex.renderToString
# 渲染真排版（\hat{C}_i / \bar{C}_i，含正确的下标与宽帽）；渲染失败显示
# span 内原 token 文本（渐进增强，零数据丢失）。fitz 罗马斜体伪字区
# （犃-犫，U+7283-72B6）→ ASCII 映射后进 TeX；其余字符保守不动。

_RE_TEX_HAT = re.compile(r"\^([A-Za-z\u7283-\u72ee])([A-Za-z\u7283-\u72ee])?")
_RE_TEX_BAR = re.compile(r"([A-Za-z\u7283-\u72ee])\u0304([A-Za-z\u7283-\u72ee])?")
# 说明条目段（含破折号 ——— 的 <p>）——正文段不动（e^x 等数学记号零误伤）
_RE_MEAN_PARA = re.compile(r"<p>(?:(?!</p>).)*———(?:(?!</p>).)*</p>", re.S)


def _tex_alpha(ch: str | None) -> str | None:
    """单字符 → TeX 可用 ASCII 字母；伪字区映射，其余 None（保守跳过）。"""
    if not ch:
        return None
    o = ord(ch)
    if 0x7283 <= o <= 0x729C:      # 犃..犛 → A..Z
        return chr(65 + o - 0x7283)
    if 0x729D <= o <= 0x72B6:      # 犜..犷 → a..z
        return chr(97 + o - 0x729D)
    return ch if ch.isascii() and ch.isalpha() else None


def _katex_span(token: str, cmd: str, base: str, sub: str) -> str:
    tex = f"\\{cmd}{{{base}}}" + (f"_{{{sub}}}" if sub else "")
    return f'<span class="katex-sym" data-tex="{tex}">{token}</span>'


def katex_sym_html(html: str | None) -> str:
    """展示 html 的式中说明行符号 token → KaTeX span（幂等；仅说明段处理）。"""
    if not html or ("^" not in html and "\u0304" not in html):
        return html or ""

    def _sub_entry(m: re.Match) -> str:
        seg = m.group(0)
        if "katex-sym" in seg:      # 幂等：已处理段不再嵌套
            return seg

        def bar_repl(bm: re.Match) -> str:
            base = _tex_alpha(bm.group(1))
            if not base:
                return bm.group(0)
            sub = _tex_alpha(bm.group(2)) or ""
            return _katex_span(bm.group(0), "bar", base, sub)

        def hat_repl(hm: re.Match) -> str:
            base = _tex_alpha(hm.group(1))
            if not base:
                return hm.group(0)
            sub = _tex_alpha(hm.group(2)) or ""
            return _katex_span(hm.group(0), "hat", base, sub)

        seg = _RE_TEX_BAR.sub(bar_repl, seg)   # bar 先消费（C̄i 的 i 归下标）
        seg = _RE_TEX_HAT.sub(hat_repl, seg)
        return seg

    return _RE_MEAN_PARA.sub(_sub_entry, html)


# ========== 国标排版还原三件套（2026-08-30，GB/T 34406 §4/§5 实测，语料级）==========
# 出口动态重放（_content_html 拼装层），content_text 零污染；三个函数均幂等，
# 在 _inject_formulas 之后调用——<sup> 尖括号会切断 _FORMULA_SEG 的 [^<>] 匹配。

# ① PUA 键横线：双层扫描 PDF 的嵌入字体把基团键位横线（—CH 的 "—"，有机
#    化学基团记法，横线在前）编码到 PUA 私用区（34406 §4 实测 U+E5C6，形态
#    '中\ue5c6CH、\ue5c6NH、\ue5c6OH 等'），浏览器无字形 → 豆腐块（用户读作
#    "扣"）。语义双闸（全库扫描 286 处 PUA+字母 定型）：前一位须是汉字/中文
#    标点/空白（排除乱码行 'F\ue011F()' 的字母夹心形态），后两位须是连续
#    大写字母（排除单字母 '犖\ue011K'、Symbol 串 '\uf03dH W'）；其余 PUA
#    语境一律不动，保守留白待报告。
_RE_PUA_BOND = re.compile(
    r"(?<=[\u4e00-\u9fff\u3001\u3002\uff0c\uff1b\uff1a\uff5e\u3000\s])"
    r"[\ue000-\uf8ff](?=[A-Z][A-Z])")


def pua_bond_dash_html(html: str | None) -> str:
    """展示 html 的 PUA 键横线 → em dash（幂等；content_text 不动）。"""
    if not html or not re.search(r"[\ue000-\uf8ff]", html):
        return html or ""
    return _RE_PUA_BOND.sub("\u2014", html)


# ② 单位负指数上标：PDF 文本层把 cm⁻¹ 拍平成 cm-1（字号/基线偏移在提取时
#    丢失，34406 §4 实测 '4000cm-1~10000cm-1,分辨率优于8cm-1'）。规则：数值
#    后紧跟物理单位白名单 + '-' + 正整数 → <sup>-n</sup>（波数/频率量纲记
#    法）；'图A-1'/'表B-2' 编号连字符不命中（单位前必须是数字）零误伤；
#    白名单外单位与 '-abc' 非数字指数一律不动。
_RE_UNIT_EXP = re.compile(
    r"(?<=\d)(nm|µm|μm|mm|cm|km|mol|min|kPa|MPa|Pa|kJ|kWh|kW|kHz|kg|mg|mL|dB|"
    r"Hz|MJ|J|W|g|t|s|h|m|L|d)-(\d+)(?![0-9A-Za-z])")


def sup_unit_exponents_html(html: str | None) -> str:
    """展示 html 的单位负指数 → <sup> 上标（幂等；content_text 不动）。"""
    if not html or "-" not in html:
        return html or ""
    return _RE_UNIT_EXP.sub(
        lambda m: f"{m.group(1)}<sup>-{m.group(2)}</sup>", html)


# ③ 条款编号排版：国标原文编号与标题间空一格（'5　仪器与设备'），文本层
#    提取后拍平成 '5仪器与设备'/'4原理'（34406 §4/§5 实测）。规则：块级
#    段落起始的 ≤3 段点分编号紧跟汉字 → 补一个空格。'2026年'（\d{1,2} 限长
#    后回溯失败）、'0.5mol'（编号后非汉字）天然不命中；已空格幂等（数字后
#    是空格不再满足汉字前顾）。
_RE_CLAUSE_NO_GAP = re.compile(
    r"(<(?:p|h[1-6])(?:\s[^>]*)?>)(\d{1,2}(?:\.\d{1,2}){0,3})(?=[\u4e00-\u9fff])")


def space_clause_numbers_html(html: str | None) -> str:
    """展示 html 的段首条款编号补空格（幂等；content_text 不动）。"""
    if not html or ("<p" not in html and "<h" not in html):
        return html or ""
    return _RE_CLAUSE_NO_GAP.sub(
        lambda m: f"{m.group(1)}{m.group(2)} ", html)


# ---- 入库路（纯文本形态，2026-08-30）：与出口同规则、形态收敛 ----
# pua_bond_dash_html 本身不含 HTML 语法，直接复用于入库清洗（等长替换）。

def sup_unit_exponents_text(text: str | None) -> str:
    """入库清洗：cm-1 → cm⁻¹ Unicode 上标（与 latex_to_text 上标纪律一致，
    WPS/LLM 引用/FTS 纯文本面全链路同形）。幂等：转换后无 '-+数字' 形态；
    出口 HTML 版对 cm⁻¹ 不再二次处理——新旧文档渲染收敛同形。"""
    if not text or "-" not in text:
        return text or ""

    def _repl(m: re.Match) -> str:
        return f"{m.group(1)}\u207b{m.group(2).translate(_SUP_SCRIPTS)}"

    return _RE_UNIT_EXP.sub(_repl, text)


_RE_CLAUSE_NO_TEXT = re.compile(
    r"^(\d{1,2}(?:\.\d{1,2}){0,3})(?=[\u4e00-\u9fff])", re.M)


def space_clause_numbers_text(text: str | None) -> str:
    """入库清洗：段首条款编号补空格（re.M 行首=normalize_wraps 后段首）。
    幂等：加空格后汉字前顾失败。bbox 为独立 PDF 几何，文本加空格不影响
    高亮映射。"""
    if not text:
        return text or ""
    return _RE_CLAUSE_NO_TEXT.sub(lambda m: f"{m.group(1)} ", text)


#: KaTeX 不识别命令 → 等价格式（2026-09-02，需求1 公式"完美还原"）
_KATEX_CMD_MAP = {
    r"\pmb": r"\mathbf",      # bold math（KaTeX 无 \pmb）
    r"\textmu": r"\mu",       # 微
}


def clean_latex_for_katex(latex: str | None) -> str:
    """MinerU OCR 公式 LaTeX → KaTeX 可渲染（2026-09-02，需求1）。

    MinerU 识别的 interline_equation 是逐字符 OCR 产物的 LaTeX，token 间
    有多余空格（'f { = } \\frac { h ^ { 1 . 3 5 } } { A _ { \\textrm { b } } }'）。
    本函数做**结构安全**的紧凑化：只去 token 边界空格（保留 \\ 命令、{}、
    ^_、转义空格 \\ 与 ~），数字串归并，并对少数 KaTeX 不识别的命令做等
    价格式替换（\\pmb→\\mathbf）。不改任何语义 token；幂等（已紧凑零变化）。
    """
    if not latex:
        return latex or ""
    s = latex
    for cmd, repl in _KATEX_CMD_MAP.items():
        s = s.replace(cmd, repl)
    # 1) {}、^、_ 边界空格：{ 1 . 2 5 } → {1.25}、h ^ { → h^{
    s = re.sub(r"\s*([{}^_])\s*", r"\1", s)
    # 2) 数字/点/逗号串归并（循环直到稳定：1 . 2 5 → 1.25、3 0 0 → 300、
    #    1 , 0 → 1,0；保留命令→变量空格，故不动 \Delta t 等）
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"(\d)\s+(\d)", r"\1\2", s)
        s = re.sub(r"(\d)\s+\.", r"\1.", s)
        s = re.sub(r"\.\s+(\d)", r".\1", s)
        s = re.sub(r"(\d)\s*,\s*(\d)", r"\1,\2", s)
    # 3) 关系/运算符号边界（不动字母）：= < > + - × ÷ :
    s = re.sub(r"\s*([=<>+×÷])\s*", r"\1", s)
    s = re.sub(r"\s*:\s*", ":", s)
    # 4) ~ 紧缩；多空格折叠为单空格（保留命令后单空格分隔）
    s = re.sub(r"\s*~{1,2}\s*", "~", s)
    s = re.sub(r"[ \t]{2,}", " ", s).strip()
    return s


#: 面积下标误识别（2026-09-02 C5 上下标）：MinerU 把下标 Aₑ（e）识别成
#: 度符号 A°——当 A° 后接面积量纲（> / 数字 + m²/cm²）判据时，° 必为下标 e
#: （GB 面积符号 Aₑ），非角度。保守：仅'有效散热面积/散热面积'上下文或
#: 后接 面积单位 才转，防误伤角度 A°。
_RE_AREA_SUB = re.compile(
    r"([Aa])\s*°(?![⁰0-9\.])(?=\s*[>＞]\s*\d|[\u4e00-\u9fff]{0,6}面积)")


def normalize_area_subscript(text: str | None) -> str:
    """面积下标纠正（出口 reflow，幂等）：'A ° > 1.25 m²' 的 'A°' 实为下标
    Aₑ（有效散热面积，MinerU 误识别为度符号）→ 归一为 Aₑ。
    保守：'A°' 后接 面积判据（>数值）或 '面积' 上下文才转，防误伤角度/温度
    A°。幂等（转换后无 'A°' 形态）。"""
    if not text or "°" not in text:
        return text or ""
    return _RE_AREA_SUB.sub(lambda m: m.group(1) + "\u2091", text)


#: 水印行判据：**必须有 `www.` 或 `scheme://`**。
#: 不可放宽为裸域名（`[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)+`）——实测会把普通文本
#: `'2.1 较大婴儿'`、`'3.1 婴幼儿谷物辅助食品'` 当成域名（误判 **10025 处**！）。
#: 这是"先做反向对照再放宽"救回来的一次：判据一宽，正常条款被整行删掉。
_RE_WM_URL2 = re.compile(r"(?:https?://)?(?:www\.)[A-Za-z0-9\-]+"
                         r"(?:\.[A-Za-z0-9\-]+)+(?:/[^\s，。；]*)?", re.I)
#: 剥掉 URL 后残留多少算"短装饰"——'网址'/'网址:'/'下载'/'出版' 等标签都很短；
#: 参考文献（`[1] SOAP Version 1.2 …, http://…`）残留很长，据此区分。
_WM_RESIDUE_MAX = 12

#: 无 URL 的**工具水印**签名（2026-09-16 新增，实测来自 `pypdf_backfill` 越界抽取）。
#:
#: 缺陷证据：盗版标准 PDF 常由 Aspose.PDF 生成，页脚带
#:     `Evaluation Only. Created with Aspose.PDF. Copyright 2002-2025 Aspose Pty Ltd.`
#: 该句**不含 `www.`/`://`** → 旧守卫（`"www." not in text and "://" not in text`
#: 直接 return）使整个函数原样返回 → 水印存活。实测库内 **12,614 条**补丁正文含它，
#: 而**原文 0 条**（即由回填越界引入，非 OCR 原产）。
#:
#: 判据收紧到**厂商专名**，不放宽到"含 Copyright/Evaluation"这类通用词——
#: 后者会误删合法正文（如引用他人文档的版权声明）。
#: `Aspose` 是本项目语料的工具专名，作为整体 token 具备足够特异性。
_RE_WM_TOOL = re.compile(
    r"(?:Evaluation\s+Only\.?\s*)?(?:Created\s+with\s+)?Aspose(?:\.PDF)?"
    r"(?:\.\s*Copyright\s+\d{4}\s*-\s*\d{4}\s+Aspose\s+Pty\s+Ltd\.?)?",
    re.I)

#: 全部"行内水印 token"（剥除后残留长度决定整行去留）。新增水印一律入此表，
#: 使 strip_watermark_lines 只有一个判据来源。
#:
#: 第三族·**页眉「页码 + 标准号」**（2026-09-16）：实测 `pypdf_backfill` 越界抽取
#: 把页眉连同工具水印一起吞进补丁正文，形态 `'5 GB/T 10029—2010 Evaluation Only…'`。
#: 只剥工具 token 时残留 `'5 GB/T 10029—2010'`（17 字 > 阈值 12）→ 整行不删 → 水印存活。
#:
#: 判据**精确到标准号前缀族**（GB/GB\///GBZ/DB/JGJ/…），**不放宽为"数字+大写字母"**：
#: 后者会误删合法条款标题（如 `'5.2.3 试验方法'`）；且要求 `\d{3,5}` 三位以上数字，
#: 与条款号（`5.2.3` 这类短段）天然区分。
_WM_STD_CORE = (
    r"(?P<pfx>GB|DB|JGJ|JG|CJJ|CJ|HG|SH|SY|NB|DL|YB|TB|JT|MT|AQ|TSG)"
    r"\s*/?\s*(?P<mid>[A-Z])?\s*(?P<num>\d{3,5}(?:\.\d+)?)"
    r"\s*[—\-–]\s*(?P<year>\d{2,4})")

_RE_WM_HEADER = re.compile(r"^\s*\d{1,4}\s+" + _WM_STD_CORE + r"\s*$", re.I)

#: 文末页眉（**不锚行首**）：单行化正文（`pypdf_backfill` 的 `" ".join(buf)`）会把页眉
#: 拍在长行尾部，此时 `^…$` 的 `_RE_WM_HEADER` 够不着（实测残留
#: `'…执行。 5 GB/T 10029—2010'`）。此判据只吃**行尾**。
#:
#: ⚠ **前导页码是必须的，不是可选的**：本仓库的回归用例抓出过一次放宽事故——
#: 把页码写成可选后，`'应符合 GB/T 10029—2010'`（行尾只是一个标准号引用）被整段删掉。
#: 页眉与"正文标准号引用"的判别特征正是**页码**（`'5 GB/T 10029—2010'` vs
#: `'应符合 GB/T 10029—2010'`）。
#:
#: ⚠⚠ **但"有页码"还不够**（2026-09-17 复核实测）：**表格末格**同样是
#: `<裸数字> <标准号>`（`'…牵条 优质碳素结构钢 20 GB/T699—2015'`），于是被误删。
#: 消歧要靠**上下文**：调用方把该文档**自己的标准号**传进来（`own_standard_no`），
#: 判据就只吃"标准号 == 本文档标准号"的尾巴 —— 页眉永远是**自家**标准号，
#: 而表格里引用的通常是**别的**标准。不传时保持历史行为（见诚实边界注释）。
_RE_WM_HEADER_TAIL = re.compile(r"\s+\d{1,4}\s+" + _WM_STD_CORE + r"\s*$", re.I)

#: 全角 → 半角（U+FF01–U+FF5E → U+0021–U+007E）。标准号在库里可能是全角写法
#: （实测存在 `GB／T 10067.6-2023` 这种**全角斜杠**），故比较前必须抹平。
_FW2HW = {c: c - 0xFEE0 for c in range(0xFF01, 0xFF5F)}


def canon_standard_no(s: str | None) -> str:
    """标准号归一（**仅供比较**，不用于展示）：全角→半角、统一破折号、去空白与斜杠、大写。

    与 `update.channels.base.norm_no` 同口径，额外抹平全角与多种破折号
    （`—` U+2014 / `–` U+2013 / `－` U+FF0D）。
    """
    s = (s or "").translate(_FW2HW)
    for d in ("\u2014", "\u2013", "\uff0d", "\u2500"):
        s = s.replace(d, "-")
    return re.sub(r"[\s/]+", "", s).upper()


def _match_std(m: "re.Match[str]") -> str:
    """从页眉判据的匹配里重建标准号（前缀族 + 可选分册字母 + 号 + 年）。"""
    return canon_standard_no(
        (m.group("pfx") or "") + (m.group("mid") or "")
        + (m.group("num") or "") + "-" + (m.group("year") or ""))


#: 比较键：只取**号 + 年**（丢弃前缀族与 `/T` 分册标记）。
#:
#: ⚠ 为什么不能整串比较（2026-09-17 实测踩到）：同一份标准的**页眉**常把 `GB/T` 印成
#: `GB`（`own='GB／T 12041.1-2010'` vs 页眉 `'1 GB 12041.1—2010'`）—— OCR/排版去掉
#: 了 `/T`。整串比较会把这些**真页眉**判成"别人的标准号"而留下：实测**226 行**会因此
#: 漏删。只比"号 + 年"既能容纳这种写法差异，又仍能把表格里引用的**别的**标准
#: （`GB/T699—2015` vs own `GB/T 12041.1-2010` → 号不同）正确保住。
_RE_STD_KEY = re.compile(r"(\d{3,5}(?:\.\d+)?)\s*-?\s*(\d{2,4})\s*$")


def standard_key(s: str | None) -> str:
    """把标准号压成比较键 `号-年`；压不出来就退回整串归一号（保守）。"""
    c = canon_standard_no(s)
    m = _RE_STD_KEY.search(c)
    return f"{m.group(1)}-{m.group(2)}" if m else c


def segment_for_fts(text: str | None) -> str:
    """FTS 用的**唯一**分词实现：jieba `cut_for_search` + 空格连接。

    为什么集中在这里（2026-09-17）：`clause_fts` 与新建的 `material_fts` 都靠
    "先分词、再交给 `tokenize='ascii'` 的 FTS5"这条口径。**只要出现第二份实现，
    两条检索线早晚会分叉**（分叉了就是"同一句话在法条里搜得到、在材料里搜不到"这种
    最难查的 bug）。故 clause 侧原有的私有 `_seg` 改为委托本函数。

    jieba 首次导入较慢（要建词典），故**函数内延迟导入**——不要提到模块顶层。
    """
    import jieba
    return " ".join(w.strip() for w in jieba.cut_for_search(text or "") if w.strip())


def fts_match_expr(text: str | None) -> str:
    """FTS5 `MATCH` 表达式的**唯一**构造器（2026-09-17 集中到此处）。

    为什么必须只有一个：这是"分词"之后的第二道**检索口径**，两条检索线若各写一份，
    症状是"同一句话在法条里搜得到、在材料里搜不到"——最难查的一类 bug。
    本函数由 `clause_repo`/`hybrid_engine` 侧与 `material_repo` 侧**共用**。

    三条被实测证明必需的规则：
    1. **每个词加引号**：裸 `-` 会被 FTS5 当语法（实测 `'GB 30871-2022'` → 报
       `no such column: 2022`）；`. ` 亦然（实测 `'5.2.3'` → `syntax error near "."`）。
       而这类错误**会被兜底 except 吞成"没有命中"**——静默失效，最坏的一种。
    2. **用 `OR` 连接**：FTS5 的多个词是**隐式 AND**，于是"住宿标准是多少"（材料里只有
       "住宿标准…"）会 0 命中——自然语言提问基本检索不到东西。要召回，排序交给 bm25。
    3. **剥掉非字母数字/非中文的字符**、且**丢弃单字符词**（`的`/`是` 之类纯噪声）。
       ⇒ 已知代价：`'5.2.3'` 这种**整个表达式都是单字符**的查询会得到空串 ⇒ 该查询在
       FTS 上**无命中**（法条侧靠"精确条款号通道"补上，材料侧目前没有对应通道，
       见 `material_repo.search_materials` 的诚实边界）。

    本函数的契约与"与旧法条侧实现逐字等价"的回归都在 `tests/test_answer_materials.py`
    的 `TestFtsMatchExprIsTheSingleOwner` / `TestNaturalLanguageRecall` 里。
    """
    words = segment_for_fts(text).split()
    quoted: list[str] = []
    for w in words:
        safe = re.sub(r"[^\w\u4e00-\u9fff]", " ", w)   # 只留字母数字/下划线/中文
        for tok in safe.split():
            if len(tok) > 1:
                quoted.append(f'"{tok}"')
    return " OR ".join(quoted)


def standard_no_key(value: str | None) -> str:
    """标准号的**比较键**（只用于"是不是同一部标准"的判断，**不是**存储格式）。

    为什么需要它（2026-09-17，Track L 判重）：同一个标准号在库里/在采集侧有**多种写法**——
    实测生产库 `doc_meta.standard_no` 是 **`GB 10146-2015`**（带空格、带连字符），
    而 `knowledge.auto_tag` 抽出来的是 **`GB10146-2015`**（去空格去斜杠）。
    不归一就永远比不上，而"库内到底有没有这部标准"是 Track L 的唯一判据。

    规则（**保守**：只吃掉"肯定等价的差异"）：
    - NFKC（全角 `／`／`－` → 半角）；
    - 大写；
    - **去掉所有空白**；
    - **去掉 `/`**（`GB/T 1234` 与 `GBT1234` 等价）；
    - 各种连字符（`—–‐‑‒―－`）统一成 `-`。

    ⚠ **保留年份与部分号**：`GB 10769-2010` 与 `GB 10769-2025` 是**两部不同的文件**
    （生产库里确实同时存在），`GB 1094.2-2013` 的 `.2` 也是身份的一部分。
    ⇒ **不要**在这里做"取基名"的模糊匹配；要跨版本关联是另一件事（`short_code` 管那个）。

    ⚠ 本函数**不**取代既有的几处就地归一（`pipeline._hier_from_no` 取的是**前缀**、
    `docx_ingest` 的 `short_code` 是**去掉连字符**的另一套语义、`ccs_fetcher._seed_key`
    是给种子表用的）——那些各有各的用途，本函数只服务"相等判断"。
    """
    s = unicodedata.normalize("NFKC", str(value or "")).upper()
    s = re.sub(r"\s+", "", s)
    s = s.replace("/", "")
    return re.sub(r"[‐‑‒–—―－]", "-", s)


def law_name_key(value: str | None) -> str:
    """**法规名**的比较键（只用于"是不是同一部法规"，**不是**存储格式）。

    ⚠ **与 `standard_no_key` 的关键区别：这里保留版本/修正标记**。
    标准靠"号 + 年"区分版本（`GB 10769-2010` vs `-2025`），法规靠**名称里的修正年份**
    （`安全生产法（2021年修正）` vs `（2014年修正）`）。**不能**把括号里的年份去掉：
    那会把"库里有 2014 版"当成"这部法已经有了"，于是**把 2021 修正版指到旧版上**
    ——P1 准确性上最坏的一种后果（引用的法条是过时的）。
    跨版本关联是 `doc_meta.short_code` 的事，不是本函数的事。

    规则（保守）：NFKC（全角→半角）→ 去掉所有空白 → 去掉书名号 `《》` → 统一连字符。
    """
    s = unicodedata.normalize("NFKC", str(value or ""))
    s = re.sub(r"\s+", "", s)
    s = s.replace("《", "").replace("》", "")
    return re.sub(r"[‐‑‒–—―－]", "-", s)


#: "内容不进正文"的标签名（**一个列表，两处正则共用**）。
#: - `script` / `style`：脚本与样式（本函数存在的原本理由）；
#: - `iframe` / `noembed` / `noframes`：**浏览器不渲染其内容**的元素
#:   （2026-09-17 独立复核 b8 的 LOW-5 实测：这一族的内容**全部**进了正文，8/8）。
#:   ⚠ 这三个的判据是"**浏览器真机不显示**"——2026-09-18 复核 b9 用 Edge headless 的
#:   `innerText` 逐条裁过：`iframe`/`noembed`/`noframes` **不显示**（收得对）。
#: - ❌ **`xmp` / `plaintext` 已从这个列表里移出**（2026-09-18，复核 b9 的 MEDIUM-4）：
#:   它们**是可见文字**（`<xmp>` 原样显示其字面文本、`<plaintext>` 之后全部当可见文本），
#:   收掉它们是**删可见正文**——方向与本函数的定位（"页面上看到什么就是正文"）**相反**。
#:   上一轮把它们一起收编，依据的是一句没验证过的注释（"浏览器不渲染其内容"），
#:   真机裁决直接证伪；而且那个收编是**本区间引入**的（修前它们的内容是保留的）。
#: ⚠ **故意保留** `noscript` / `textarea` / `title`（浏览器**不显示**它们，但内容可能是
#:   有用的文字）：我们**不执行 JS**，所以 `<noscript>` 里那套"没有 JS 时的兜底内容"
#:   恰恰是"我们会看到的东西"；`textarea` 是表单默认值、`title` 是页面标题
#:   （采集侧另有标题通道，正文里留着无害）。这两条**判据不同**（一个"浏览器不显示但我们要"
#:   一个"浏览器不显示且不要"），所以在这一段里分开写：**别把两条判据混成一条**
#:   （上一版的注释就是把它们混在一起，才让 `xmp`/`plaintext` 混进来的）。
#:   这些保留是**有意的**，登记在方案 §12 未决第 9 条。
_CONTENT_HIDDEN_TAGS = r"script|style|iframe|noembed|noframes"

#: 开标签。⚠ `(?<!["'])` 挡的是"**属性值里**的字面 `<script>`"（`title='<script>'`）：
#: 那不是标签，当成标签会把其后正文整段吞掉（复核 D② 的第 5 组边角，实测丢"可见"）。
_RE_SCRIPT_STYLE_OPEN = re.compile(
    rf"(?<![\"'])<({_CONTENT_HIDDEN_TAGS})\b(?P<attrs>[^>]*)>", re.IGNORECASE)

#: 结束标签：`</script>` / `</script >` / `</script foo>`（浏览器都接受这种写法）。
_RE_SCRIPT_STYLE_CLOSE_ANY = re.compile(
    rf"</({_CONTENT_HIDDEN_TAGS})\b[^>]*>", re.IGNORECASE)

#: HTML 注释：**必须先剥**（注释里的 `<script>` 不是标签；不剥会吞掉其后正文）。
_RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

#: 标签开头：`<` 后面紧跟字母或 `/`（HTML5：`<` 后面是空白/数字/`=` 等**不是**标签开头）。
_RE_TAG_START = re.compile(r"<[A-Za-z/]")


def _inside_unclosed_tag(s: str, start: int, at: int) -> bool:
    """`s[start:at]` 里是否有一个**未闭合的标签开头**（⇒ `at` 处的 `<` 在标签内部）。

    判据（与 `_strip_script_style` 的 docstring 第 4 条同源）：
    取 `s[start:at]` 里**最后一个** `<`；它必须①紧跟字母或 `/`（像标签开头）、
    ②其后**没有** `>`（标签还没结束）——两条都成立才算"我们在那个标签里面"。
    ⚠ ② 不能省：`<a title="a>b"><script>` 里那个 `<a` 后面有 `>`（哪怕是引号里的），
    这时我们**不在**标签内部，`<script>` 是真的标签（在它旁边少判一次就会漏 JS 进正文）。
    """
    seg = s[start:at]
    lt = seg.rfind("<")
    if lt < 0:
        return False
    return ">" not in seg[lt:] and bool(_RE_TAG_START.match(seg, lt))


def _strip_script_style(html: str) -> str:
    """丢掉 `script`/`style` **及其内容**（含**自闭合**与**未闭合**两种形态）。

    ## 为什么不能用一句 `re.sub(r"<(script|style)\\b[^>]*>.*?</\\1>", " ", s)`
    独立复核实测两种真实页面会出事，且都是**静默**的：
    1. **未闭合** `<script>`：没有闭合标签就**匹配不上** ⇒ JS 源码被当成正文**进了材料**；
    2. 属性里带 `>` 等写法会让它定位偏差，一路吃到**后面第一个** `</script>`。

    ## 三条语义（第二版，2026-09-17 复核 D② 之后）
    1. **先剥 HTML 注释** `<!-- … -->`：注释里的 `<script>` **不是**标签
       （第一版没剥 ⇒ `<!-- <script> -->` 会让我把**其后的正文整段吞掉**，实测丢材料）。
    2. **自闭合按 HTML5 语义**（我们收的是 `text/html`）：`<script … />` 里的 `/` **被忽略**，
       它**不是**自闭合，内容到下一个 `</script>` 为止。第一版按 XHTML 当自闭合 ⇒
       `<script src="a.js"/>var x=1;</script>` 会把 **JS 留在正文里**（复核 LEAK）。
       ⇒ 两种读法**直接冲突**，本函数选 **HTML5**：浏览器就是这么解析的，
       而"页面里看到什么"才是我们要的正文。
       ⚠ 代价（诚实登记）：一份 **XHTML** 风格的页面（`<script src=x/>` 之后紧跟可见正文、
       且**另有**一个 `</script>`）会因此丢掉中间那段正文。这种页面在浏览器里同样什么都
       不显示（`/` 被忽略 ⇒ 那一段是脚本），所以**跟着浏览器走**；要按 XHTML 语义分流，
       得把 Content-Type 传进来（`application/xhtml+xml`），**未做**（登记为待办）。
    3. **结束标签放宽**为 `</(script|style)\\b[^>]*>`：`</script foo>` 这种（浏览器接受的）
       写法第一版认不出 ⇒ 找不到闭合 ⇒ **其后正文被整段吞掉**（复核 OVERKILL）。
    未闭合 ⇒ 其后整段丢弃（HTML5：未闭合的 `<script>` 吞到文档末尾，浏览器不渲染）。

    ⚠ 其余局限（粗，与 `html_to_text` 整体定位一致）：不解析 DOM；**引号内**的
    `>`（`<a title="a>b">`）仍可能让标签边界定位偏差。要更准得引 HTML 解析器（未立项）。

    ## 第 4 条语义（2026-09-17 复核 LOW 顺带实测，v3 加）
    **"还在一个未闭合的标签里"的 `<script>` 不是标签**。复核给的那组
    `<p title=<script> 可见甲</p><p>后</p>`（**无引号**属性值里带字面 `<script>`）
    第一版会把它当标签 ⇒ 其后正文**整段丢掉**（实测只留 `'前<p title='`，丢了"可见甲"与"后"）。
    HTML5 的实际解析是：`<` 在无引号属性值里属于**属性值**（parse error 但继续），
    标签在下一个 `>` 处结束 ⇒ `<p title=<script` 是一个完整标签，**"可见甲"是正文**。
    ⇒ 判据：匹配点之前若有一个 `<` 是**未闭合的标签开头**（后面紧跟字母或 `/`，
    且其后没有 `>`），则我们还在那个标签内部，本次匹配**不是**标签，跳过。
    ⚠ 为什么要求"紧跟字母/`/`"：正文里的裸 `<`（`a < b <script>…`）后面跟的是空格，
    那不是标签开头，**不能**因此把真 `<script>` 当文本——那会把 JS **漏进正文**
    （本函数要防的正是这个方向）。两个方向都实测过，见 §10.40。
    """
    # ① 先剥注释：注释里的 `<script>` 不是标签（不剥会把其后正文全吞掉，实测丢材料）
    s = _RE_HTML_COMMENT.sub(" ", html)
    out: list[str] = []
    pos = 0
    while True:
        m = _RE_SCRIPT_STYLE_OPEN.search(s, pos)
        if m is None:
            out.append(s[pos:])
            return "".join(out)
        # ④ 还在一个**未闭合的标签**里 ⇒ 这次匹配是属性值里的字面文本，不是标签
        #    （见 docstring 第 4 条；跳过一个字符继续找，保证循环终止）
        if _inside_unclosed_tag(s, pos, m.start()):
            out.append(s[pos:m.start() + 1])
            pos = m.start() + 1
            continue
        out.append(s[pos:m.start()])
        # ② 自闭合**不特殊处理**（HTML5：`<script/>` 里的 `/` 被忽略，它不是自闭合）
        close = _RE_SCRIPT_STYLE_CLOSE_ANY.search(s, m.end())
        if close is None:
            # 未闭合 ⇒ 其后全部是脚本文本（HTML5 规则），整段丢掉
            return "".join(out)
        pos = close.end()


def html_to_text(html: str | None, limit: int | None = None) -> str:
    """HTML → 紧凑纯文本（**页面/表格通用**的规范实现）。

    算法：`<eq>` 公式转可读 → 单元格/行转分隔 → **丢 script/style** → 剥标签 → 解实体
    → 折叠空白。

    ⚠ **为什么放到这里**（2026-09-17）：此前同一算法在**三处**各有一份
    （`server._html_to_text`、`ks_answer._html_to_text_compact`、
    `quality.clause_health.clause_health_html_to_text`），而 `clause_health` 的
    docstring 自己就写着"**逐字符等价于** `server.py` 的原 `_html_to_text`"
    —— 那是承认了的重复。采集器需要**页面级**转换（不是小片段、也不是表格），
    与其再写第四份，不如把规范实现放这里。
    **没有**顺手改那三处的调用点（各自 limit 与语义是当场选的，改动面大于收益）——
    登记为待办。

    ⚠ **与 `clause_health_html_to_text` 的关系要精确说**（2026-09-17 独立复核指出：原措辞
    只说了 script/style 一条差异，**不够精确**）。同一 `limit` 下，两者**逐字符等价**，
    **除了两处有意的改进**（各有测试钉住，别当成 bug 改回去）：
      1. **含 `script`/`style` 时**：本函数**丢掉它们的内容**（那三份会把 JS/CSS 当正文）；
      2. **大写的 `</TD>`/`</TR>`**：本函数照样转成表格分隔（那三份的正则只认小写，
         实测 `'<TD>甲</TD><TD>乙</TD>'` → 本函数 `'甲 | 乙'` vs 旧 `'甲乙'`）。
         真实页面两种大小写都有，故这同样是改进。
    除此之外**不要**再引入第三处差异；发现第三处就说明两边开始分叉，必须收口。

    ⚠ **它是粗的**：不解析 DOM、不做正文抽取（readability）、不去导航/页脚样板。
    采集件默认只是**线索**（T3 起），这个精度与那个定位是匹配的；
    要更干净得引入正文抽取库（未立项）。
    """
    if not html:
        return ""
    # ⚠ **顺序是承重的**（2026-09-17 独立复核 b7 的 MEDIUM）：`_strip_script_style`
    # **必须最先**做。它内部的 `_inside_unclosed_tag` 判的是"我是不是还在一个未闭合的
    # 标签里"（看最后一个 `<` 之后有没有 `>`）；而下面那三步
    # （`clean_eq_tags` / `</td>` / `</tr>`）**会把 `>` 删掉** ⇒ 若先做它们，
    # 原串里**已经闭合**的 `<b` / `<div` 会变成"未闭合的标签开头"，守卫误判 ⇒
    # **JS 反而漏进正文**（复核实测 7 组，例：`<td>a<b</td><script>JS</script>` → `'aJS'`）。
    # 先剥 script/style 就没有这个窗口：守卫看到的是**原始**字符串。
    t = _strip_script_style(html)
    t = clean_eq_tags(t)
    t = re.sub(r"</t[dh]>", " | ", t, flags=re.IGNORECASE)
    t = re.sub(r"</tr>", "\n", t, flags=re.IGNORECASE)
    # ① 整体丢掉**内容不该进正文**的两类标签（含其内容）：script/style。
    # 不做这一步的话，页面里的 JS/CSS 会被当成正文塞进材料（采集最脏的来源）。
    # ⚠ 用 `_strip_script_style` 而**不是**一句正则：自闭合/未闭合两种形态会让
    # 那句正则**静默**吃掉可见正文或漏掉 JS（见那个函数的 docstring）。
    t = re.sub(r"<[^>]+>", "", t)
    t = html_unescape(t)
    t = re.sub(r"[ \t\u3000]+", " ", t)
    t = re.sub(r"(?m) \| +$", "", t)
    t = re.sub(r"\n{2,}", "\n", t).strip()
    return t if limit is None else t[:limit]


#: 二进制容器在"文本"里的开头签名（采集侧唯一能拿到的线索，见 `looks_like_binary`）。
#:
#: ⚠ **哪些在文本路径上真的可达**（2026-09-17 独立复核指出原叙述会制造假信心，
#: 第二轮复核又指出清单**少列了三个**——按复核的实测，可达的是**七个**）：
#: 只有**纯 ASCII** 的那些能在 `resp.text`（`errors='replace'` 解出来的 str）里原样出现：
#: `%PDF-` / `%!PS` / `PK\x03\x04` / `Rar!\x1a` / `GIF87a` / `GIF89a` / `\x7fELF`
#: （ELF 的头是 ASCII 的 DEL + "ELF"，`\x7f` 在 UTF-8 里合法）。
#: 而 `\x89PNG`、`\xff\xd8\xff`（JPEG）、`\xd0\xcf\x11\xe0`（OLE2）这些**非 UTF-8 首字节**
#: 在真实传输路径上早被替换成 U+FFFD，**永远命中不了**——它们只对**真实字节**有意义
#: （见 `looks_like_binary_bytes`）。保留在同一个元组里是为了让"字节判据"复用一份签名表
#: （**一个所有者**）。
_BINARY_HEADS = (
    "%PDF-", "%!PS", "PK\x03\x04", "Rar!\x1a",
    "\x89PNG", "GIF87a", "GIF89a", "\xff\xd8\xff", "\x7fELF", "\xd0\xcf\x11\xe0",
)

#: 上面那张表的**字节**形态（字节级 magic 用；顺序与内容一一对应）。
_BINARY_HEADS_BYTES = tuple(h.encode("latin-1") for h in _BINARY_HEADS)


def looks_like_binary(text: str | None) -> bool:
    """这段"文本"其实是**二进制容器**吗？（**文本入口**用；字节入口见下一个函数）

    ## 为什么需要这个判据（2026-09-17，采集器接线时实测踩到）
    传输层（`update.channels.base.fetch`）把响应统一收敛成 `str`（先试 `resp.json()`，
    失败取 `resp.text`）。采集的**登记门**（`collect_text`）拿到的是 `str`，所以那里
    只能按文本判。不判的后果实测是：`%PDF-1.7 …`（PDF 的 ASCII 头 + 解出来的乱码）
    会被 `html_to_text` 原样当成正文，登记成一条"**看起来有内容、其实一个字都读不了**"
    的材料 —— 比空材料**更坏**：空材料一眼看得出有问题，这个要等分析时才发现。

    ## 判据（窄）
    1. 去掉前导空白后以 `_BINARY_HEADS` 里的签名开头；或
    2. 前 4096 字符里含 `NUL`（`\\x00`）—— 正常正文不会有。

    ## 诚实边界（这一节是独立复核 2026-09-17 逼出来的，别再写成"零误伤"）
    - **文本路径上真正有效的只有两条**：ASCII 签名（`%PDF-`/`%!PS`/`PK\\x03\\x04`/`Rar!`）
      与 NUL 规则。`\\x89PNG`/JPEG/ELF/OLE2 那几条在 `str` 上**基本不可能命中**
      （非 UTF-8 首字节已被替换成 U+FFFD）——它们由 `looks_like_binary_bytes` 在
      **真实字节**上兑现（采集器现在两条都走）。
    - **会误伤**（实测，不再声称"零误伤"）：以 `%PDF-` 开头的**讲解文**、
      `%!PS` 的 **PostScript 源码**（纯 ASCII 文本）、前 4096 字符含 NUL 的 **CSV**，
      都会被判成二进制而**被采集门拒收**（= 丢材料）。取舍是：采集路径上"把二进制当正文"
      的后果（脏材料进评审队列）比"拒掉几篇讲 PDF 格式的文章"更坏，所以宁可漏/宁可误伤，
      并把这些情形**写出来**而不是假装没有。
    - 只认**开头**；认不出**没有签名**的二进制；完整判断要 magic 库（未立项）。
    - **不要**拿它去清洗已入库正文：那里的文本不是"刚抓回来的响应"。
    """
    s = (text or "").lstrip()
    if not s:
        return False
    if s.startswith(_BINARY_HEADS):
        return True
    return "\x00" in s[:4096]


def looks_like_binary_bytes(data: bytes | None) -> bool:
    """**真实字节**是不是二进制容器（采集器在拿到 `resp.content` 时用这个）。

    与 `looks_like_binary` 是**同一份签名表**（`_BINARY_HEADS`）的两个入口：
    文本入口只能认 ASCII 签名 + NUL，字节入口才能真正兑现 PNG/JPEG/ELF/OLE2 那几条。
    分开的原因见 `looks_like_binary` 的诚实边界——**合并成一个函数会让"文本路径上
    永远命中不了的分支"看起来像在工作**（那正是复核报的假信心）。

    ⚠ 同样的局限：只看开头；无签名的二进制认不出。
    """
    if not data:
        return False
    head = data[:64].lstrip()
    if head.startswith(_BINARY_HEADS_BYTES):
        return True
    return b"\x00" in data[:4096]



#: 「副本后缀」：浏览器/资源管理器重复下载产生的 `xxx(1).pdf` / `xxx（2）.pdf`。
#:
#: ⚠ **只吃结尾**的 `(数字)`（半角/全角括号都算），**不吃中间的**——库内大量**合法**
#: 括号名（`聚丙烯(PP)树脂`、`湿式(非金属)摩擦材料`、`额定电压1kV(Um=1.2kV)…`）
#: 必须原样保留。实测（2026-09-17 生产库）`:264` 行 `standard_name` 含括号，
#: 其中**结尾是 `(数字)`** 的 :139 行才是副本后缀（数字随灌库在涨）。
_RE_DUP_SUFFIX = re.compile(r"\s*[（(]\s*\d{1,3}\s*[)）]\s*$")


def strip_duplicate_suffix(name: str | None) -> str:
    """去掉名称**结尾**的副本后缀 `(1)`/`（2）`（只动结尾，中间的合法括号不动）。

    ⚠ **要反复剥，不能只剥一次**（2026-09-17 回填时被自己的写后复验抓到）：库内真实存在
    **双重后缀** `…测定法(1)(1)`。`re.sub` 一趟只吃掉一个（锚定 `$` 的匹配在引擎扫过之后
    就不再回头），所以只剥一次会留下 `…测定法(1)`——5 行就是这样漏网的。
    循环剥到稳定为止（每轮长度严格减小，必然终止）。
    """
    s = name or ""
    while True:
        nxt = _RE_DUP_SUFFIX.sub("", s).strip()
        if nxt == s:
            return s
        s = nxt


def clean_standard_name(raw: str | None, *, standard_no: str | None = None) -> str:
    """文件名（或原始串）→ **干净的标准名称**（展示用，不改内容）。

    做三件事，顺序固定：
      1. 全角斜杠 `／` → ASCII `/`、压缩连续空白；
      2. 去掉**结尾**的副本后缀（`…(1)`）；
      3. 若给了 `standard_no`：把**开头**那个标准号前缀去掉（`GB／T 10058-2023 电梯技术条件`
         → `电梯技术条件`）。

    为什么要有这个函数（2026-09-17 前置清理）：库内 :139 行 `standard_name` 是
    `电梯技术条件(1)` 这种形态，而它**不是**从内容里读出来的——是入库时**从文件名派生**的，
    且各个调用方各派生各的（`write_queue_bootstrap` 直接 `name = path.stem`；
    `scripts/_stdparse.derive_standard` 先清理、下一行又用**原始 stem** 覆盖回去；
    `std_bulk_import` 用 manifest 里的 `name`）。⇒ 修数据前先把**派生**归一，否则灌一次库又脏一次。

    **关于第 3 步的容错**：库内真实文件名常是全角斜杠（`GB／T 10058-2023 电梯技术条件(1).pdf`），
    而 `standard_no` 已归一成 ASCII `/`，直接 `stem.replace(std_no, "")` **永远匹配不上**
    （这正是 `_stdparse` 那个 bug 的成因）。这里改为按**号 + 年**匹配前缀，容忍前缀族差异
    （`GB` vs `GB/T` vs `GBZ`）与各类破折号，且**只剥开头**。

    结果为空时**回退**到"只去了副本后缀"的串——绝不返回空名（调用方常拿它当展示名）。
    """
    s = (raw or "").replace("／", "/")
    s = re.sub(r"\s+", " ", s).strip()
    s = strip_duplicate_suffix(s)
    if standard_no:
        # ⚠ 不能复用 `_RE_STD_KEY`：它要求号是 **3~5 位**（那是为"从页眉里抽比较键"设计的），
        # 而真实标准号有 1~2 位的（`GBZ 1-2010`、`GB/T 1.1-2020`）——用它会让这些标准号
        # **永远剥不掉**（2026-09-17 自检实测：`GBZ 1-2010 工业企业设计卫生标准` 原样返回）。
        # 这里单独用一个**宽松**的号+年判据。
        m = re.search(r"(\d{1,5}(?:\.\d+)*)\s*[-–—－]\s*(\d{4})",
                      canon_standard_no(standard_no))
        if m:
            num, year = m.group(1), m.group(2)
            # 前缀族随便（GB/GBT/GBZ/DB11/T…）+ 号 + 破折号 + 年，只要求出现在**开头**
            rx = re.compile(
                r"^\s*[A-Za-z]{0,8}\s*(?:[/\s]\s*[A-Za-z]{0,2}\s*)*"
                + re.escape(num) + r"\s*[-–—－]\s*" + re.escape(year) + r"\s*[-–—－:：]?\s*",
                re.I)
            s = rx.sub("", s, count=1).strip(" -_‐—－:：")
    return s or strip_duplicate_suffix((raw or "").replace("／", "/"))


def _match_key(m: "re.Match[str]") -> str:
    return standard_key((m.group("pfx") or "") + (m.group("mid") or "")
                    + (m.group("num") or "") + "-" + (m.group("year") or ""))


def _std_matches(m: "re.Match[str] | None", own_key: str | None) -> bool:
    """该匹配是否可视为页眉。`own_key=None` → 不设限（历史行为）。"""
    if m is None:
        return False
    if own_key is None:
        return True
    return _match_key(m) == own_key


def _sub_own_header(rx: "re.Pattern[str]", text: str, own_key: str) -> str:
    """只删"号 + 年 == 自家标准号"的行尾页眉，其余原样保留。"""
    def repl(m: "re.Match[str]") -> str:
        return "" if _match_key(m) == own_key else m.group(0)
    return rx.sub(repl, text)


_WM_TOKENS = (_RE_WM_URL2, _RE_WM_TOOL, _RE_WM_HEADER)


def _strip_wm_tokens(s: str) -> str:
    """剥掉一行里的全部水印 token，返回残留。

    **迭代**（而非单遍）：token 互相咬尾——剥掉工具水印后剩下的 `'5 GB/T 10029—2010 '`
    只有在**去掉尾随空白**后才被页眉判据认出（实测单遍残留 17 字 > 阈值 12 → 漏网；
    迭代后为 0）。上限 4 轮且要求每轮都变短，保证终止且绝不误删。
    """
    cur = s
    for _ in range(4):
        nxt = cur
        for rx in _WM_TOKENS:
            nxt = rx.sub("", nxt)
        nxt = nxt.strip(" 　:：-—,.，。;；[]()（）")
        if len(nxt) >= len(cur):
            break            # 不再变短 → 停（防死循环/防抖）
        cur = nxt
    return cur


def strip_watermark_lines(text: str | None, *,
                          own_standard_no: str | None = None) -> str:
    """站点水印行剥离（幂等）：整行删掉，正文行一字不动。

    `own_standard_no`（2026-09-17 新增，**可选**）：该文本所属文档**自己的标准号**。
    传入后，"页码 + 标准号"这一族判据只吃**标准号与之相符**的页眉 —— 页眉永远是自家
    标准号，而**表格末格**里引用的是别人的标准。
    不传时保持历史行为（可能误删表格末格）。

    ⚠ **诚实边界**：不传 `own_standard_no` 时，本函数**无法**区分"行尾页眉"与
    "表格末格" —— 两者都是 `<裸数字> <标准号>`。保留历史行为是为了不改变既有调用方
    的输出；**知道文档标准号的调用方都应当传**（`pipeline.build_clause_models` 与
    `repair_patch_watermarks.py` 已传）。

    **缺陷证据**（2026-09-15 新语料实测，38/231 部 = 16% 命中）：VLM 把盗版标准站
    的页眉水印读进条款正文，污染内容：
        '网址 www.spc.net.cn'（23 处）、'http://www.bzcbs.com'、
        '龙牛网 www.longniu.com 下载'、'网址: www.spc.net.cn'
    形态分两族：**裸 URL 独占一行**（http://www.spc.net.cn）与**短标签+URL**
    （'网址 www…'）。两者剥掉 URL 后残留都极短。

    **反向对照（必须存活）**——判据靠"剥掉 URL 后的残留长度"区分水印与引用：
        '本附录使用 SOAP 1.2 规范…命名空间为 http://www.w3.org/2003/05/soap-envelope'
        '[1] SOAP Version 1.2 Part 1: Messaging Framework, http://www.w3.org/TR/soap12/'
        '[13] 2011年和2012年中国区域电网平均二氧化碳排放因子.http://www.ccchina.org.cn/…'
        '[4] 卡内基梅隆大学软件工程研究所《CMMI 开发模型 2.0 版》, 2018, www.sei.cmu.edu/cmmi.'
        这些残留都是实质文字 → 一律保留。

    另：已有 `strip_block_noise` 只处理"整行即水印（URL±页码±点线）"且**未被内容
    清洗链调用**；本函数是它在正文清洗链里的对应实现（整行删除语义），
    判据更宽（含短标签族与**无 URL 的工具水印族**），故作为单一所有者独立存在。
    """
    if not text:
        return text or ""
    own_canon = standard_key(own_standard_no) if own_standard_no else None
    # 早退守卫：**四类形态一个都不匹配**才不必处理。逐次修补的教训（每次都漏一族）：
    #   只判 URL → 无 URL 的工具水印整族漏网；
    #   加工具水印后 → "已被拍进行尾的页眉"仍漏（既无 URL 也无 Aspose）；
    #   再加行尾页眉后 → **整行即页眉**（`'5 GB/T 10029—2010'`）又漏
    #   ——它不匹配需要 `\s+` 前缀的 `_RE_WM_HEADER_TAIL`（回归用例抓出）。
    # 故守卫改为"把 text 当成一条**独立页眉**也试一次"。
    if ("www." not in text.lower() and "://" not in text
            and not _RE_WM_TOOL.search(text)
            and not _std_matches(_RE_WM_HEADER_TAIL.search(text), own_canon)
            and not _std_matches(_RE_WM_HEADER.match(text.strip()), own_canon)):
        return text
    # ① **行内 token 剥离**（不依赖换行）：工具水印/页眉常被拍进长行中间——
    #    `pypdf_backfill` 用 `" ".join(buf)` 把整段合成**单行**，水印不在自己行上，
    #    故"整行删除"判据够不着（实测：只加行级判据时全库清理数为 0）。
    #    工具水印是厂商专名，作为整体 token 直接删除是安全的（无合法正文会包含
    #    `Aspose` + 版权年份串）。
    stripped = _RE_WM_TOOL.sub("", text)
    out: list[str] = []
    for ln in stripped.split("\n"):
        s = ln.strip()
        # **(a) 整行就是一个页眉**（`'5 GB/T 10029—2010'`）：直接删。
        #     传了 own_standard_no 时只删"自家标准号"那一族（别的标准号可能只是
        #     表格里独立成行的一格数据）。
        if s and _std_matches(_RE_WM_HEADER.match(s), own_canon):
            continue
        if s and any(rx.search(s) for rx in _WM_TOKENS):
            residue = _strip_wm_tokens(s)
            # 整行删除的两种情形：
            #  ① 残留是"短装饰"（旧口径：'网址'/'下载'/空）；
            #  ② 残留**本身就是页眉**（`'5 GB/T 10029—2010'`）——仅当本行另有水印 token
            #     时才可能走到这里，故不会误删一条独立的合法正文行。
            if (len(residue) <= _WM_RESIDUE_MAX
                    or _std_matches(_RE_WM_HEADER.match(residue), own_canon)):
                continue                      # 整行删除（水印）
        out.append(ln)
    # ② 收尾：行级剥离在单行文本上留下**行尾页眉**（`'…执行。 5 GB/T 10029—2010'`）。
    #    用不锚行首的 _RE_WM_HEADER_TAIL 收口（只吃行尾 + 前置空白，
    #    故正文中的 `'按 GB/T 18654.1 的规定执行。'` 不受影响）。
    res = "\n".join(out).rstrip()
    if own_canon is None:
        res = _RE_WM_HEADER_TAIL.sub("", res)
        res = _RE_WM_HEADER.sub("", res)
    else:
        # 只收"自家标准号"的行尾页眉 —— 表格末格里引用的**别的**标准号必须留下
        res = _sub_own_header(_RE_WM_HEADER_TAIL, res, own_canon)
        res = _sub_own_header(_RE_WM_HEADER, res, own_canon)
    # ⚠ **不要**再补一条"收掉孤立尾部页码"的规则：正文以数字结尾很常见
    #   （`'见图 5'`/`'应符合 4.2'`），收掉就是误删合法内容。
    #   代价是页眉被剥后可能残留一个孤立页码（`'…执行。 5 '`）——**有意接受**，
    #   与"误删正文"相比这是更轻的缺陷（宁缺不高灭）。
    return res.rstrip()


def clean_clause_text(text: str | None, *,
                      legend_stripper=None,
                      own_standard_no: str | None = None) -> str:
    """**入库文本清洗链的唯一所有者**（次序即契约，2026-09-15 立）。

    为什么要有它：这条链原先是 `pipeline.py` 入库处的一行嵌套调用，于是
    「谁清洗了条款正文」只存在于那个调用点。后果在自进化循环里暴露成结构性
    缺陷——`evolve.evaluate_doc` 直接对 **VLM 产物原文**跑判据（见该函数），
    从不经过清洗链，导致：

    - 清洗器修好的类，判据照旧报（判据 → 越报越假，头部类永远"达线"）；
    - 留出集判定的是"识别层原文有没有瑕疵"，而不是"管线输出有没有瑕疵"，
      于是**修复永远无法被验证通过**（实测：dot-leader 留出集基线 1 → 修复后 1）。

    抽成单一所有者后，入库（`pipeline._content_html` 路径）与评估
    （`evolve.evaluate_doc`）取同一次序——判据看的就是入库后文本，口径不再错位。

    `legend_stripper`（图例段切除）与条款**切分**耦合，住在
    `pipeline.strip_figure_legend_segment`；此处以参数注入，避免 text_utils
    反向依赖 ingestion 层。缺省不跑该步（纯文本消费者无需切分语义）。

    `own_standard_no`（2026-09-17 新增）：本文档自己的标准号，透传给
    `strip_watermark_lines` 用于消解"行尾页眉 vs 表格末格"的歧义。**入库调用方应当传**
    （`pipeline.build_clause_models` 已传）。
    """
    if not text:
        return text or ""
    out = space_clause_numbers_text(
        sup_unit_exponents_text(normalize_label_comma(
            strip_formula_leader(normalize_pua_separators(text)))))
    if legend_stripper is not None:
        out = legend_stripper(out)
    # 站点水印行最后剥（放在图例切除之后：两者都是"整行/整段删除"语义，
    # 但水印行可能落在图例段内，先切图例再剥水印更彻底）
    return strip_watermark_lines(out, own_standard_no=own_standard_no)
