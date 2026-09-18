"""渠道台账端点（§11.0 R2b）：**只读**。

为什么只读先落地：面板（R4）要的是"链接 / 有效性 / 上次成功查询"三列的**数据源**，
而这三列的语义已经由 `channel_repo` 定死（`wiring` 与 `state` 分开、`summary()` 把
注册数与能力数分开报）。写接口（人工增删改/立即探测）要等 R3 的探针出来再一起做，
否则会出现"面板能改但改了不知道有没有用"的空壳。

⚠ 两个端点都是 **`def`**（不是 `async def`）：它们走 SQLite，必须在**线程池**里跑，
否则单事件循环被阻塞（§10.87/§10.88 的名单制门禁会拦 async 版本——本文件因此不需要
往 `tests/test_material_api.py::_ASYNC_ENDPOINTS` 里加任何条目）。
"""
from __future__ import annotations

from src.core.storage import channel_repo as cr


def register(app, json_error):
    @app.get("/api/v1/channels")
    def list_channels(category: str | None = None, wiring: str | None = None,
                      state: str | None = None, verification: str | None = None,
                      enabled_only: bool = False, limit: int = 500):
        """渠道台账列表（面板表格数据源）。

        - 四个筛选都是**可选**；非法值不 404，而是让 `channel_repo` 抛 `ValueError`
          翻成 422（口径统一：参数错是 422，不是"空结果"——空结果会让人以为库里没这条）。
        - `summary` 与 `items` **一起返回**：面板头部要显示"能干活几条 / 台账几条"，
          分开两次请求会出现两次口径不同的数字（R1 的 G5/G6 就是这么虚高的）。
        """
        if limit < 1 or limit > 2000:
            return json_error(422, "illegal_limit", f"limit 需在 1..2000（收到 {limit}）")
        for name, value in (("category", category), ("wiring", wiring),
                            ("state", state), ("verification", verification)):
            if value is None:
                continue
            allowed = {"category": cr.CATEGORIES, "wiring": cr.WIRING,
                       "state": cr.STATE, "verification": cr.VERIFICATION}[name]
            if value not in allowed:
                return json_error(422, "illegal_channel_filter",
                                  f"{name}={value!r} 不在 {list(allowed)}")
        items = cr.list_channels(category=category, wiring=wiring, state=state,
                                 verification=verification, enabled_only=enabled_only)[:limit]
        # ⚠ `has_probe_target`（R6）：面板上「⚪ 未探」其实是**三种不同的处境**——
        #   ① "还没给它配探针"（tool 类的代码仓库、我方代码通路）；
        #   ② "配了、也探了，但只探到连通性"（`last_error_code=no_anchor_configured`，
        #      通道回 200 却没有语义期望 ⇒ **不算可抓**，也不是欠账）；
        #   ③ "配了但还没探过"（真欠账）。
        #   字段只回答"有没有目标"（①③ 的分界）；② 要看 `last_error_code`——
        #   两处口径合起来才能把三种处境分开（独立复核 b28-fix2 的第 5 条）。
        #   不区分的话，业主无法判断一条灰行是"等我们做"还是"这条本来就不该探"。
        #   探针目标表是随包发布的小 JSON（一次读 100+ 条），就在这一层补上，
        #   不往数据库里塞第二份真相（表是唯一所有者）。
        #   ⚠ 局部导入：本模块被 app 启动时导入，而 `src.core.update` 会把整包适配器拉进来
        #   —— 只是为了让面板少一次歧义，不值得抬高**每次启动**的代价。
        from src.core.update import channel_probe as cp
        targets = cp.load_targets()
        for it in items:
            it["has_probe_target"] = it["channel_id"] in targets
        return {"code": 200, "status": "success",
                "data": {"summary": cr.summary(), "items": items}}

    @app.get("/api/v1/channels/{channel_id}")
    def get_channel(channel_id: str):
        """单条渠道详情（面板行展开用）。不存在 → 404（不是空对象）。"""
        from src.core.update import channel_probe as cp
        row = cr.get_channel(channel_id)
        if row is None:
            return json_error(404, "channel_not_found", f"渠道不存在: {channel_id}")
        row["has_probe_target"] = channel_id in cp.load_targets()
        return {"code": 200, "status": "success", "data": row}

    @app.post("/api/v1/channels/probe")
    def probe_channels(body: dict | None = None):
        """**立刻探一遍**（面板上的人工动作：怀疑某个渠道坏了，点一下看真相）。

        - `body.ids`：只探这些 channel_id（省略 = 所有配了探针目标的渠道）；
        - `body.persist`：默认 true；false = 只探不落库（调试用）。
        ⚠ 单线程序列执行（体检不是爬取）：一个渠道一次请求、超时 20s。
          传几百个 id 会把请求拖很久——面板一次别点多条（宿主侧也有超时）。
        ⚠ 不传 `ids` 时**只探配了目标的渠道**（数量随目标表变：R3 时 28 条，R6 后 **102** 条），
          不会盲探全部台账（131 条）。
        """
        from src.core.update import channel_probe as cp
        b = body or {}
        ids = b.get("ids")
        if ids is not None and (not isinstance(ids, list)
                               or not all(isinstance(i, str) for i in ids)):
            return json_error(422, "illegal_ids", "ids 必须是字符串数组")
        try:
            out = cp.probe_channels(ids=ids, persist=bool(b.get("persist", True)))
        except ValueError as e:
            return json_error(404, "channel_not_found", str(e))
        out["summary"] = cr.summary()
        return {"code": 200, "status": "success", "data": out}
