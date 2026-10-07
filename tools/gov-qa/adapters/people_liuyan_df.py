"""适配器：**人民网「领导留言板」· 地方版块**（省/市/区县，全国覆盖）。

## 为什么这是"全国省市县覆盖"的近路（2026-10-07 实测）
地方版块 `/v1/threads/list/df` 与部委版块同构（同签名、同翻页、同答复抽取），
一条流里混着**全国 31 省 → 地市 → 区县**的留言，行内自带归属：
 · `pForumNames`（如 `["河北省","衡水市"]`）→ 已采进每条记录的 `extra`；
 · `forumName` → 具体承办单位（某市生态环境局……）。
⇒ **不需要逐省写适配器**，一条流按 `extra.pForumNames` 自行分省归档。

## 边界（继承 _liuyan_common 的全部口径）
 · 媒体平台来源；答复是"办理答复"，与官网正式答复区分（数据归人民网，注明出处）；
 · 只收已办理（`showUnAnswer=0`）且详情确有 `dataType==9` 答复的条目；
 · ⚠ 403 限流实测在案（见 SITE-REGISTRY「people-liuyan 的两个未决问题」）——
   `PAUSE` 默认提到 2.5s，大批量采集分多次跑。
"""
from __future__ import annotations

from pathlib import Path

from adapters._liuyan_common import harvest_liuyan

#: 游标文件：时间流按时间排序，每轮**从上次位置续采**（否则去重会把新数据全挡掉，
#: 实测不加游标时一轮只新增 1 条）
CURSOR = Path(__file__).resolve().parent.parent / "data" / ".people-liuyan-df.cursor"

SITE = {
    "key": "people-liuyan-df",
    "name": "人民网领导留言板·地方",
    "kind": "api",
    "level": "mixed",        # 同一流内省/市/县混排，按 extra.pForumNames 区分
    "entry": "https://liuyan.people.com.cn/index",
    "status": "ok",
    "note": "地方版块 threads/list/df（showUnAnswer=0=已办理）；"
            "省/市/县归属在 extra.pForumNames；游标续采 + 限流冷却后分批",
}


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回地方版块带官方答复的问答（详见 _liuyan_common）。"""
    return harvest_liuyan(fetch, SITE=SITE, stream="df", limit=limit,
                          cursor_file=CURSOR)
