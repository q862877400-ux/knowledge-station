"""T05 管线测试：切分/分型/边/坐标翻转（合成 fixture）+ 真实 middle.json 集成。"""
import json
from pathlib import Path

import pytest

from src.core.ingestion.pipeline import (
    MidItem, build_clause_models, load_middle_items, resolve_edges,
    split_items_into_clauses,
)
from src.core.knowledge.classifier import classify_clause, normalize_clause_number

#: 判据四的**真乱码夹具**（形状：汉字被整体映射成 ASCII 印刷区字符；
#: 出自 GB/T 35210.1-2023 的用户实测报障，见各测试的 docstring）。
#:
#: ⚠ **提到模块级是为了让"阈值锚点"测试与既有测试共用同一批字面量**。
#: 2026-09-25 复核实测教训：锚点测试里我另写了一份"乱码样本"（取模现造的那条），
#: 于是它量到的 s2 上界是 **0.3808**，而**仓里真正在用的两条夹具**上界是 **0.4143**
#: —— 锚点因此比真实约束松，正好授权了一个"三条新测试全绿、而判据四对真乱码失效"
#: 的阈值组合（复核的变异 D）。**夹具一旦分两份，锚点就会锚在错的地方。**
GARBLED_ASCII_396 = (
    "34.567.589.:;) a)*<\"*!'=>yz+a>?k@>GA)!!\"!#!\"#$%,$\"#%#! www.bzfxw.com"
    "%!!$!!WXtuYZ[PM?s¯BCWXDE¨[PµF]GH(IJKnM?01+sWXµD] 2Ln 3 M C)W X t u Y Z "
    "[ P$\\ [ ] v . 0 1 b c N E n Ä O+m ? U V 1 - ] 1)-.$/#%\"!* P¯¶QRST("
    "<WXtuYZ[P$\\[]v.ghnej+UVlmpW)%%%k!lm'STUV1)%%%k\"lm' ]1)-.$/#%\"!*,!"
    "%\"*!'yzMXwÜ%+YZ[denh(\\]/^/JKn _+YZ[P M?nE`æç-Mabcdyef)fgæçnhi+RSb?"
    "M?vjn[P]?tu¯W Xkln [P]+mn<©Mn[P]+¥3MCtu[PJKo[PVp [P]qf?¡¢[P]"
)
GARBLED_ASCII_270 = (
    "34.567.589.:;) a)*<\"*!'=>yz+a>?k@>GA)!!\"!#!\"#$%,$\"#%#! www.bzfxw.com"
    "%!!$!!WXtuYZ[PM?s\u00afBCWXDE\u00a8[P\u00b5F]GH(IJKnM?01+sWX\u00b5D] 2Ln 3 M C)W X t u Y Z "
    "[ P$\\ [ ] v . 0 1 b c N E n \u00c4 O+m ? U V 1 - ] 1)-.$/#%\"!* P\u00af\u00b6QRST("
    "<WXtuYZ[P$\\[]v.ghnej+UVlmpW)%%%k!lm'STUV1)%%%k\"lm' ]1)-.$/#%\"!*,!"
)
#: cid 乱码第三形态（拉丁扩展 + 泰米尔 + 超长同字跑），由**判据三**抓。
GARBLED_CID = (
    "www.bzfxw.com / 㼬 ௿ / ಆ૆㠯ఠ ಆććććććććććććććććććććććććć / "
    "ಇ૆㻰㠯ᕓᑁ⩔᪳Т ಆćććććććććććććććććććććććć"
)


