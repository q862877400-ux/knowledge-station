"""MinerU (magic-pdf) 版面解析适配器 + PyMuPDF 几何提取（T03'）。

分层降级策略：
1. 几何提取 (rotation/crop_box/media_box) — 纯 PyMuPDF，始终可用；
2. 文本块提取 — PyMuPDF 文本层（识别版 PDF 秒级完成）；
3. MinerU 深度版面分析 — **云优先 → 本地兜底**（2026-09-08 用户修订）：
   用户在「设置→API配置」配置云 OCR Key 时先走 MinerU 官方云 API，
   云失败/不可用则回退本地（GPU 攒批服务 → 进程内 do_parse）；未配置
   Key 则直接走本地通道（纯本地、不外发）；两条都不可用则记录日志继续，
   不阻塞入库（完整管线在 T05）。
"""
from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

from src.core.exceptions import ParserError
from src.core.text_utils import strip_block_noise

logger = logging.getLogger(__name__)


def extract_page_geometries(pdf_path: Path) -> Dict[int, Dict[str, Any]]:
    """提取每页 PDF 的 Point 宽高、旋转角、CropBox、MediaBox（PyMuPDF）。"""
    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf_path))
    geometries: Dict[int, Dict[str, Any]] = {}
    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            rect = page.rect
            cropbox = page.cropbox
            mediabox = page.mediabox
            geometries[page_idx + 1] = {
                "width": float(rect.width),
                "height": float(rect.height),
                "rotation": int(page.rotation),
                "crop_box": [float(cropbox.x0), float(cropbox.y0),
                             float(cropbox.x1), float(cropbox.y1)],
                "media_box": [float(mediabox.x0), float(mediabox.y0),
                              float(mediabox.x1), float(mediabox.y1)],
            }
    finally:
        doc.close()
    return geometries


def _extract_text_blocks(pdf_path: Path) -> List[Dict[str, Any]]:
    """PyMuPDF 文本块（含 bbox，已转 PDF 左下原点坐标系）。"""
    import fitz

    blocks: List[Dict[str, Any]] = []
    with fitz.open(str(pdf_path)) as doc:
        for pno in range(len(doc)):
            page = doc[pno]
            page_h = page.rect.height
            for b in page.get_text("dict")["blocks"]:
                if b.get("type") != 0:  # 0 = 文本块
                    continue
                lines_text = []
                for line in b.get("lines", []):
                    span_text = "".join(sp.get("text", "") for sp in line.get("spans", []))
                    lines_text.append(span_text)
                x0, y0, x1, y1 = b["bbox"]
                text = "\n".join(t for t in lines_text if t.strip())
                if not text:
                    continue
                blocks.append({
                    "page_number": pno + 1,
                    "text": text,
                    "bbox": [float(x0), float(page_h - y1), float(x1), float(page_h - y0)],
                    "source": "pymupdf",
                })
    return blocks


# GB 出版 PDF 的内嵌 CID 字体 ASCII 错位（2026-08-28 假 ok 第二真凶）：
# 文本层"存在"但字形码整体平移——'GB/T'→'犌犅／犜'、数字 '0'-'9'→'!'-'*'
# （0x30+d → 0x21+d）。切分器认不出任何条款号，按行入库会把全文坍缩成
# 1 条前置说明。唯一判定所有者：预分拣（_classify_text_layer）与解析
# ladder（parse_pdf_with_mineru）共用，两端口径一致。
_PUA_GB_PREFIX = re.compile(r"[犌犅犜]")

# 2026-08-29 块级噪声剔除（语料级，GB/T 34406-2017 实测）：盗版标准站每页页眉
# 水印块（"www.bzfxw.com" 独立块，切分压平后粘进条款尾）与页眉/页脚页码块
# （全角页码 '３' NFKC 归一化后为半角数字，罗马页码 'Ⅰ'→'I'）。
_RE_PAGENO = re.compile(r"[IVXivx\d]{1,4}")


