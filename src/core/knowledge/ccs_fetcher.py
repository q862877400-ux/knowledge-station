"""入库自动查询中国标准分类号（CCS）——官方渠道抓取（2026-08-23 新增）。

依据用户指定权威渠道：
  - 中国标准服务网 cssn.net.cn（中国标准化研究院主办）搜索结果列表直接含
    【CCS分类】<code><分类名>（如 "P16工程防火"、"C65劳动安全技术"），一次请求即得。
    流程：按标准编号搜索 → 列表页正则提取 CCS。
  - 失败降级：返回 None，由调用方用本地映射表兜底（不阻塞入库）。
网络不可用时自动跳过（离线可入库，分类后续可补）。
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

_CSSN_LIST = "https://www.cssn.net.cn/api/cssn/list"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ---------------------------------------------------------------------------
# 本地 CCS 种子库（2026-08 v2）：批量入库前由 std_bulk_import.py 从 CSSN 体检结果
# 一次性生成 <jsonl同级>/ccs_seed.json（数据区，数据/代码分离），经环境变量
# KS_CCS_SEED_FILE 注入——fetch_ccs 命中即零网络返回，未命中才回退在线查询。
# 未设置环境变量时行为完全不变（测试基线不受影响）。
# ---------------------------------------------------------------------------
_CCS_SEED_ENV = "KS_CCS_SEED_FILE"
_seed_cache: dict[str, dict] | None = None


def _seed_key(standard_no: str) -> str:
    """种子键归一（与 std_bulk_import.write_ccs_seed 同一约定）。"""
    return standard_no.upper().replace("／", "/").replace(" ", "")


def _load_ccs_seed() -> dict[str, dict]:
    """懒加载种子文件；只缓存成功解析的结果。

    未配置环境变量 / 文件缺失损坏时不缓存（每次仅一次 env 读取的成本），
    避免进程早期被错误地固化成"无种子"，导致后配的种子永远不可见。
    """
    global _seed_cache
    if _seed_cache:
        return _seed_cache
    p = os.environ.get(_CCS_SEED_ENV)
    if not p:
        return {}
    try:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            _seed_cache = {str(k): v for k, v in data.items()
                           if isinstance(v, dict) and v.get("code")}
    except Exception:
        pass          # 种子不可用≠入库失败：走原在线路径
    return _seed_cache or {}

# 本地兜底映射表（已人工核实官方 CCS；网络不可用时用，优先 cssn 实时结果）
LOCAL_CCS: dict[str, tuple[str, str]] = {
    "GB 30871-2022": ("C", "C65 劳动安全技术"),
    "GB 18218-2018": ("A", "A80 标志包装运输贮存"),
    "GB 3608-2025": ("C", "C75 劳动保护管理"),
    "GB/T 3608-2008": ("C", "C75 劳动保护管理"),
    "GB/T 29639-2020": ("C", "C78 劳动保护管理(应急)"),
    "AQ 3028-2008": ("B", "B09 农业、林业综合"),
    "GB 50140-2005": ("P", "P16 工程防火"),
    "GB 50444-2008": ("P", "P16 工程防火"),
    "GB 55010-2021": ("P", "P46 供热、采暖工程"),
    "GB 55036-2022": ("P", "P16 工程防火"),
    "GB 55037-2022": ("P", "P16 工程防火"),
    "GB/T 50493-2019": ("P", "P72 石化、化工工程"),
}

# 列表页条目块:每条含 标题 + 【CCS分类】... 
# 块边界用 标题 h3 与 后续 li 提取(按标准号过滤)
_BLOCK_TITLE = re.compile(r'ph_img_contenta301">([^<]+)</strong>')
_CCS_IN_BLOCK = re.compile(r'【CCS分类】</strong>([A-Z]\d{2}[^<]*)</li>')
_STD_NO_RE = re.compile(r"\d{4,6}")


def _major_from_code(code: str) -> str:
    """CCS 代码首字母 → 大类字母（P16 → P）。"""
    return code[:1] if code else ""


def fetch_ccs(standard_no: str, standard_name: str = "") -> dict | None:
    """按标准号查询 CCS。返回 {code, major, sub}；失败返回 None。

    种子优先（KS_CCS_SEED_FILE 命中即零网络返回，批量入库场景）；
    未命中走在线查询（cssn 列表页）。一次请求：搜索列表 → 找匹配标准号的条目 → 提取【CCS分类】。
    """
    seed = _load_ccs_seed().get(_seed_key(standard_no))
    if seed and seed.get("code"):
        code = str(seed["code"])
        return {"code": code, "major": _major_from_code(code), "sub": seed.get("sub") or ""}
    try:
        import httpx
        m = _STD_NO_RE.search(standard_no)
        if not m:
            return None
        num = m.group(0)
        client = httpx.Client(headers=_HEADERS, timeout=20, follow_redirects=True)
        try:
            r = client.get(_CSSN_LIST, params={"keyword": num})
            t = r.text
            # 按标题块切分,找含标准号/名称的块,提取其 CCS
            titles = list(_BLOCK_TITLE.finditer(t))
            for i, tm in enumerate(titles):
                title = tm.group(1).strip()
                # 名称/编号匹配
                hit = (standard_no.replace(" ", "").replace("/", "") in title
                       or (standard_name and standard_name[:6] in title))
                if not hit:
                    continue
                # 该块 = 从标题到下一个标题之间的文本
                end = titles[i + 1].start() if i + 1 < len(titles) else len(t)
                block = t[tm.start():end]
                cm = _CCS_IN_BLOCK.search(block)
                if cm:
                    raw = cm.group(1).strip()          # 如 "P16工程防火"
                    mm = re.match(r"([A-Z]\d{2})(.*)", raw)
                    assert mm is not None  # raw 非空且以大写字母开头（上面 strip 后必匹配）
                    code = mm.group(1)
                    sub = mm.group(2).strip() or ""
                    return {"code": code, "major": _major_from_code(code), "sub": sub}
            return None
        finally:
            client.close()
    except Exception:
        return None


def ccs_to_tag(ccs: dict | None, standard_no: str) -> str | None:
    """CCS 结果 → domain_tags 条目（"CCS:P16 工程防火"）。失败回退本地表。

    ⚠ 查本地表前先折**存储形**（§11.0 R6c-3f；独立复核 b36 实测点名的一处）：
    调用方给的是**折前**的号（`pipeline.py:2143`），而本地表的键是半角写法
    ⇒ 全角入参（`GB／T …`）在这里**静默查不到**、直接丢掉 CCS 标签。
    复核原话是"构造不出活复现"，所以影响面小；但"写入侧折了、读侧不折"这种不对称
    在本轮已经栽过一次（`resolve_clause`），同一个坑不该留第二个。
    """
    if ccs and ccs.get("code"):
        sub = ccs.get("sub") or ""
        return f"CCS:{ccs['code']}" + (f" {sub}" if sub else "")
    from src.core.text_utils import store_standard_no
    key = store_standard_no(standard_no)
    if key in LOCAL_CCS:
        code, sub = LOCAL_CCS[key]
        # sub 已含 code（如 "B09 农业、林业综合"），直接返回
        return f"CCS:{sub}" if sub else f"CCS:{code}"
    return None