def _mk_middle(tmp_path: Path) -> Path:
    """合成一份 2 页 middle.json：封面/前言 + 2 条款(跨页拼接) + 但书 + 表绑定 + 附录。"""
    mj = {
        "pdf_info": [
            {"page_idx": 0, "page_size": [595, 841],
             "para_blocks": [
                 {"type": "text", "bbox": [60, 700, 500, 740], "lines": [
                     {"spans": [{"type": "text", "content": "前  言"}]}]},
                 {"type": "text", "bbox": [60, 600, 500, 660], "lines": [
                     {"spans": [{"type": "text", "content": "本标准代替 GB 30871-2014。"}]}]},
             ],
             "discarded_blocks": [
                 {"type": "header", "bbox": [200, 20, 400, 40], "lines": [
                     {"spans": [{"type": "text", "content": "GB 30871—2022"}]}]}]},
            {"page_idx": 1, "page_size": [595, 841],
             "para_blocks": [
                 {"type": "text", "bbox": [60, 700, 530, 740], "lines": [
                     {"spans": [{"type": "text",
                                 "content": "5.2.1 动火作业应有专人监护，作业前应清除易燃物品。"}]}]},
                 {"type": "text", "bbox": [60, 650, 530, 690], "lines": [
                     {"spans": [{"type": "text",
                                 "content": "但节假日或夜间作业除外，应升级管理。"}]}]},
                 {"type": "table", "bbox": [60, 400, 530, 600], "blocks": [
                     {"type": "table_caption", "lines": [
                         {"spans": [{"type": "text", "content": "表 5.2.1 动火分级"}]}]},
                     {"type": "table_body", "lines": [
                         {"spans": [{"type": "table", "html": "<table><tr><td>级别</td></tr></table>"}]}]},
                 ]},
                 {"type": "text", "bbox": [60, 300, 530, 340], "lines": [
                     {"spans": [{"type": "text",
                                 "content": "5.2.2 动火分析合格标准：可燃气体浓度不大于 0.5%。"}]}]},
             ],
             "discarded_blocks": [
                 {"type": "page_number", "bbox": [280, 800, 320, 820], "lines": [
                     {"spans": [{"type": "text", "content": "2"}]}]}]},
        ]
    }
    p = tmp_path / "fake_middle.json"
    p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")
    return p


def test_load_middle_items_drops_discarded(tmp_path):
    items, page_sizes = load_middle_items(_mk_middle(tmp_path))
    assert page_sizes[0] == (595.0, 841.0)
    texts = " ".join(i.text for i in items)
    assert "GB 30871—2022" not in texts, "页眉应被丢弃（R65/E4）"
    assert "动火作业" in texts
    kinds = [i.kind for i in items]
    assert "table" in kinds


def test_split_clauses_and_table_binding(tmp_path):
    items, page_sizes = load_middle_items(_mk_middle(tmp_path))
    clauses = split_items_into_clauses(items)
    numbers = [c.number for c in clauses]
    assert "5.2.1" in numbers and "5.2.2" in numbers
    c521 = next(c for c in clauses if c.number == "5.2.1")
    assert "但节假日" in "\n".join(c521.texts), "但书应拼接到母条款（E4 跨块合并）"
    assert c521.table_html and "<table>" in c521.table_html, "表 5.2.1 应绑定母条款（E5）"
    assert c521.table_summary == "动火分级"
    preface = [c for c in clauses if c.number.startswith("前置")]
    assert preface, "前言应成为前置说明"


def test_split_rejects_table_value_clause_heads():
    """E8 表格数值防误判（2026-08-28 生产实测）：成分表数据行不得切成 0.x/伪章号条款。

    化学分析类标准（GB/T 3260.x/3286.x/5009.x 等）的大表被 MinerU 切成文本行后，
    行首单元格值（0.10 / 0.0001 / 1103.11 / "4.2 1.5 3.0"）曾满足 _CLAUSE_GB
    门槛 → 每行一个假条款（41% 新产出文档中招）。E8 闸门：章号首段∈1..60
    且号码后不紧跟 ≥2 个独立数字（表格行特征）。
    """
    items = [
        MidItem(kind="text", text="4.1 化学成分应符合表 1 的规定", page_idx=0),
        MidItem(kind="text", text=(
            "0.10 0.030 0.002 余量\n"
            "0.15 0.040 0.003 余量\n"
            "0.0001 0.001\n"
            "4.2 1.5 3.0 0.25\n"
            "1103.11 抗拉强度\n"), page_idx=0),
        MidItem(kind="text", text="5.2.1 动火作业应专人监护", page_idx=1),
    ]
    clauses = split_items_into_clauses(items)
    numbers = [c.number for c in clauses]
    assert "4.1" in numbers and "5.2.1" in numbers
    assert not any(n.startswith("0.") or n == "1103.11" or n == "4.2"
                   for n in numbers), numbers
    # 表格行应并入母条款 4.1，内容不丢
    blob = "\n".join("\n".join(c.texts) for c in clauses)
    assert "0.030" in blob and "1103.11" in blob and "抗拉强度" in blob