def _clean_blocks(blocks: List[dict]) -> List[dict]:
    """通用二次清洗（2026-08-29，语料级，GB/T 34406-2017 实测）：
    ① 每块行级 strip_block_noise（水印行/公式引导点线）；
    ② 剔除纯水印块（'www.bzfxw.com' 每页页眉，压平后粘条款尾）；
    ③ 剔除页眉/页脚区纯页码块（全角页码 '３' 已 NFKC 为 '3'，罗马 'Ⅰ'→'I'）。

    页码块判定额外要求 bbox 落在页面顶部 ≤100pt 或底部 ≥700pt（fitz 顶部
    原点；A4/Letter 页边距内正文首行 y0≈90+ 且行高外扩，不会误伤正文）。
    """
    out: List[dict] = []
    for b in blocks:
        t = b.get("text")
        if t is None:
            out.append(b)
            continue
        t2 = strip_block_noise(t)
        if not t2.strip():
            continue  # 整块水印/点线
        # 防御性 NFKC：管线语义上 _clean_blocks 只在归一化后调用，
        # 此处再折叠一次，保证罗马页码 'Ⅰ'（U+2160）等直接输入也能命中
        rest = re.sub(r"\s", "", unicodedata.normalize("NFKC", t2))
        if _RE_PAGENO.fullmatch(rest):
            bb = b.get("bbox") or []
            if len(bb) == 4 and (bb[3] <= 100 or bb[1] >= 700):
                continue  # 页眉/页脚页码块
        if t2 != t:
            b2 = dict(b)
            b2["text"] = t2
            out.append(b2)
        else:
            out.append(b)
    return out


def _reflow_block(b: dict, fn) -> dict:
    """对单个 block 的 text 应用行级重排；无变化时复用原对象。"""
    t = b.get("text")
    if not t:
        return b
    t2 = fn(t)
    if t2 == t:
        return b
    b2 = dict(b)
    b2["text"] = t2
    return b2


#: 「像词」的判定：≥3 个字母、含元音、且没有 5 个以上连续非元音字母。
#: 真英文散文里绝大多数字母串都满足；"汉字被映射成 ASCII"的乱码则不满足
#: （字母串短、密集夹标点/变音字母）。
_VOWELS = frozenset("aeiouAEIOU")
_NONVOWEL_RUN = re.compile(r"[^aeiouAEIOU\s]{5,}", re.IGNORECASE)

#: 判据四的两个阈值。**不是拍的**，是从实测间隔里选的，两侧都留了余量：
#:   · 字母/(字母+标点)：真英文 0.94~0.96，乱码 0.53~0.69
#:   · 像词串占比：真英文 0.91~0.95，乱码 0.27~0.40
#: 独立复核（2026-09-25）在**全语料 54 个真 PDF** 上量到英文文档级
#: s1 ∈ [0.855, 0.975]、s2 ∈ [0.882, 0.953]，真英文最近的一侧仍留 +0.155/+0.182。
#: ⚠ 改这两个数**必须两侧都实测**（夹具仍判中 + 全语料 A/B 不掉块），
#:   见 `_looks_unlike_latin_prose` 里"误判代价"那段。
#: `tests/test_pipeline.py::TestLatinProseThresholdIsAnchored` 会断言它们
#: **落在实测间隔内且离真英文一侧留有余量**——所以改宽改严都会当场变红。
_MIN_LETTER_RATIO = 0.70
_MIN_WORDY_RATIO = 0.70


def _latin_prose_signals(text: str) -> tuple[float, float]:
    """判据四的两个量：`(字母/(字母+标点), 像词串占比)`。判据见 `_looks_unlike_latin_prose`。

    抽出来是为了**能被测试直接断言数值**：原先两个量埋在布尔函数里，测试只能断言
    `is True/False`，于是阈值改成任何值都可能照样全绿（2026-09-25 复核 P-2 实测
    0.70→0.90 仍 45 passed）——"阈值是多少"这件事当时**没有任何测试在管**。
    """
    letters = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    punct = sum(1 for ch in text if ch.isascii() and not ch.isalnum() and not ch.isspace())
    ratio = letters / max(letters + punct, 1)
    runs = re.findall(r"[A-Za-z]{2,}", text)
    if not runs:
        return ratio, 0.0                      # 一个字母串都没有 ⇒ 记为 0（必判乱码）
    wordy = sum(len(r) for r in runs
                if len(r) >= 3 and (set(r) & _VOWELS) and not _NONVOWEL_RUN.search(r))
    return ratio, wordy / max(sum(len(r) for r in runs), 1)


