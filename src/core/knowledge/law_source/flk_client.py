"""flk.npc.gov.cn 国家法律法规数据库客户端（官方公开 API）。

接口状态核实于 2026-06（见 docs/LAW-SOURCE-PLAN.md §1）：
  POST /law-search/search/list      搜索（JSON body）
  GET  /law-search/search/enumData  分类/机关/时效枚举
  GET  /law-search/search/flfgDetails?bbbs=  详情（元数据+章条结构+ossFile）
  GET  /law-search/download/pc?format=docx|pdf&bbbs=  签名下载 URL（主路径，勿拼 ossFile）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.knowledge.law_source.http import download_file, fetch_json

BASE = "https://flk.npc.gov.cn"
_SEARCH = f"{BASE}/law-search/search/list"
_ENUM = f"{BASE}/law-search/search/enumData"
_DETAIL = f"{BASE}/law-search/search/flfgDetails"
_DOWNLOAD = f"{BASE}/law-search/download/pc"


def _headers(bbbs: str | None = None) -> dict[str, str]:
    return {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": f"{BASE}/detail?id={bbbs}" if bbbs else f"{BASE}/"}


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

def enum_data() -> dict[str, Any]:
    """全部分类/机关/时效字典（flfgCodeId / zdjgCodeId / sxx 叶子 code 表）。"""
    return fetch_json(_ENUM, referer=f"{BASE}/")


# ---------------------------------------------------------------------------
# 搜索
# ---------------------------------------------------------------------------

def search(content: str, *, search_range: int = 1, search_type: int = 2,
           category_ids: list[str] | None = None, org_ids: list[str] | None = None,
           sxx: list[int] | None = None, year: list[str] | None = None,
           gbrq: list[str] | None = None, sxrq: list[str] | None = None,
           sort: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """搜索（searchRange 1=标题 2=正文；searchType 1=精确 2=模糊）。

    sort 取值: "" 默认 | gbrq 公布日期 | sxrq 施行日期 | sxx 时效 | flxz 分类 | zdjg 机关。
    """
    payload = {
        "searchRange": search_range,
        "sxrq": sxrq or [],
        "gbrq": gbrq or [],
        "sxx": sxx or [],
        "searchType": search_type,
        "xgzlSearch": False,
        "searchContent": content,
        "orderByParam": {"order": "-1", "sort": sort},
        "flfgCodeId": category_ids or [],
        "zdjgCodeId": org_ids or [],
        "gbrqYear": year or [],
        "pageNum": page,
        "pageSize": page_size,
    }
    return fetch_json(_SEARCH, method="POST", json_body=payload, referer=f"{BASE}/search")


def parse_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    """搜索结果 rows → 精简列表（title / bbbs / flxz / zdjgName / gbrq / sxrq / sxx）。"""
    out = []
    for r in data.get("rows", []) or []:
        out.append({
            "bbbs": r.get("bbbs"),
            "title": r.get("title"),
            "flxz": r.get("flxz"),
            "zdjgName": r.get("zdjgName"),
            "gbrq": r.get("gbrq"),
            "sxrq": r.get("sxrq"),
            "sxx": r.get("sxx"),
        })
    return out


# ---------------------------------------------------------------------------
# 详情
# ---------------------------------------------------------------------------

@dataclass
class FlkDetail:
    bbbs: str
    title: str
    flxz: str = ""                 # 分类（法律/行政法规/…）
    zdjgName: str = ""             # 制定机关
    gbrq: str = ""                 # 公布日期
    sxrq: str = ""                 # 施行日期
    sxx: int | None = None         # 时效（3=有效）
    content: dict[str, Any] = field(default_factory=dict)   # 章/条结构化 children
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def oss_word_path(self) -> str:
        return (self.raw.get("ossFile") or {}).get("ossWordPath") or ""

    @property
    def oss_pdf_path(self) -> str:
        return (self.raw.get("ossFile") or {}).get("ossPdfPath") or ""


def detail(bbbs: str) -> FlkDetail:
    data = fetch_json(_DETAIL, params={"bbbs": bbbs}, referer=f"{BASE}/detail?id={bbbs}")
    d = (data.get("data") or {})
    return FlkDetail(
        bbbs=bbbs, title=d.get("title") or "", flxz=d.get("flxz") or "",
        zdjgName=d.get("zdjgName") or "", gbrq=d.get("gbrq") or "",
        sxrq=d.get("sxrq") or "", sxx=d.get("sxx"),
        content=d.get("content") or {}, raw=d)


def history(bbbs: str) -> list[dict[str, Any]]:
    """一部法规的**历次版本链**（详情接口的 `lsyg` = 历史沿革）。

    返回 ``[{"bbbs","title","gbrq","highlight"}]``，**按公布日期降序**
    （日期为空的沉底）。没有 `lsyg` 字段或为空 ⇒ 返回 ``[]``。

    ⚠ **空列表与查询失败必须区分**（spec FR-007）：
    - 官方返回了 `lsyg` 但为空/缺失 ⇒ 这是"确实没有历次版本"，返回 `[]`；
    - 网络/接口失败 ⇒ **抛异常**（`fetch_json` 会抛），**绝不**用 `[]` 冒充。

    ⚠ 字段名是 `highLight`（驼峰，官方原样），本函数**归一成 `highlight`** 输出。
    ⚠ `gbrq` 实测**可为 null**（如"包头市水资源管理条例"链上有一条 null），
      故排序时须容忍缺失——不能假定它是字符串。

    实测样例（2026-10-10，`bbbs=ff8081818f19d3bc018f6038d6d54d36`）：
    三版（2026-08-04 / 2024-04-07 / null）。⚠ 注意 `highLight=true` 标的是
    **2024-04-07 那版**而不是最新版——官方该标记的语义**未核实**，
    故本函数只**透传**它，不据此判断"哪版是现行"。
    """
    d = detail(bbbs)
    raw = d.raw.get("lsyg") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append({
            "bbbs": item.get("bbbs") or "",
            "title": item.get("title") or "",
            "gbrq": item.get("gbrq") or "",
            "highlight": bool(item.get("highLight")),
        })
    # 公布日期降序；空日期沉底（空串比任何 YYYY-MM-DD 小，故 reverse 后会沉底）
    out.sort(key=lambda r: r["gbrq"] or "", reverse=True)
    return out


# ---------------------------------------------------------------------------
# 下载（主路径：download/pc 拿签名 URL）
# ---------------------------------------------------------------------------

def download_url(bbbs: str, fmt: str = "docx") -> str:
    """返回签名 OSS URL；部分法规 format=pdf 返回空 data → 调用方回退 docx。"""
    data = fetch_json(_DOWNLOAD, params={"format": fmt, "bbbs": bbbs},
                      referer=f"{BASE}/detail?id={bbbs}")
    url = (data.get("data") or {}).get("url")
    if not url:
        raise ValueError(f"flk 下载链接为空: format={fmt} bbbs={bbbs}")
    return url


def download(bbbs: str, dest: Path, fmt: str = "docx") -> Path:
    """下载官方 Word/PDF 到 dest；docx 校验 ZIP 魔数。失败抛异常（不静默）。"""
    url = download_url(bbbs, fmt)
    expected = "pdf" if fmt == "pdf" else "docx"
    return download_file(url, dest, expected=expected,
                         referer=f"{BASE}/detail?id={bbbs}")