def test_pua_detector_catches_cid_garbage_without_pua_glyphs():
    """E9 cid 乱码变体（2026-08-28 GB/T 20529.2-2010 实测）：文本层不含
    犌犅犜/数字错位特征，而是拉丁扩展+泰米尔+生僻字 + 超长同字符跑，
    也必须判乱码转 OCR，否则 0 条款入库。"""
    from src.core.ingestion.mineru_adapter import text_layer_pua_mangled

    assert text_layer_pua_mangled([{"text": GARBLED_CID}] * 3), "cid 乱码必须被判中"
    # 正常中文不得误伤
    normal = "4.1 化学成分应符合表 1 的规定。表 1 中的数值……\n4.2 抗拉强度不小于 1103 N/mm²。"
    assert not text_layer_pua_mangled([{"text": normal}]), "正常文本不得误判"


def test_pua_detector_catches_ascii_mapped_garbage():
    """E9b 判据四：cid 错位第四形态——汉字被映射为 ASCII（GB/T 35210.1-2023
    用户实测报障），无怪区字符、无非 ASCII 长跑、条款号首段合法，
    仅能靠「中文标准正文无汉字」捕获。"""
    from src.core.ingestion.mineru_adapter import text_layer_pua_mangled

    garbage = GARBLED_ASCII_396
    assert len(garbage) >= 200
    assert text_layer_pua_mangled([{"text": garbage}]) is True
    # 正常中文条款不受影响
    normal = "4.1 化学成分应符合表 1 的规定。表 1 中的数值对热轧（锻造）钢材按 GB/T 223 的规定。"
    assert text_layer_pua_mangled([{"text": normal}]) is False


class TestNonChineseTextIsNotMangled:
    """**非中文文档不许被判成 PUA 乱码**（2026-09-25 修 P0.11）。

    起因（实测）：`2023_Query2doc.pdf`（arXiv 英文论文）`_extract_text_blocks` 抽出
    **181 个块、文字干净**，却被判 `pua_mangled` ⇒ `blocks=[]`；
    而材料入库默认 `deep_fallback=False`（深通道云优先、会外发）⇒ 无人救 ⇒ **整份材料 0 字**。
    根因是判据四「CJK 占比 <5% ⇒ 乱码」——它按"中文国标"写的，**对任何非中文文档都成立**。

    修法：判据四叠加"**这不像真拉丁文本**"（两个量，阈值 0.70 由实测选定；
    对照表见 `var/tmp/probe-pua-discriminator.py`）。本类把**两个方向**都钉住：
    真英文不许误伤、真乱码仍须判中（后者由上面两个既有测试覆盖，这里再各放一条）。
    """

    #: 一段**真英文论文体**文字（≥200 字，判据四才会生效）。
    #: 不是抄某篇的具体段落，而是按论文常见行文写的，含公式符号/引用/括号。
    _EN = (
        "Retrieval-augmented generation has become a standard approach for knowledge-intensive "
        "tasks. Given a query q, the retriever selects a set of passages from a corpus D, and the "
        "generator conditions on both. Prior work reports consistent gains on open-domain QA "
        "(e.g., Natural Questions, TriviaQA), while recent studies question whether those gains "
        "reflect genuine retrieval ability or parametric knowledge already encoded in the model. "
        "We therefore measure recall at k for k in {1, 5, 20}, together with mean reciprocal "
        "rank, and we report the fraction of queries whose gold passage is absent from the index. "
        "Our results indicate that a dense bi-encoder degrades as the index grows, whereas sparse "
        "lexical matching remains comparatively stable, which motivates hybrid fusion."
    )

    def test_english_paper_text_is_not_mangled(self):
        from src.core.ingestion.mineru_adapter import text_layer_pua_mangled
        assert len(self._EN) >= 200, "前提：样本必须 ≥200 字，否则判据四不生效"
        assert text_layer_pua_mangled([{"text": self._EN}]) is False, (
            "真英文文档被判成 PUA 乱码 —— 会把整份材料挡在库外（P0.11 复发）")

    def test_garbled_ascii_mapped_chinese_is_still_mangled(self):
        """对照：**原来的真乱码案例仍须判中**（别为了修误伤把这条判据废掉）。"""
        from src.core.ingestion.mineru_adapter import text_layer_pua_mangled
        garbage = GARBLED_ASCII_270
        assert len(garbage) >= 200
        assert text_layer_pua_mangled([{"text": garbage}]) is True

    def test_the_two_signals_separate_english_from_garbled_ascii(self):
        """把判据背后的**两个量**单独钉住（这样以后谁改了阈值，能看出动的是哪一条）。"""
        from src.core.ingestion.mineru_adapter import _looks_unlike_latin_prose
        assert _looks_unlike_latin_prose(self._EN) is False
        assert _looks_unlike_latin_prose(GARBLED_ASCII_270) is True