def _looks_unlike_latin_prose(text: str) -> bool:
    """这段文字**像不像正常的拉丁文散文**？（不像 ⇒ 倾向判乱码）

    为修 P0.11 而加（2026-09-25）：判据四原先只看"CJK 占比 <5%"，把英文文档全判成乱码。
    这里给两个**互相独立**的量，任一异常即认为"不像正常拉丁散文"：

    1. **字母/(字母+标点)**：正常英文散文 ≈0.94~0.98（标点稀疏）；
       "汉字被映射成 ASCII"的乱码 ≈0.53~0.69（标点密集）。
    2. **像词串占比**：正常英文 ≈0.91~0.95；乱码 ≈0.27~0.40。

    阈值 0.70 取自 `var/tmp/probe-pua-discriminator.py` 的实测对照表
    （正样本＝仓里既有的 GB/T 35210.1-2023 与 cid 乱码夹具；负样本＝三篇 arXiv 英文论文
    前 4,000 字 + 正常英文句）。⚠ 对**纯公式密集**的英文页可能偏保守（判成不像散文）。

    ⚠⚠ **误判的代价不是"多走一次 OCR"**（2026-09-25 复核打回并更正，这里原文写错过）：
    判成 mangled ⇒ `blocks=[]`，而**材料入库默认 `deep_fallback=False`**（深通道云优先、
    会外发，见本文件 `if not blocks:` 分支）⇒ **没有人来救 ⇒ 整份 0 字**，
    与 P0.11 那个病**一模一样**。所以两个方向都不免费：判宽了放进真乱码，
    判严了英文文档整份消失。⇒ **动这两个阈值必须两侧都实测**：
    ① 构造乱码夹具仍判 True；② 全语料 A/B 不许出现"有块变 0 块"。
    """
    letter_ratio, wordy_ratio = _latin_prose_signals(text)
    return letter_ratio < _MIN_LETTER_RATIO or wordy_ratio < _MIN_WORDY_RATIO


