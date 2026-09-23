"""渠道台账端点（§11.0 R2b 只读 + R6d 人工维护）。

**只读先落地**（R2b）：面板要的是"链接 / 有效性 / 上次成功查询"三列的数据源，语义由
`channel_repo` 定死（`wiring` 与 `state` 分开、`summary()` 把注册数与能力数分开报）。

**写接口（R6d）**：业主的诉求是"渠道台账要能人工增删与复核"，所以本文件的写侧只做三件事，
且每件都**留痕**（`event_log`，actor=user，与改动同事务）：

- `POST /api/v1/channels`：新增（默认 `wiring='user'`）；
- `PATCH /api/v1/channels/{id}`：复核/编辑**描述性字段**；
- `POST /api/v1/channels/{id}/enabled`：启停（停用不删，历史健康度是证据）；
- `DELETE /api/v1/channels/{id}`：删除（痕迹里带删除前整行快照）。

⚠ **人工写不了运行期健康度**（`state`/`last_*`/`consecutive_failures`）：那是探针的产出，
人能填就等于凭空造证据 ⇒ 这些键一律 422 拒绝（不是静默丢弃——静默丢弃会让人以为写成功了）。
⚠ 本文件所有端点都是 **`def`**（不是 `async def`）：它们走 SQLite，必须在**线程池**里跑，
否则单事件循环被阻塞（§10.87/§10.88 的名单制门禁会拦 async 版本——本文件因此不需要
往 `tests/test_material_api.py::_ASYNC_ENDPOINTS` 里加任何条目）。
"""
from __future__ import annotations

import re

from src.core.storage import channel_repo as cr

#: 人工新增时可给的描述性字段（= 仓储 `_DESCRIPTIVE` 去掉引擎侧登记字段后的**可写子集**）
#: `segments_json`（号段，§11.0 R7）：**号段→渠道**是业主可维护的事实，所以它必须是可写的；
#: 形状校验（字符串数组、非空、去重）在仓储层 `check_segments`，错就 422 出声拒绝。
_WRITABLE = (
    "name", "category", "category_raw", "url", "fetch_kind", "list_endpoint",
    "params_json", "answers_json", "covers", "gaps", "wiring", "verification",
    "probe_url", "probe_expect", "source_file", "note", "segments_json",
    # 单位性质（2026-09-22）：用户面「分类」的那根轴（树=单位性质分组）。
    "org_kind",
)


def _new_user_channel_id(name: str) -> str:
    """人工新增的 id：`user:<slug>-<8位hash>`（稳定、可读、可追）。

    ⚠ 用 hash 而不是自增序号：两个人各加一条同名渠道不能互相覆盖，重跑同一次新增也拿到同一个 id
    （幂等）——而序号会在删除后重复利用，正是"id 复用"这类最难查的问题。
    """
    from ulid import ULID

    slug = re.sub(r"[^0-9a-zA-Z]+", "-", name).strip("-").lower()[:24] or "channel"
    return f"user:{slug}-{str(ULID())[-8:].lower()}"


def _reject_health_and_unknown(body: dict) -> str | None:
    """返回错误说明（None = 通过）。健康度字段与未知键都**出声拒绝**。"""
    bad_health = sorted(set(body) & set(cr.HEALTH_FIELDS))
    if bad_health:
        return (f"这些是**探针产出**的字段，人工不能写：{bad_health}；"
                f"要让它们变化请用 POST /api/v1/channels/probe")
    unknown = sorted(set(body) - set(_WRITABLE) - {"channel_id", "enabled"})
    if unknown:
        return f"未知字段：{unknown}（可写字段见 /api/v1/channels 的返回项）"
    return None