class TestLatinProseThresholdIsAnchored:
    """**阈值 0.70 不许是拍的**（2026-09-25 复核 P-2 打回后补，第 2 轮又被打回后重写）。

    第 1 次打回的原因：上面那三条测试只断言 `is True/False`，把两个阈值 0.70 → **0.90**
    之后**仍然 45 passed 全绿** ⇒ "阈值到底是多少"**当时没有任何测试在管**。

    第 2 次打回的原因（**这一版是按它重写的**）：我补的锚点用**自己另写的一份乱码样本**
    （取模现造那条）量 s2 上界 = 0.3808，而**仓里真正在用的两条乱码夹具**上界是 **0.4143**。
    ⇒ 锚点比真实约束松，它授权了一个组合（把字母/标点阈值放到 0.0、像词串阈值放到 0.381），
    在那个组合下**三条新测试全绿，而判据四对仓里那两条真乱码夹具已经失效**（复核变异 D）。
    ⇒ **教训写进断言里**：锚点只用**仓里既有夹具**，而且断言的是**行为不变量**
    （"每条乱码夹具都必须仍被判中"），不是我从某个样本上量出来的标量。

    ⚠ 锚点数值的出处（本机实测；探针在 gitignore 的 `var/` 下，故把结论抄在这里留痕）：
      · **真英文下界**（54 个真 PDF，独立复核 2026-09-25 机械复算，判据四在 PDF 上的真实口径
        `blocks[:120]`）：未判乱码的 51 份英文档 **s1 ∈ [0.8547, 0.9749]**。
        ⚠ 我自己先前的读法（38 份 `.md` 头部 4000 字）报的是 **0.8836**，
        **对不上，是偏乐观的**；原因见下面那条留痕。
      · **乱码夹具 s2 上界 0.4143**（`GARBLED_ASCII_270`；`GARBLED_ASCII_396` 是 0.4000）
        —— 复核逐字 AST 提取仓里全部夹具复算所得，与我的 0.3808 不符（我量错了样本）。
      · **目录段 s1 = 0.5765**（Lin/Nogueira/Yates 综述；复核扫窗独立量到 0.5762，Δ0.0003 ⇒ **真**），
        参考文献段 0.8824（复核量到 0.8832）。复核还在 Croft 教材 `blocks[20:]` 量到真英文低至
        **0.3524**（就是 Contents 点线页码区）—— 这两份现在安全只是因为开头 20 块恰好是版权页。

    ⚠ **留痕（两处对不上的数，别当成我量过）**：
      ① 我报的 `s1 ∈ [0.8836, 0.9624] / s2 ∈ [0.8871, 0.9612]` 复核**两种读法都复现不出**
         （它量到 `s1 ∈ [0.8787, 0.9608] / [0.8913, 0.9611]`）。**不能说是假的**：
         `.md` 的 mtime（18:59）晚于我提交（18:51）——**我随后跑了批次 2 的转换**，
         语料在提交后被整体重写过，旧版无备份、不进 git ⇒ 那组数**现在复核不了**，已不再引用。
      ② 我写的"真正承重的是 s2"——**在本机真语料上没有实例支撑**（唯一一对真乱码 chap1/chap10
         是**判据三a**抓的，s1=0.7185/s2=0.6649）。这句只对**取模现造那条**成立。
         准确的说法是：**不许只看 s1**（s1 单独抓不住取模现造那条，它 s1=0.8235 很高）。

    为什么还要留余量（`_MARGIN`）而不是贴着下界放：判据四吃的是**头部聚合样本**，而真英文里
    "标点密集的头"是真实存在的（目录段 0.5765、Croft 的 Contents 区 0.3524）⇒ 阈值一旦上抬到
    贴着文档级下界，这类文档就会被整份判乱码（**又是 0 字**）。
    """

    #: 真英文下界（出处见类 docstring）。**这是"不许误伤"那一侧的锚**。
    _EN_S1_MIN = 0.8547
    _EN_S2_MIN = 0.8861
    #: 阈值离真英文下界必须留的不动余量（理由见类 docstring 末段）。
    _MARGIN = 0.05

    #: 一段**逐字取自真语料**的英文（`2019_Passage_Reranking_with_BERT` 正文，
    #: 即我们已入库的 PDF 转文本；不是编的样例），它带引用/括号/年份，
    #: 是实测里**较难**的一档（s1≈0.88），所以拿它当活锚。
    _EN_REAL = (
        "1 INTRODUCTION We have seen rapid progress in machine reading compression in recent "
        "years with the introduction of large-scale datasets, such as SQuAD (Rajpurkar et al., "
        "2016), MS MARCO (Nguyen et al., 2016), SearchQA (Dunn et al., 2017), TriviaQA (Joshi "
        "et al., 2017), and QUASAR-T (Dhingra et al., 2017), and the broad adoption of neural "
        "models, such as BiDAF (Seo et al., 2016), DrQA (Chen et al., 2017), DocumentQA (Clark "
        "& Gardner, 2017), and QAnet (Yu et al., 2018). The information retrieval community has "
        "also produced large-scale datasets and effective neural rankers."
    )

    def test_real_english_excerpt_stays_above_both_thresholds(self):
        """活锚：真语料里较难的一段，两个量都还高过阈值**且留有余量**。"""
        from src.core.ingestion.mineru_adapter import (
            _MIN_LETTER_RATIO, _MIN_WORDY_RATIO, _latin_prose_signals,
        )
        s1, s2 = _latin_prose_signals(self._EN_REAL)
        assert len(self._EN_REAL) >= 200, "前提：样本 ≥200 字，否则判据四不生效"
        assert s1 > _MIN_LETTER_RATIO and s2 > _MIN_WORDY_RATIO, (
            f"真英文段落被两个量判成「不像散文」（s1={s1:.4f} s2={s2:.4f}）⇒ 整份 0 字")
        assert s1 - _MIN_LETTER_RATIO >= self._MARGIN, (
            f"阈值离实测真英文太近（s1={s1:.4f} vs 阈值 {_MIN_LETTER_RATIO}）")

    def test_thresholds_sit_inside_the_measured_gap(self):
        """阈值不许贴住真英文下界（这一条杀"改严"：0.70→0.90 就死在这里）。"""
        from src.core.ingestion.mineru_adapter import (
            _MIN_LETTER_RATIO, _MIN_WORDY_RATIO,
        )
        assert _MIN_LETTER_RATIO <= self._EN_S1_MIN - self._MARGIN, (
            f"字母/标点阈值 {_MIN_LETTER_RATIO} 太靠近实测真英文下界 "
            f"{self._EN_S1_MIN} ⇒ 头部标点密集的真文档会被整份判乱码")
        assert _MIN_WORDY_RATIO <= self._EN_S2_MIN - self._MARGIN, (
            f"像词串阈值 {_MIN_WORDY_RATIO} 太靠近实测真英文下界 {self._EN_S2_MIN}")

    def test_every_repo_garbled_fixture_is_still_caught(self):
        """**行为不变量**：仓里每一条乱码夹具都必须仍被判中（这一条杀"改宽"）。

        为什么不写成"阈值 > 某个 s2 标量"：那样只约束了一个数，而判据是
        `s1 < T1 or s2 < T2` 的**或**——两个阈值一起放宽就能从旁边绕过去
        （复核变异 D：T1=0.0 + T2=0.381 ⇒ 标量断言仍绿、真乱码已漏）。
        断言行为本身，绕不过去。

        ⚠ 这里**故意只用仓里既有的夹具**（模块级那三条 + 取模现造那条），
        不另造样本 —— 第 2 次打回就是因为锚点锚在了我自己另写的样本上。
        """
        from src.core.ingestion.mineru_adapter import (
            _MIN_LETTER_RATIO, _MIN_WORDY_RATIO, _latin_prose_signals,
        )
        mod94 = "".join(chr(0x21 + ord(c) % 94)
                        for c in ("汉字被映射成 ASCII 的乱码形态" * 40))
        fixtures = {
            "GARBLED_ASCII_396（仓里既有，判据四型）": GARBLED_ASCII_396,
            "GARBLED_ASCII_270（仓里既有，判据四型）": GARBLED_ASCII_270,
            "GARBLED_CID（仓里既有，判据三型）": GARBLED_CID,
            "取模现造（本仓新测试用的那条）": mod94,
        }
        for name, g in fixtures.items():
            s1, s2 = _latin_prose_signals(g)
            assert s1 < _MIN_LETTER_RATIO or s2 < _MIN_WORDY_RATIO, (
                f"{name} 已不被「不像散文」判据抓住（s1={s1:.4f} s2={s2:.4f} vs "
                f"阈值 {_MIN_LETTER_RATIO}/{_MIN_WORDY_RATIO}）⇒ 真乱码会漏进库。"
                f"⚠ 注意这是**或**关系：单独放宽任一个都还能被另一个兜住，"
                f"两个一起放宽就会从旁边绕过去。")

    def test_letter_ratio_side_has_no_repo_fixture_lower_bound(self):
        """**诚实登记**：字母/标点那一侧的**下界在本仓钉不住**——别假装钉住了。

        ⚠ **本条第 1 版写成 `pytest.skip()`，被棘轮当场打回**（`-Full` 实测：
        "出现基线里没有的 skip nodeid" ⇒ 整体失败）。仓规里"测试只涨不跌"**专门防
        "悄悄跳过"**，所以**登记空白不能用 skip 表达**——skip 会在每次门禁里留下一条
        永久豁免，相当于把"没在测"伪装成"测过了"。⇒ 本条改成**纯断言 + 说明**。

        事实（复核变异 B 实测）：`_MIN_LETTER_RATIO = 0.0` 时 **83 passed 全绿**——
        因为仓里所有乱码夹具的 s2（≤0.4143）都被 `_MIN_WORDY_RATIO=0.70` 单独兜住，
        **没有任何一条夹具是"只有 s1 才能抓住"的**。⇒ 想真正约束 s1 的下界，
        得先有**一条 s1 低、s2 高**的真乱码样本；在那之前 **s1 只是 s2 的旁证**，
        不是承重判据。本仓现有真乱码（chap1/chap10，s1=0.7185/s2=0.6649）是**判据三a**抓的，
        也不是那种样本。

        所以这里断言的是**可以证实的那一半**：s1 的门槛确实没有仓内锚（把它调到 0
        也仍然全绿）——写成断言而不是 skip，是为了让"这条空白"每次门禁都被**机械地过一遍**，
        而不是躺在注释里。
        """
        from src.core.ingestion.mineru_adapter import (
            _MIN_LETTER_RATIO, _MIN_WORDY_RATIO, _latin_prose_signals,
        )
        only_s1 = [(s1, s2) for s1, s2 in (
            _latin_prose_signals(GARBLED_ASCII_396),
            _latin_prose_signals(GARBLED_ASCII_270),
            _latin_prose_signals(GARBLED_CID),
        ) if s1 < _MIN_LETTER_RATIO and s2 >= _MIN_WORDY_RATIO]
        assert not only_s1, (
            f"仓里**出现**了「只有 s1 才抓得住」的乱码夹具 {only_s1} ⇒ "
            f"现在可以给 `_MIN_LETTER_RATIO` 补一条真的下界断言了"
            f"（本条的空白已消失，请更新这里）")