def text_layer_pua_mangled(blocks: List[dict]) -> bool:
    """文本层是否为 PUA 错位字体（不可用于条款切分，必须走像素 OCR）。"""
    sample: List[str] = []
    total = 0
    for b in blocks[:120]:
        t = (b.get("text") or "").strip()
        if t:
            sample.append(t)
            total += len(t)
        if total > 4000:
            break
    if not sample:
        return False
    joined = "\n".join(sample)
    # 判据一：犌/犅/犜 错位字形（封面"犌犅／犜"几乎必现，正常中文不含此组合）
    if len(_PUA_GB_PREFIX.findall(joined)) >= 2:
        return True
    # 判据二：数字位整体错位（'!'-'*' = 0x21-0x2A 占比异常高）
    # 2026-09-02 修复误判：0x21-0x2A 也含正常标点 '(' ')' '*' '!' 等。真"数字整体
    # 平移"型文本层必然同时缺正常数字（0x30-0x39 占比≈0，数字都被平移进 !-*）；
    # 正常文档 0x21-2A 只是零散标点、0x30-39 数字正常——不应判 PUA。叠加"正常数字
    # 占比异常低"防误判（GB/T 1000-2016 实测：'('→'7'、')'→'8' 即被此误判 +
    # normalize_pua_latin ② 的 +15 把正常括号误还原，引入 '7简称8'）。
    shift = sum(1 for ch in joined if 0x21 <= ord(ch) <= 0x2A)
    digits = sum(1 for ch in joined if "0" <= ch <= "9")
    if shift >= 30 and shift / max(1, len(joined)) > 0.03 \
            and digits / max(1, len(joined)) < 0.005:
        return True
    # 判据三（2026-08-28 E9，GB/T 20529.2-2010 实测）：cid 乱码第三形态——
    # 文本层由 错位 cid 渲染为 拉丁扩展/泰米尔/CJK扩展A 等异常区字符
    # （'ಆćććććććć'），无 犌犅犜 也无数字错位。两个子判据：
    #   a) 异常区字符占比 >15%（样本 ≥200 字）：ASCII/常用汉字(4E00-9FFF)/
    #      中文标点(3000-303F,FF00-FFEF)/常用符号 之外都算异常；
    #   b) 非 ASCII、非汉字字符连续同字长跑 ≥12（cid fallback 的典型形态）。
    if len(joined) >= 200:
        weird = sum(1 for ch in joined if _is_weird_char(ch))
        if weird / len(joined) > 0.15:
            return True
        # 判据四（2026-08-28 E9b，GB/T 35210.1-2023 实测）：cid 错位第四形态——
        # 汉字被整体映射为 ASCII 拉丁/标点（"34.567.589.:;) a)*<'*!'=>yz+a>?k@>GA"），
        # 无怪区字符、无非 ASCII 长跑，前三判据全漏。
        # 中文国标正文不可能没有汉字：样本 ≥200 字而 CJK 占比 <5% 即判乱码。
        # ⚠ 原文此处写「误判代价仅为多走一次 OCR，零数据风险」——**错话，已更正**
        #   （2026-09-25 复核打回）：`deep_fallback=False`（材料入库默认）时没有 OCR 可走，
        #   误判 ⇒ `blocks=[]` ⇒ **整份 0 字**，就是 P0.11 这个病本身。代价见
        #   `_looks_unlike_latin_prose` 的说明。
        # 🔴 2026-09-25 修误判（计划 P0.11）：原来**只**看"CJK 占比 <5%"就判乱码，
        # 于是**任何非中文文档**（英文论文/技术文档）都被判 PUA mangled ⇒ blocks=[]；
        # 而材料入库默认 deep_fallback=False（深通道云优先、会外发）⇒ 无人救 ⇒ 整份 0 字。
        # 实测 `2023_Query2doc.pdf`（arXiv）：抽出 181 个块、文字干净，却被判 mangled。
        # ⇒ 叠加"**这不像真拉丁文本**"两个量（阈值由实测选定，见
        #   var/tmp/probe-pua-discriminator.py 的对照表）：
        #     · 字母/(字母+标点)：乱码 0.53~0.69 vs 真英文 0.94~0.96
        #     · 像词串占比（≥3 字母、含元音、无 5 连辅音的串占比）：乱码 0.27~0.40 vs 0.91~0.95
        #   两者取**或**：任一项像"不是正常拉丁散文"就仍判乱码（宁可多走一次 OCR，
        #   也不能让真乱码进来）；**真英文两项都高，因此不再被误伤**。
        # ⚠ 前置条件"CJK<5%"保留：中文文档（CJK≥5%）根本走不到这里，不受影响。
        cjk = sum(1 for ch in joined if "\u4e00" <= ch <= "\u9fff")
        if cjk / len(joined) < 0.05 and _looks_unlike_latin_prose(joined):
            return True
    run, prev = 1, None
    for ch in joined:
        # 2026-09-02 修复误判：长跑判据只对「异常区字符」(cid 乱码) 计连续同字。
        # 国标正文的长破折号 '———' / 重复符号是常用标点（_is_weird_char=False），
        # 不该触发——GB/T 1000-2016 实测因 '———' 等正常符号被判 PUA mangled，
        # 导致文本层被弃、走 OCR 深度丢字。
        if (ch == prev and not ch.isspace() and _is_weird_char(ch)):
            run += 1
            if run >= 12:
                return True
        else:
            run = 1
        prev = ch
    return False


def _is_weird_char(ch: str) -> bool:
    """异常区字符：不属于 ASCII/常用汉字/中文标点/常用符号 的字符。"""
    o = ord(ch)
    if ch.isascii() or 0x4E00 <= o <= 0x9FFF:
        return False
    if 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF:
        return False
    if o in (0x00B7, 0x00D7, 0x00B0, 0x00AE, 0x2013, 0x2014, 0x2015,
             0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x2122):
        return False
    return True


#: 公开别名（2026-09-11）：质量判定侧（R27 预览/数据体检）复用**同一**异常字符判据，
#: 避免复制实现导致两套口径。注意 0xFFFD（替换字符）落在 0xFF00–0xFFEF 白名单里 →
#: 本判据**不**把替换字符算作异常字符，那需要独立判据（见 quality.recognition）。
is_weird_char = _is_weird_char


def mineru_available() -> bool:
    try:
        import mineru  # noqa: F401 — MinerU 2.x (magic-pdf 继任包)
        return True
    except ImportError:
        try:
            import magic_pdf  # noqa: F401 — 旧名兼容
            return True
        except ImportError:
            return False


_GPU_LOCK_DEFAULT_TIMEOUT_S = 3600.0


