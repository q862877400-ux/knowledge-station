"""适配器：**江门市人民政府·网民留言及答复**（静态 `content/post_<id>.html` 列表）。

## 为什么是这条栏目（不是别的）

`recon/probe-city-hd-api.py` 列出江门互动页的全部入口后，逐个实测：
 · `/hdjlpt/published` → **404**（江门没部署 hdjlpt）
 · `/gzhd/lyxd/`（**留言选登**）→ 200，且明细页**确实是问答**
   （昵称/留言时间/主题/内容 + 受理时间/答复时间/答复单位/答复内容）

⚠ 同站另有 `/gzhd/jgfk/`，是**结果反馈**不是问答 —— 别混。

引擎见 `_post_list_common.py`。翻页 `index.html` → `index_2.html` → `index_3.html`。
"""
from __future__ import annotations

from adapters._post_list_common import harvest_post_list

SITE = {
    "key": "gd-jiangmen",
    "name": "江门市人民政府·网民留言及答复",
    "kind": "html",
    "level": "city",
    "entry": "http://www.jiangmen.gov.cn/gzhd/lyxd/index.html",
    "status": "ok",
    "note": "静态 content/post 列表；明细为 th/td 表（主题/内容 + 答复单位/答复内容）",
}

BASE = "http://www.jiangmen.gov.cn"
LIST = "/gzhd/lyxd/"

#: 问题侧字段（明细表里的 th 标签）
Q_KEYS = ("主题", "内容")
#: 答复侧字段
A_KEYS = ("答复内容",)


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回江门「网民留言及答复」全文。"""
    return harvest_post_list(fetch, SITE=SITE, BASE=BASE, LIST=LIST,
                             q_keys=Q_KEYS, a_keys=A_KEYS, limit=limit)