def test_delete_document_uses_bulk_fts_delete(db):
    """E10 性能根因（2026-08-28 试点实测）：clause_fts.clause_revision_id 是
    UNINDEXED 列，逐行 DELETE 每行都全表扫描 24 万行 FTS 索引——覆盖式重入库
    每本文档都要付分钟级代价（py-spy 实测单文档卡 15 分钟）。
    delete_document 必须用单条子查询批量删除（≤2 条语句），且删干净不留孤儿。"""
    from src.core.domain.models import ClauseRevisionModel
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction

    if db.execute("SELECT 1 FROM doc_meta WHERE doc_id='e10'").fetchone():
        clause_repo.delete_document("e10")
    with write_transaction() as c:
        clause_repo.insert_document(c, dict(
            doc_id="e10", standard_no="GB E10-2025", standard_name="E10",
            short_code="e10", current_revision_id="r", domain_tags=[],
            file_path="e10.pdf", file_hash="he10"))
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id=f"e10c{i}", doc_id="e10", clause_key=f"e10k{i}",
            standard_no="GB E10-2025", clause_number=f"4.{i}",
            content_text=f"条款 {i} 的内容。", knowledge_type="legal",
            modality="应", modality_strength=3, page_start=1, page_end=1)
        for i in range(30)
    ])
    assert db.execute(
        "SELECT COUNT(*) FROM clause_fts WHERE clause_revision_id LIKE 'e10c%'"
    ).fetchone()[0] == 30

    stmts: list[str] = []
    db.set_trace_callback(stmts.append)
    try:
        clause_repo.delete_document("e10")
    finally:
        db.set_trace_callback(None)
    fts_deletes = [s for s in stmts if "DELETE FROM CLAUSE_FTS" in s.upper()]
    assert len(fts_deletes) <= 2, (
        f"clause_fts 删除语句 {len(fts_deletes)} 条（30 条款）——仍是逐行全表扫描")
    assert db.execute(
        "SELECT COUNT(*) FROM clause_fts WHERE clause_revision_id LIKE 'e10c%'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM clause_vec WHERE clause_revision_id LIKE 'e10c%'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT 1 FROM doc_meta WHERE doc_id='e10'").fetchone() is None