@contextlib.contextmanager
def _gpu_deep_lock():
    """跨进程 GPU 排队锁：16GB 显存只容一路 MinerU 深度管线，并发分片
    同时上卡必然 CUDA OOM（2026-08-27 三分片战况实测 ~95% 瞬败，单跑同
    文档 117s 完整成功）。持锁进程崩溃时 OS 自动释放文件锁，无残留死锁；
    KS_GPU_LOCK=0 关闭（测试/冒烟），KS_GPU_LOCK_PATH/KS_GPU_LOCK_TIMEOUT
    可覆盖锁文件与等待上限。"""
    if os.environ.get("KS_GPU_LOCK", "1") == "0":
        yield
        return
    lock_path = Path(os.environ.get("KS_GPU_LOCK_PATH") or
                     (Path(tempfile.gettempdir()) / "ks_mineru_gpu.lock"))
    timeout_s = float(os.environ.get("KS_GPU_LOCK_TIMEOUT",
                                     _GPU_LOCK_DEFAULT_TIMEOUT_S))
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    t0 = time.monotonic()
    try:
        while True:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(  # type: ignore[attr-defined]  # fcntl=POSIX-only；本分支仅 os.name!=nt 到达
                        fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]  # 同上：fcntl=POSIX-only
                break
            except OSError:
                if time.monotonic() - t0 > timeout_s:
                    raise TimeoutError(
                        f"GPU 锁等待超时 {timeout_s}s: {lock_path}") from None
                time.sleep(0.5)
        yield
    finally:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)  # type: ignore[attr-defined]  # fcntl=POSIX-only；本分支仅 os.name!=nt 到达
        except OSError:
            pass
        os.close(fd)


def _cloud_enabled() -> bool:
    """云解析通道是否可用（2026-09-08 用户修订后的语义）。

    - 用户已在「设置→API配置」配置云 OCR Key（HKCU 注册表/环境变量）→ True；
    - KS_MINERU_CLOUD=0 → 显式禁用云（纯本地，给不想外发的用户）；
    - 未配置 Key → False（导入文件直接走本地通道）。
    """
    if os.environ.get("KS_MINERU_CLOUD", "1") == "0":
        return False
    from src.core.ingestion.mineru_cloud import mineru_cloud_available
    ok, _ = mineru_cloud_available()
    return ok


def _local_backend() -> str:
    """本地深度通道的 MinerU backend。

    2026-09-15（用户指令）：**本次 OCR 后处理进化循环只走 VLM**——云 VLM 优先，
    云不通则本地 VLM，**pipeline 不参与**。为此提供两个环境开关：

    - `KS_VLM_ONLY=1`：强制本地 backend = `vlm-engine`（循环进化专用；同时禁止
      任何 pipeline 兜底，见 `_pipeline_allowed`）；
    - `KS_MINERU_LOCAL_BACKEND`：显式指定 `pipeline` / `vlm-engine` /
      `hybrid-engine`（未设置或非法值 → 历史默认 `pipeline`，保证既有行为不变）。
    """
    import os
    if os.environ.get("KS_VLM_ONLY", "") == "1":
        return "vlm-engine"
    v = (os.environ.get("KS_MINERU_LOCAL_BACKEND") or "").strip()
    return v if v in ("pipeline", "vlm-engine", "hybrid-engine") else "pipeline"


def _pipeline_allowed() -> bool:
    """本次调用是否允许 pipeline 通道（KS_VLM_ONLY=1 时一律不允许）。"""
    import os
    return os.environ.get("KS_VLM_ONLY", "") != "1"


