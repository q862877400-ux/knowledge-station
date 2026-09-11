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


def latex_to_text(latex: str) -> str:
    r"""MinerU <eq> LaTeX → 可读文本。
    例：'h _ { \mathrm { ~ w ~ } } / \mathrm { m }' → 'hw/m'

    2026-09-01 保真修复（GB/T 24276 24 条独立公式逐条实测）：
    ① 包裹命令扩容（\pmb/\bf/\mathbb/\textrm/…）并支持一层嵌套
       （\mathrm{\textmu} 此前剥不动）；
    ② 符号替换改词边界单遍正则——\pmb 不再被 \pm 前缀误吃成 '±b'；
    ③ 下标/上标组内容先过符号映射+剥命令再 translate——\circ/\textmu
       不再被逐字下标化残留 '\ₜₑₓₜₘᵤ'；
    ④ '\ '（LaTeX 显式空格）转空格，不再残留 '\ '。
    """
    t = latex
    # 1) 剥命令包裹：\mathrm{...} 等取其内容（支持一层嵌套，迭代处理）
    for _ in range(3):
        t2 = re.sub(
            r"\\(?:mathrm|text|textrm|mathbf|mathit|mathbb|mathsf|mathtt"
            r"|pmb|bf|boldsymbol)\s*\{((?:[^{}]|\{[^{}]*\})*)\}",
            r"\1", t)
        if t2 == t:
            break
        t = t2

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
    return re.sub(r"\s+", " ", t).strip()


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


def table_html_to_pipe(table_html: str) -> str:
    """<table> html → 管道行文本（与前端 table_md 同源格式），单元格已解码实体。"""
    rows: list[str] = []
    for tr in re.findall(r"<tr>(.*?)</tr>", table_html or "", re.S):
        cells = [strip_tags(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


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
