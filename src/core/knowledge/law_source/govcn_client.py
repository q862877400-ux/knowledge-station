"""gov.cn 国务院政策文件库客户端（官方公开接口）。

搜索后端（核实于 2026-06，见 docs/LAW_SOURCE_PLAN.md §2）：
  GET https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary&q=...
详情页（www.gov.cn/...）：解析标题/正文/日期 + 官方下载链接（.docx/.doc/.ofd/.wps）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.core.knowledge.law_source.http import check_host, download_file, fetch_json

SEARCH_API = "https://sousuo.www.gov.cn/search-gov/data"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
       " (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
_DOWNLOAD_RE = re.compile(r'href=["\']([^"\']+\.(?:docx?|ofd|wps))["\']', re.I)

# childtype 映射（政策库 UI 分类）
CHILDTYPE = {
    "国务院文件": "gongwen",
    "部门文件": "bumenfile",
    "解读": "otherfile",
}


def search(keyword: str, *, field: str = "title", page: int = 0, size: int = 10,
           childtype: str = "", year: str = "", department: str = "",
           sort: str = "score", maxtime: str = "", mintime: str = "") -> dict[str, Any]:
    """搜索政策文件库。field: title|content；childtype: 国务院文件/部门文件/解读。"""
    params: dict[str, Any] = {
        "t": "zhengcelibrary", "q": keyword, "searchfield": field,
        "sort": sort, "sortType": 1, "p": page, "n": size, "type": "gwyzcwjk",
    }
    if childtype:
        params["childtype"] = CHILDTYPE.get(childtype, childtype)
    if year:
        params["pubtimeyear"] = year
    if department:
        params["bmfl"] = department
    if maxtime:
        params["maxtime"] = maxtime
    if mintime:
        params["mintime"] = mintime
    return fetch_json(SEARCH_API, params=params)


def parse_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    """搜索响应 → 精简列表（title / pcode 文号 / source 机关 / pubtime / url 详情页）。"""
    out = []
    sv = data.get("searchVO") or {}
    for cat in (sv.get("catMap") or {}).values():
        for item in cat.get("listVO", []) or []:
            title = re.sub(r"</?em>", "", item.get("title") or "")
            if not title:
                continue
            out.append({
                "title": title.strip(),
                "pcode": item.get("pcode") or "",
                "source": item.get("source") or "",
                "pubtime": item.get("pubtime") or "",
                "summary": re.sub(r"</?em>", "", item.get("summary") or "").strip(),
                # 实测：piclinksurl 常为空，稳定链接字段是 url（公报/解读条目）
                "url": item.get("url") or item.get("piclinksurl") or "",
                "category": cat.get("catName") or "",
            })
    return out


@dataclass
class GovDetail:
    url: str
    title: str = ""
    content_text: str = ""
    publish_date: str = ""
    source: str = ""
    download_urls: list[str] = field(default_factory=list)   # 官方 Word/OFD 直链（白名单内）


def fetch_detail(url: str) -> GovDetail:
    """抓取政策详情页：标题/正文/日期/来源 + 官方下载链接。

    下载链接仅保留白名单域（www.gov.cn / gov.cn）；页面无下载链接时
    download_urls 为空，调用方走"正文生成 docx"兜底（仍记官方来源 URL）。
    """
    host = check_host(url)
    headers = {"User-Agent": _UA}
    resp = requests.get(url, headers=headers, timeout=30, verify=False)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    title = (soup.select_one("h1") or soup.select_one(".article-title")
             or soup.select_one(".title") or soup.select_one("h2"))
    content = (soup.select_one(".article-content") or soup.select_one(".content")
               or soup.select_one("#content") or soup.select_one(".pages_content"))
    date_node = soup.select_one(".date, .time, .pub-date, .publish-time, .articletime")
    source_node = soup.select_one(".source, .origin, .article-source")

    detail = GovDetail(url=url)
    if title:
        detail.title = title.get_text(" ", strip=True)
    if not detail.title and soup.title and soup.title.string:
        # 公报等页面无 h1 时兜底 <title>（去掉站点后缀"__…_中国政府网"）
        t = soup.title.string.strip()
        if "__" in t:
            t = t.split("__")[0]
        detail.title = t.strip()
    if content:
        detail.content_text = content.get_text("\n", strip=True)
    if date_node:
        detail.publish_date = date_node.get_text(" ", strip=True)
    if source_node:
        detail.source = source_node.get_text(" ", strip=True)

    # 官方下载链接（href 以下载扩展名结尾），域名白名单校验
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        ext = re.search(r"\.(docx?|ofd|wps)$", href.lower())
        if not ext:
            continue
        try:
            check_host(href)
        except ValueError:
            continue  # 非官方域链接（如第三方镜像）丢弃
        if href not in seen:
            seen.add(href)
            detail.download_urls.append(href)
    return detail


def download(dest_dir, url: str, *, referer: str | None = None) -> Path:
    """下载官方文件（docx/ofd），魔数校验 ZIP；返回落盘路径。"""
    dest_dir = Path(dest_dir)
    ext = re.search(r"\.(docx?|ofd|wps)$", url.lower())
    suffix = ext.group(1) if ext else "docx"
    if suffix == "doc":
        suffix = "docx"  # 旧版 .doc 统一落盘为 source.docx（python-docx 不支持 .doc，转换器处理）
    dest = dest_dir / f"source.{suffix}"
    kind = "ofd" if suffix == "ofd" else "docx"
    return download_file(url, dest, expected=kind, referer=referer or url)