def test_build_models_classification_and_edges(tmp_path):
    items, page_sizes = load_middle_items(_mk_middle(tmp_path))
    clauses = split_items_into_clauses(items)
    models, raw_edges = build_clause_models("d1", "GB T-2022", "standard", clauses, page_sizes)
    by_no = {m.clause_number: m for m in models}
    m521, m522 = by_no["5.2.1"], by_no["5.2.2"]
    assert m521.knowledge_type == "rule" and m521.modality == "应"
    assert m522.knowledge_type == "data", "含数值量纲应归 data 型"
    assert m522.modality is None, "'可燃气体'的'可'不应误判为模态"
    assert m521.exception and "节假日" in m521.exception
    assert m521.hierarchy_path == "5 > 5.2"
    # 坐标契约（v5 修正）：source_span 原样直存 MinerU bbox（PDF 底部原点，y 向上；
    # 页顶文本 y 接近页高）。前端 PdfViewer 直接 convertToViewportPoint(x, y)，禁止翻转。
    span = m521.source_spans[0]
    assert span.bbox == pytest.approx([60.0, 700.0, 530.0, 740.0])  # 原样直存，未翻转
    number_to_id = {m.clause_number: m.clause_revision_id for m in models}
    edges = resolve_edges(raw_edges, number_to_id)
    assert all(e[0] in ("reference_relation", "exception_relation") for e in edges)


