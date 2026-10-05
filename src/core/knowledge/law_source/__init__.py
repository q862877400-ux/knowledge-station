"""官方法律法规来源管线（docs/LAW-SOURCE-PLAN.md）：

flk.npc.gov.cn（国家法律法规数据库）+ gov.cn（国务院政策文件库）→
官方带格式 Word → LibreOffice/WPS 转 PDF → 现有 run_full_ingest 管线
（预览/高亮/目录/条款修正与标准件完全同构）。来源域白名单在 http.py 强制。
"""
from src.core.knowledge.law_source import convert, flk_client, govcn_client
from src.core.knowledge.law_source.ingest import (
    ensure_schema,
    find_by_source,
    ingest_law_from_flk,
    ingest_law_from_govcn,
)

__all__ = [
    "convert", "flk_client", "govcn_client",
    "ensure_schema", "find_by_source",
    "ingest_law_from_flk", "ingest_law_from_govcn",
]
