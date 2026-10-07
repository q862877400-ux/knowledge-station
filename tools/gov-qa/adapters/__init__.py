"""政务问答采集 · 站点适配器登记处。

## 给接手的人（尤其要接着扒**各省市**的那位）

**加一个新站点 = 写一个适配器 + 在下面登记**，不用改别的地方。

### 适配器要长什么样
一个模块，暴露两个东西：

```python
SITE = {
    "key": "mee",                    # 短名，做文件名与去重前缀
    "name": "生态环境部",
    "kind": "api",                   # api | static  （怎么取：接口 or 静态列表）
    "level": "national",             # national | province | city
    "entry": "https://www.mee.gov.cn/hdjl/",
    "status": "ok",                  # ok | blocked | todo | chat_only
    "note": "WAS5 检索中间件；列表由内联 JS 调 /was5/web/search",
}

def harvest(fetch, *, limit=None) -> list[dict]:
    '''返回**统一的记录格式**（见下）。fetch(url, **kw) 是注入的 HTTP 函数。'''
```

### 统一的记录格式（**所有适配器都必须返回这个形状**）
```json
{
  "source": "mee",                       // = SITE["key"]
  "id": "1791251",                       // 站内唯一 id（用于去重）
  "url": "http://.../t20260116_1140853.shtml",
  "question": "关于十三五期间环保政策文件是否有效的咨询",
  "answer": "《生态环境部行政规范性文件制定和管理办法》适用于……",
  "asked_at": "2025.10.24 08:05:00",     // 可为 null
  "answered_at": "2025.10.27 11:04:00",  // 可为 null
  "dept": "办公厅",                       // 回复单位，可为 null
  "channel": "常见问题",                   // 该站内的栏目名，可为 null
  "extra": {}                            // 站点特有字段原样留着，别丢
}
```

⚠ **`answer` 必须是答复原文**，不要清洗、不要摘要 ——
下游要靠它抽出「答复点名了哪些文件」来判断这条能不能当考卷。

### 三条硬规矩（踩过的坑，别重踩）
1. **礼貌抓取**：请求之间 `sleep >= 1.5s`；能用接口就别逐页爬静态列表。
2. **`NO_PROXY` 里 `[::1]` 会让 httpx 直接崩**（本仓 G27）⇒ 动手前先把它改成 `::1`。
   政务站还常见「配置了代理反而被拦」，见 `README.md` 的"代理"一节：
   **实测代理与直连结果一样**，412 是站点反爬、405 是路径/方法不对。
3. **不许批量下载数据集**：这是"取问答文本"，不是"镜像网站"。一次一个站，取完就停。
"""
from __future__ import annotations

from typing import Callable

#: 已登记的适配器：key → 模块路径。
#: ⚠ **新增站点在这里加一行**，`harvest.py --list` 会读它。
ADAPTERS: dict[str, str] = {
    "hunan-st": "adapters.hunan_sthjt",   # 湖南省生态环境厅（统一互动平台，已跑通）
    "hunan-yj": "adapters.hunan_yjt",     # 湖南省应急管理厅（同一平台，已跑通）
    "mem": "adapters.mem_gov",            # 应急管理部（静态列表，已跑通）
    "mee": "adapters.mee_gov",            # 生态环境部（WAS5 接口，已跑通）
    "people-liuyan": "adapters.people_liuyan",  # 人民网领导留言板·部委版块（接口+签名，已跑通）
    "people-liuyan-df": "adapters.people_liuyan_df",  # 同平台·地方版块（省/市/县全国覆盖，已跑通）
    "gd-st": "adapters.gd_sthj",          # 广东省生态环境厅（同款 hdjlpt 平台，已跑通）
    "gd-yj": "adapters.gd_yjgl",          # 广东省应急管理厅（hdjlpt Laravel 接口，已跑通）
    "gd-hr": "adapters.gd_hrss",          # 广东省人社厅（同平台，年窗 510 条）
    "gd-jt": "adapters.gd_jt",            # 广东省交通运输厅（同平台）
    "gd-ws": "adapters.gd_wsjkw",         # 广东省卫健委（同平台）
    "gd-jy": "adapters.gd_eea",           # 广东省教育厅（同平台）
    "gd-fg": "adapters.gd_drc",           # 广东省发改委（同平台）
}

#: 用户要能直接 `from adapters import load`
FetchFn = Callable[..., object]


def load(key: str):
    """按 key 载入适配器模块（延迟导入，免得没装的依赖拦住别的站）。"""
    import importlib

    path = ADAPTERS.get(key)
    if not path:
        raise KeyError(f"未登记的站点 key：{key}；已登记：{sorted(ADAPTERS)}")
    return importlib.import_module(path)