def _mineru_deep_analyze(pdf_path: Path, output_dir: Path) -> Dict[str, Any] | None:
    """深度版面分析（2026-09-08 用户修订：**云优先 → 本地兜底**）。

    通道决策：
    1. 已配置云 OCR Key（且未 KS_MINERU_CLOUD=0）→ **先走 MinerU 官方云 API**；
       云失败/超时/产物守卫失败 → 回退本地通道（GPU 攒批服务 → 进程内 do_parse）；
    2. 未配置 Key → **直接本地通道**（纯本地，不外发）；
    3. KS_MINERU_LOCAL=0 → 跳过本地（云失败后无更多通道，返回 None）；
    4. KS_MINERU_DEEP=0 → 整体跳过深度分析（冒烟/测试用）。

    云产物归一化为本地同构布局（见 mineru_cloud），下游解析路径不感知通道。
    旧语义（本地优先→云兜底）已被本函数 2026-09-08 修订取代，见
    docs/DSH_REINCARNATION.md 台账。
    """
    import os
    if os.environ.get("KS_MINERU_DEEP", "1") == "0":
        return None

    cloud_on = _cloud_enabled()
    if cloud_on:
        try:
            logger.info("走云解析优先通道 (%s)", pdf_path.name)
            from src.core.ingestion.mineru_cloud import mineru_cloud_submit_and_wait
            r = mineru_cloud_submit_and_wait(pdf_path, output_dir)
            if r is not None:
                return r
            # 2026-09-08 修复（verifier F1）：该函数契约是**网络/超时/HTTP 类失败
            # 返回 None（不抛异常）**——原先直接 return 会把本地兜底整个短路，
            # 配了云 Key 后任何云侧抖动都导致扫描版 PDF 无法解析。
            logger.warning("云解析返回 None（网络/超时/HTTP 失败），回退本地通道: %s",
                           pdf_path.name)
        except Exception as e:  # noqa: BLE001 — 云失败不阻塞，回退本地兜底
            logger.warning("云解析失败，回退本地通道: %s", e)

    local_disabled = os.environ.get("KS_MINERU_LOCAL", "1") == "0"
    if not local_disabled and mineru_available():
        try:
            # 常驻 GPU 攒批服务优先（模型只加载一次 + 多文档合并批次）；
            # 服务不可用/超时/任务失败 → 回退旧版单文档路径（本进程内 do_parse）
            if os.environ.get("KS_DEEP_SERVER", "1") != "0":
                from src.core.ingestion.deep_server import deep_server_submit_and_wait
                r = deep_server_submit_and_wait(pdf_path, output_dir / "mineru",
                                                timeout=1800.0)
                if r is not None:
                    return {"output_dir": r["output_dir"]}
            from mineru.cli.common import do_parse

            out_dir = output_dir / "mineru"
            out_dir.mkdir(parents=True, exist_ok=True)
            t_lock = time.monotonic()
            with _gpu_deep_lock():
                logger.info("GPU deep 上卡 (%s, 排队 %.1fs)",
                            pdf_path.name, time.monotonic() - t_lock)
                # 2026-09-14（执行计划 v3 阶段 1）：ch → ch_server（v6 medium_rec），
                # 与 deep_server.py 批量通道同步升档。
                # 2026-09-15（用户指令）：backend 改由 _local_backend() 决定——
                # KS_VLM_ONLY=1 时走 vlm-engine（本地 VLM），pipeline 不参与。
                do_parse(str(out_dir), [pdf_path.stem], [pdf_path.read_bytes()],
                         ["ch_server"],
                         backend=_local_backend(), parse_method="auto",
                         f_draw_layout_bbox=False, f_draw_span_bbox=False,
                         f_dump_orig_pdf=False, f_dump_model_output=False)
            return {"output_dir": str(out_dir)}
        except Exception as e:  # noqa: BLE001 — 本地失败不阻塞入库，返回 None
            logger.warning("MinerU 本地深度分析失败: %s", e)
    else:
        if local_disabled:
            logger.info("KS_MINERU_LOCAL=0：跳过本地深度分析")
        else:
            logger.info("mineru 未安装，本地深度分析不可用")

    if cloud_on:
        logger.info("云解析已优先尝试且失败，本地通道亦不可用——无文本层文档无法解析")
    else:
        logger.info("未配置云 OCR Key（纯本地模式），本地通道不可用——无文本层文档无法解析")
    return None