def register(app, json_error):
    # 单位性质粗分类回填（2026-09-22）：只填 NULL、幂等、人工标的不覆盖。
    try:
        cr.backfill_org_kind()
    except Exception as exc:  # noqa: BLE001 —— 回填失败不挡路由注册（面板照常开，未分类可人工标）
        # 复核点名修（2026-09-23）：原来是 except: pass 零留痕=静默失败；现在如实报一行。
        print(f"[ks] org_kind 回填失败（不挡路由注册，可人工标分类）：{exc!r}")
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

    @app.post("/api/v1/channels")
    def create_channel(body: dict | None = None):
        """**人工新增**一条渠道（面板"加一条"）。`name` 必填，`channel_id` 可省。

        新条目的默认值：`wiring='user'`（"这是人加进来的"，与适配器/种子区分开）、
        `verification='unverified'`（**人工录入 ≠ 已核实**：它得先被探一次才算数）、
        `enabled` 默认开。
        """
        b = dict(body or {})
        err = _reject_health_and_unknown(b)
        if err:
            return json_error(422, "illegal_channel_field", err)
        name = str(b.get("name") or "").strip()
        if not name:
            return json_error(422, "channel_name_required", "人工新增必须给 name")
        cid = str(b.get("channel_id") or "").strip() or _new_user_channel_id(name)
        if not cid.startswith("user:") and not re.match(r"^(ch|seed|user):", cid):
            return json_error(422, "illegal_channel_id",
                              "channel_id 需以 ch:/seed:/user: 开头（面板新增用 user:）")
        payload = {k: v for k, v in b.items() if k in _WRITABLE}
        payload["name"] = name
        payload.setdefault("wiring", "user")
        payload.setdefault("verification", "unverified")
        enabled = b.get("enabled")
        if enabled is not None:
            payload["enabled"] = 1 if enabled else 0
        try:
            row = cr.upsert_channel(cid, payload, actor="user")
        except ValueError as e:
            return json_error(422, "illegal_channel_field", str(e))
        return {"code": 200, "status": "success", "data": row}

    @app.patch("/api/v1/channels/{channel_id}")
    def update_channel(channel_id: str, body: dict | None = None):
        """**人工复核/编辑**描述性字段（面板"改链接/改备注/改五类声明"）。

        ⚠ 健康度字段走 `POST .../enabled` 或探针，不经这里（见模块 docstring）。
        """
        b = dict(body or {})
        err = _reject_health_and_unknown(b)
        if err:
            return json_error(422, "illegal_channel_field", err)
        if "enabled" in b:
            return json_error(422, "use_enabled_endpoint",
                              "启停请用 POST /api/v1/channels/{id}/enabled（语义与留痕不同）")
        payload = {k: v for k, v in b.items() if k in _WRITABLE}
        if not payload:
            return json_error(422, "empty_patch", "没有可写字段（描述性字段见 /api/v1/channels）")
        if cr.get_channel(channel_id) is None:
            return json_error(404, "channel_not_found", f"渠道不存在: {channel_id}")
        try:
            row = cr.upsert_channel(channel_id, payload, actor="user")
        except ValueError as e:
            return json_error(422, "illegal_channel_field", str(e))
        return {"code": 200, "status": "success", "data": row}

    @app.post("/api/v1/channels/{channel_id}/enabled")
    def set_channel_enabled(channel_id: str, body: dict | None = None):
        """**人工启停**（`{"enabled": false}` = 停用但保留历史健康度）。"""
        b = body or {}
        if not isinstance(b.get("enabled"), bool):
            return json_error(422, "illegal_enabled", 'body 需要 {"enabled": true|false}')
        try:
            row = cr.set_enabled(channel_id, b["enabled"], actor="user")
        except ValueError as e:
            return json_error(404, "channel_not_found", str(e))
        return {"code": 200, "status": "success", "data": row}

    @app.delete("/api/v1/channels/{channel_id}")
    def remove_channel(channel_id: str):
        """**人工删除**（高风险动作；默认建议用"停用"）。

        删除不是"抹掉证据"：`channel/deleted` 痕迹里带**删除前整行快照**
        （含 state/last_*），审计仍能回答"它当时是什么状态、什么时候没的"。
        """
        if cr.get_channel(channel_id) is None:
            return json_error(404, "channel_not_found", f"渠道不存在: {channel_id}")
        ok = cr.delete_channel(channel_id, actor="user")
        return {"code": 200, "status": "success", "data": {"deleted": bool(ok),
                                                           "channel_id": channel_id}}

    @app.post("/api/v1/channels/{channel_id}/test-case")
    def set_channel_test_case(channel_id: str, body: dict | None = None):
        """配/改这条渠道的「已知文件」（批C，2026-09-22 业主定）：样本链接 + 期望标准号。

        验收口径（业主原话）："成功把某个你知道的文件从新渠道下载或者识别下来了，
        那就说明这个渠道是成功的"。形状校验出声拒绝（缺参/空值 ⇒ 422）。"""
        body = body or {}
        url = str(body.get("sample_url") or "").strip()
        expect = str(body.get("expect_no") or "").strip()
        if url == "" or expect == "":
            return json_error(422, "test_case_needs_url_and_expect",
                              "sample_url（样本链接）与 expect_no（期望标准号）都要填")
        from src.core.update import channel_test as ct
        out = ct.set_test_case(channel_id, url, expect, body.get("note"))
        if out is None:
            return json_error(404, "channel_not_found", f"渠道不存在: {channel_id}")
        return {"code": 200, "status": "success", "data": {"test_case": out}}

    @app.get("/api/v1/channels/{channel_id}/test-case")
    def get_channel_test_case(channel_id: str):
        """读这条渠道的「已知文件」+ 最近一次测试留痕（没配 = data.test_case 为 null）。"""
        from src.core.update import channel_test as ct
        return {"code": 200, "status": "success",
                "data": {"test_case": ct.get_test_case(channel_id)}}

    @app.post("/api/v1/channels/{channel_id}/test")
    def run_channel_test(channel_id: str, body: dict | None = None):
        """跑「已知文件测试」：真拉样本 → 识别标准号 → 比对期望 → **结果留痕**。

        返回 {"result": "ok"|"fail"|"no_case", "detail": 人话}；失败也落库（没留痕=没测过）。
        真网络 GET（10s 超时）——这是验收动作，不是探针；错误如实返回，不粉饰。"""
        from src.core.update import channel_test as ct
        return {"code": 200, "status": "success", "data": ct.run_channel_test(channel_id)}

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