def test_classifier_details():
    tc = classify_clause("高层民用建筑之间的防火间距不应小于13m", doc_type="standard")
    assert tc.knowledge_type == "data" and tc.modality == "不应"
    tc2 = classify_clause("经营者不得利用格式条款排除消费者权利", doc_type="法律法规")
    assert tc2.knowledge_type == "legal" and tc2.subject == "经营者"
    tc3 = classify_clause("本规范第5.2.1条规定了动火监护要求", doc_type="standard")
    assert "5.2.1" in tc3.cross_refs
    assert normalize_clause_number("05.02.01") == "5.2.1"


@pytest.mark.skipif(
    not Path("var/mineru_cli_out/GB30871-2022识别版/auto/GB30871-2022识别版_middle.json").exists(),
    reason="真实 MinerU 产物不存在（本机运行时自动启用）")
def test_real_middle_json_integration():
    items, page_sizes = load_middle_items(
        Path("var/mineru_cli_out/GB30871-2022识别版/auto/GB30871-2022识别版_middle.json"))
    assert len(items) > 100
    clauses = split_items_into_clauses(items)
    numbers = {c.number for c in clauses}
    assert "5.2.1" in numbers and "6.2" in numbers
    c521 = next(c for c in clauses if c.number == "5.2.1")
    assert "专人监护" in c521.texts[0]