def parse_pdf_with_mineru(pdf_path: Path, output_dir: Path,
                          force_deep: bool = False,
                          deep_fallback: bool = True) -> Dict[str, Any]:
    """标准化解析入口（Parser Worker 子进程中执行）。

    force_deep=True（T05 完整管线）：**无文本层**文档强制走深度分析
    （受跨进程 GPU 排队锁串行化）；有文本层文档直接用文本块秒级返回，
    不占 GPU（2026-08-27 修复：原条件把 deep 误限定在 not blocks 分支之外、
    文本层文档也试图上卡，且管线误拒非 is_ocr 的 blocks——B/C 区秒败双真凶）。
    无文本层：深度分析（2026-09-08 起**云优先、本地兜底**，见 _mineru_deep_analyze）。

    deep_fallback=False（2026-09-11 新增，R27 入库预览用）：**无文本层时不调深度分析**
    ——预览必须在"用户以为只是本地看看"的前提下保证零外发、零 GPU 占用，而
    深度通道是云优先的。此时如返回 `deep_fallback_skipped=True` + `text_layer_state`，
    由调用方据此如实判"扫描件/乱码"。默认 True = 既有行为逐字节不变。

    返回值新增两个键（纯加法，既有调用方不受影响）：
      text_layer_state: "ok" | "ok_normalized" | "pua_mangled" | "empty"
      deep_fallback_skipped: 是否因 deep_fallback=False 而**放弃**了本该走的深度分析
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    geometries = extract_page_geometries(pdf_path)
    raw_blocks = _extract_text_blocks(pdf_path)
    blocks = raw_blocks
    mangled = bool(raw_blocks) and text_layer_pua_mangled(raw_blocks)
    recovered = False
    if mangled:
        # 2026-08-29：PUA 错位字体先试归一化（形近 CJK→拉丁、错位数字→原值、NFKC）。
        # 归一化后复验干净 → 复用文本层（秒级入库，不占 GPU/云 OCR 配额）；
        # 仍乱 → 文本层真不可用，转像素 OCR 通道（保守回退零数据风险）。
        from src.core.text_utils import normalize_pua_latin
        fixed_blocks = []
        for b in blocks:
            t = b.get("text")
            if t:
                b2 = dict(b)
                b2["text"] = normalize_pua_latin(t)
                fixed_blocks.append(b2)
        if text_layer_pua_mangled(fixed_blocks):
            logger.info("PUA 错位字体文本层归一化无效 → 转 OCR 通道 (%s)", pdf_path.name)
            blocks = []
        else:
            blocks = fixed_blocks
            recovered = True
            logger.info("PUA 错位字体文本层已归一化复用 (%s)", pdf_path.name)

    blocks = _clean_blocks(blocks)

    # 2026-08-29 根号套分式行序重排（语料级，GB/T 34406 式(1)(2) 实测）：
    # 文本层把 √(分子/分母) 压成「分子行/分母行/√ 行」线性序列，压平后根号
    # 悬尾不可读；重排为数学读序 'R=√(分子/分母)'（保守触发，详见函数说明）。
    from src.core.text_utils import reflow_sqrt_formulas
    blocks = [_reflow_block(b, reflow_sqrt_formulas) for b in blocks]

    text_layer_state = ("ok_normalized" if recovered else "ok") if blocks else (
        "pua_mangled" if (mangled and not recovered) else "empty")

    is_ocr = False
    deep_output: str | None = None
    deep_fallback_skipped = False
    if not blocks:
        if not deep_fallback:
            # 预览模式：明确放弃深度通道（云优先 → 会外发），如实标注
            deep_fallback_skipped = True
            logger.info("deep_fallback=False：无文本层文档跳过深度分析（零外发）(%s)",
                        pdf_path.name)
        else:
            # 只有真正无文本层才上深度分析（本地 GPU 优先 → 云解析兜底，
            # 2026-09-01 架构反转，见 _mineru_deep_analyze）；
            # force_deep 语义 = 此兜底为必经（区别于冒烟模式可跳过）。
            deep = _mineru_deep_analyze(pdf_path, output_dir)
            if deep is None:
                if not blocks:
                    raise ParserError(
                        f"PDF 无文本层且深度解析不可用（本地未装/跑不动时可在"
                        f"设置中配置云解析 API Key）: {pdf_path.name}")
            else:
                deep_output = deep["output_dir"]
    # 2026-09-02 治本（正常入库识别流程丢字修复）：文本层完好时**不再跑深度**。
    # 深度模型对文本层重识别会丢数字/字母/标准号（GB/T 1000-2016 实测：
    # 10kV→空、GB/T 197→/、图号→空）；正文用 fitz 文本层保真（切分已修，
    # 章级条款不丢），表/图由矢量表格重建 + figure_locator 兜底，公式为线性文本。
    # 仅真正无文本层（blocks 空）才走深度（OCR 通道），深度正文仅供 OCR，
    # 其在文本层文档上丢字，故不可用于文本层。

    (output_dir / "blocks.json").write_text(
        json.dumps(blocks, ensure_ascii=False), encoding="utf-8")
    return {"blocks": blocks, "geometries": geometries, "is_ocr": is_ocr,
            "deep_output": deep_output,
            "text_layer_state": text_layer_state,
            "deep_fallback_skipped": deep_fallback_skipped}
