"""适配器：**人民网「领导留言板」· 部委版块**（媒体平台来源，非政府官网）。

## 与 Fissify/Message-Board-for-Leaders 的关系（改造说明，2026-10-07）
 · 它：Selenium 逐页点选（自述约 1000 条/小时），中央部委板块**不抓答复**，
   README 自述数据归人民网、仅限学术非商业。
 · 本适配器：**沿用它的字段口径，走站点自己的接口**（签名算法逆向自页面 JS，
   两组真实抓包样本验证一致），把部委板块的**官方答复**补上；
   未复制其代码，无许可证传递问题。
 · 采集面是**全站部委流**（不带 fid）：各部委版块页多是"提交入口"
   （如生态环境部 fid=5062 的 22 条全是待回复），有答复的条目在全站流里。
 · 详见 `_liuyan_common.py` 的「来源与出处」与接口/签名/参数语义说明。

## 扩展位
 · 地方版块（省/市/区县领导答复，量大且带满意度）：`_liuyan_common.harvest_liuyan`
   的 `stream="df"`，同构接口已实测（50/50 已办理）——要扩地方加一个薄适配器即可。
"""
from __future__ import annotations

from adapters._liuyan_common import harvest_liuyan

SITE = {
    "key": "people-liuyan",
    "name": "人民网领导留言板",
    "kind": "api",
    "level": "national",
    "entry": "https://liuyan.people.com.cn/index",
    "status": "ok",
    "note": "部委版块 threads/list/bw（showUnAnswer=0=已办理）+ threads/content（dataType=9=答复）；"
            "签名=md5(路径+param+md5(appCode)[:16])；媒体平台来源，答复为办理答复（与官网正式答复区分）",
}


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回部委版块带官方答复的问答（详见 _liuyan_common）。"""
    return harvest_liuyan(fetch, SITE=SITE, stream="bw", limit=limit)