def test_interline_equation_restored(tmp_path):
    """2026-09-01 独立公式行（interline_equation）不再蒸发（GB/T 24276
    "公式没识别出来"根因）：此前 _spans_rows 只认 inline_equation，
    interline_equation 块 parts 落空 → 整条公式从条目流消失。修复后
    同走 latex_to_text → 可读 Unicode 文本行，并入所属条款。"""
    mj = {"pdf_info": [
        {"page_idx": 6, "page_size": [595.0, 841.0], "para_blocks": [
            {"type": "text", "bbox": [60, 700, 530, 740], "lines": [
                {"spans": [{"type": "text",
                            "content": "5.2.4 外壳的温升应按下式计算："}]}]},
            {"type": "interline_equation", "bbox": [251, 650, 419, 680],
             "lines": [{"spans": [{"type": "interline_equation",
                                   "content": "f { = } \\frac { h ^ { 1.35 } } "
                                              "{ A _ { \\mathrm { b } } }"}]}]},
        ]},
    ]}
    p = tmp_path / "eq_middle.json"
    p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")

    items, _ = load_middle_items(p)
    eq = [i for i in items if i.kind == "text" and "f =" in (i.text or "")]
    assert eq, "独立公式行必须以文本条目入库，不得蒸发"
    t = eq[0].text
    assert "\\" not in t and "{" not in t, \
        f"LaTeX 命令/花括号应转为可读文本，实际: {t!r}"
    assert eq[0].bbox, "公式条目应带框（行框齐备，PDF 高亮不缺位）"

    clauses = split_items_into_clauses(items)
    assert [c.number for c in clauses] == ["5.2.4"], \
        "公式行不得伪造条款头（闸门兜底）"
    c524 = clauses[0]
    assert any("f =" in ln for ln in c524.texts), "公式行应并入所属条款 texts"


def test_resolve_edges_reports_unresolved():
    """未解析引用必须留痕（iteration-6 自查 §8.2，代码级核实）。

    旧实现 `if src and dst and src != dst:` **没有 else、无日志、无计数** ——
    引用目标解析不到时那条边直接蒸发。而"条款写着『应符合 GB XXXX 的 5.2.3』
    而本库没有那一条"**本身就是合规风险**，且用户与检查者都无从知晓，
    正打在 KS「可溯源」的价值主张上。

    参照 eyecite（BSD-2，`resolve.py:288-293`）的纪律：**歧义即不解析，
    但失败项必须留痕**。本用例钉住 `unresolved_out` 的语义，并确认
    **返回值与既有调用方零改动**（不传该参数时行为逐字不变）。
    """
    number_to_id = {"5.2.1": "rev_a", "5.2.2": "rev_b"}
    raw = [
        {"edge_type": "reference_relation", "src": "5.2.1", "dst": "5.2.2",
         "conf": 0.9, "status": "active"},                 # 两端都在 → 成边
        {"edge_type": "reference_relation", "src": "5.2.1", "dst": "9.9.9",
         "conf": 0.9, "status": "active"},                 # dst 不在本库 → 未解析
        {"edge_type": "exception_relation", "src": "外部标准", "dst": "5.2.1",
         "conf": 0.9, "status": "active"},                 # src 不在本库 → 未解析
        {"edge_type": "reference_relation", "src": "5.2.1", "dst": "5.2.1",
         "conf": 0.9, "status": "active"},                 # 自环 → 不成边
        {"edge_type": "clause_relation", "src": "5.2.1", "dst": "5.2.2",
         "conf": 0.9, "status": "active"},                 # 表绑定 → 有意跳过
    ]
    unresolved: list = []
    edges = resolve_edges(raw, number_to_id, unresolved)

    assert len(edges) == 1, "只有两端都解析到且非自环的边才成立"
    assert edges[0][1] == "rev_a" and edges[0][2] == "rev_b"
    # clause_relation 是**有意跳过**（表绑定已落在条款内部），不得计入"未解析"
    assert len(unresolved) == 3, f"应留痕 3 条，实际 {unresolved}"
    by = {(u["src"], u["dst"]): u for u in unresolved}
    assert by[("5.2.1", "9.9.9")]["reason"] == "unresolved_reference"
    assert by[("5.2.1", "9.9.9")]["missing"] == ["dst"], "要指明未解析的是哪一端"
    assert by[("外部标准", "5.2.1")]["missing"] == ["src"]
    assert by[("5.2.1", "5.2.1")]["reason"] == "self_loop"
    # 非破坏：不传 unresolved_out 时返回值与旧签名逐字一致
    assert resolve_edges(raw, number_to_id) == edges
