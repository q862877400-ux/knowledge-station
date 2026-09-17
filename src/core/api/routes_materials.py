# -*- coding: utf-8 -*-
"""材料平面 API 路由（2026-09-17 定位转移 Phase A 第四步）。

## 为什么要有这一层
Phase A 前三步把引擎侧做通了，但**用户碰不到**——"放一份 PDF → 评审通过 → 提问"里的
"放"和"评审"都只能由代码干。本模块把那条链开成端点，让 GUI 能真正驱动。

## 端点
- POST   /api/v1/materials/projects                    建项目
- GET    /api/v1/materials/projects                    列项目
- GET    /api/v1/materials/projects/{pid}/inbox        列出项目参考资料文件夹里的文件
- POST   /api/v1/materials/projects/{pid}/scan         扫描收件（登记为 pending 材料）
- POST   /api/v1/materials/projects/{pid}/collect      按 URL **自采**一份（Phase C-5 接线；
                                                      **不接受 `source_tier`**，见端点 docstring）
- GET    /api/v1/materials/projects/{pid}/materials    列材料（**评审/管理视图**，含 pending）
- GET    /api/v1/materials/projects/{pid}/search       在**已批准**材料里检索（见下方硬门）
- GET    /api/v1/materials/{mid}                       单份材料
- GET    /api/v1/materials/{mid}/chunks                切片分页（评审时要能读到内容）
- POST   /api/v1/materials/{mid}/review                批准/拒绝
- POST   /api/v1/materials/{mid}/tier                  改来源可信度（轴 A，用户可改）
- POST   /api/v1/materials/{mid}/role                  声明任务内效力（轴 B）
- POST   /api/v1/materials/{mid}/lifecycle             一次性 ↔ 长期
- DELETE /api/v1/materials/{mid}                       删除材料（连切片与索引）

## 两条纪律（与 storage/material_repo 同源，不要在这一层另起一套）
1. **`search` 走 `material_repo.search_materials()`**：评审硬门写死在那条 SQL 里
   （`JOIN material … review_status='approved'`）。本层**不得**为了"方便"自己拼查询；
2. **枚举校验交给仓库层**（它抛 ValueError）→ 本层统一转 422。判据只有一个所有者，
   端点层只做"取参数、转错误"。

校验语义：缺字段/非法枚举 → 422 `materials_bad_request`；找不到 → 404 `materials_not_found`；
项目目录不存在 → 404 `materials_dir_not_found`（由 material_repo 建目录，故一般不会）。
"""
from __future__ import annotations

from src.core.exceptions import KnowledgeStationError


def _run_track_l(material_id: str) -> dict:
    """批准后跑 Track L（采到的法规/标准要不要进法条库），**异常也翻成如实结果**。

    为什么不让它抛：`materials_review` 的**主旨已经完成**（材料的评审状态已落库），
    这时 Track L 抛错不该把响应变成 500——那会让界面显示"评审失败"，而用户明明批准成功了。
    但**也绝不吞掉**：异常被翻成 `action='error'` + 原因，随 `data.track_l` 一起回去。

    ⚠ 唯一的写库发生在 `track_l.reconcile` 内部，且它自己守着"必须已批准"这道门。
    """
    try:
        from src.core.materials import track_l as tl
        return tl.reconcile(material_id)
    except Exception as exc:  # noqa: BLE001 — 见上：主旨已完成，异常只作如实报告
        return {"action": "error", "material_id": material_id,
                "why": f"Track L 处理异常：{type(exc).__name__}: {exc}"}


def register(app, json_error):
    from src.core.storage import material_repo as mr

    # ---------------------------------------------------------------- 项目
    @app.post("/api/v1/materials/projects")
    async def materials_create_project(payload: dict):
        body = payload or {}
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            return json_error(422, "materials_bad_request", "缺少 name（项目名）")
        policy = body.get("authority_policy")
        if policy is not None and not isinstance(policy, dict):
            return json_error(422, "materials_bad_request", "authority_policy 必须是对象")
        try:
            proj = mr.create_project(name.strip(), authority_policy=policy,
                                     note=body.get("note"))
        except ValueError as e:
            return json_error(422, "materials_bad_request", str(e))
        except KnowledgeStationError as e:
            return json_error(500, getattr(e, "code", "internal_error"), str(e))
        return {"code": 200, "status": "success", "data": proj}

    @app.get("/api/v1/materials/projects")
    async def materials_list_projects():
        return {"code": 200, "status": "success", "data": mr.list_projects()}

    @app.get("/api/v1/materials/projects/{project_id}/inbox")
    async def materials_inbox(project_id: str):
        """列出**参考资料文件夹**里受支持的文件（用户往这里丢文件，界面照它显示）。"""
        if mr.get_project(project_id) is None:
            return json_error(404, "materials_not_found", f"项目不存在: {project_id}")
        from src.core.ingestion import material_ingest as mi
        files = []
        for p in mi.scan_project_dir(project_id):
            try:
                st = p.stat()
                files.append({"path": str(p), "file_name": p.name, "size": st.st_size})
            except OSError:
                continue
        return {"code": 200, "status": "success",
                "data": {"dir": str(mr.materials_dir(project_id)), "files": files}}

    @app.post("/api/v1/materials/projects/{project_id}/scan")
    def materials_scan(project_id: str, payload: dict | None = None):
        """扫描收件：把文件夹里的文件登记成材料（**默认 pending，未评审不可用**）。

        ⚠ **声明成 `def` 而不是 `async def`**（2026-09-17 修，与 `collect` 同款理由）：
        这个端点会**同步**解析每个 PDF（MinerU 子进程，可能**分钟级**），而 uvicorn 是
        **单事件循环**——`async def` 里做同步重活会把**整个引擎**卡住（连 GUI 的
        "列项目"都要等）。Starlette 对非 async 端点丢进线程池，慢只慢这一个请求。
        （这个坑是自己在写 `collect` 时发现的：同一文件里两种写法并排，
        对读者也是提示——**凡是做同步重活的端点都该是 `def`**。）
        """
        if mr.get_project(project_id) is None:
            return json_error(404, "materials_not_found", f"项目不存在: {project_id}")
        body = payload or {}
        origin = body.get("origin") or "user"
        try:
            from src.core.ingestion import material_ingest as mi
            rows = mi.ingest_project_dir(project_id, origin=origin)
        except ValueError as e:
            return json_error(422, "materials_bad_request", str(e))
        except KnowledgeStationError as e:
            return json_error(500, getattr(e, "code", "internal_error"), str(e))
        ok = [r for r in rows if r.get("status") != "error"]
        return {"code": 200, "status": "success",
                "data": {"scanned": len(rows), "registered": len(ok), "rows": rows}}

    # ---------------------------------------------------------------- 自采（Phase C 接线）
    # ⚠ **这个端点写成 `def` 而不是 `async def`**（本文件其它端点是 async，但**不是**没有先例：
    # `server.data_quality_issues` 也是 `def`）：它会做一次**最长 15 秒的网络抓取**，
    # 而 uvicorn 是**单事件循环**——`async def` 里做同步 I/O 会把**整个引擎**卡住
    # （期间别的请求一起等）。Starlette 对非 async 端点是丢进线程池跑的，
    # 所以"慢"只会慢这一个请求。
    # 代价（诚实说）：线程池每个工作线程会拿一条自己的 SQLite 连接（本仓库是线程局部连接），
    # 所以并发采集时连接数上界 = anyio 线程池大小（默认 40），不是无界。
    # （`materials_scan` 也做同步重活，已在本步一并改成 `def`——见那个端点的说明。）
    @app.post("/api/v1/materials/projects/{project_id}/collect")
    def materials_collect(project_id: str, payload: dict | None = None):
        """按 URL **自采**一份材料（抓取纪律全在 `materials.harvest`，本层只取参数、转错误）。

        **三条契约**：
        1. 抓回来的东西**一律 pending**——登记路径是 `collect.collect_text`，它没有设置
           评审状态的通道（硬门在那一层，本层也无法绕过）；
        2. **不接收 `source_tier`**（给了就 422，不静默忽略）：采集者（模型/脚本）
           **不得自 claim 可信度**——轴 A 由系统判据起（采集默认 T3），要改只能由
           **用户**在界面上改（`/tier`）。静默忽略更坏：调用方会以为自己设上了；
        3. 抓取失败（非 2xx / 非文本 / 空正文 / SSRF 拒绝）**不是 500**：如实回
           `collected:false` + 原因（HTTP 200），与 `scan` 的"逐条结果"同款——
           调用方需要把原因**显示给人看**，而不是收到一个没有内容可展示的错误码。
        """
        if mr.get_project(project_id) is None:
            return json_error(404, "materials_not_found", f"项目不存在: {project_id}")
        body = payload or {}
        if "source_tier" in body:
            return json_error(422, "materials_bad_request",
                              "采集不得自 claim 可信度（不接受 source_tier）——"
                              "轴 A 由系统判据起（采集默认 T3），要改请由用户在界面上改（/tier）")
        url = body.get("url")
        if not isinstance(url, str) or not url.strip():
            return json_error(422, "materials_bad_request", "缺少 url")
        for key in ("title", "note", "published_at"):
            val = body.get(key)
            if val is not None and not isinstance(val, str):
                return json_error(422, "materials_bad_request", f"{key} 必须是字符串或 null")
        try:
            from src.core.materials import harvest as hv
            out = hv.collect_url(project_id, url, title=body.get("title"),
                                 note=body.get("note"),
                                 published_at=body.get("published_at"))
        except ValueError as e:
            return json_error(422, "materials_bad_request", str(e))
        except KnowledgeStationError as e:
            return json_error(500, getattr(e, "code", "internal_error"), str(e))
        return {"code": 200, "status": "success", "data": out}

    # ---------------------------------------------------------------- 材料列表
    @app.get("/api/v1/materials/projects/{project_id}/materials")
    async def materials_list(project_id: str, status: str | None = None):
        """材料列表（**评审视图**：默认全列，含 pending/rejected——否则没法批）。"""
        if mr.get_project(project_id) is None:
            return json_error(404, "materials_not_found", f"项目不存在: {project_id}")
        if status is not None and status not in ("pending", "approved", "rejected"):
            return json_error(422, "materials_bad_request",
                              "status 只能是 pending/approved/rejected")
        rows = mr.list_materials(project_id, review_status=status)
        for r in rows:
            r["chunk_count"] = mr.chunk_count(r["material_id"])
            r["tier_label"] = mr.TIER_LABELS.get(r["source_tier"], r["source_tier"])
        return {"code": 200, "status": "success", "data": rows}

    @app.get("/api/v1/materials/projects/{project_id}/search")
    async def materials_search(project_id: str, q: str = "", limit: int = 8):
        """在**已批准**材料里检索（评审硬门由 `search_materials` 的 SQL 保证）。"""
        if mr.get_project(project_id) is None:
            return json_error(404, "materials_not_found", f"项目不存在: {project_id}")
        try:
            lim = max(1, min(int(limit), 50))
        except (TypeError, ValueError):
            return json_error(422, "materials_bad_request", "limit 必须是整数")
        hits = mr.search_materials(project_id, q, limit=lim)
        return {"code": 200, "status": "success",
                "data": {"query": q, "hits": hits, "count": len(hits)}}

    # ---------------------------------------------------------------- 层级定义
    # ⚠ 必须注册在 `/api/v1/materials/{material_id}` **之前**：FastAPI 按注册顺序匹配，
    # 否则字面量路径 `tiers` 会被 `{material_id}` 捕获（表现是"取 tiers 却得到 404 材料不存在"）。
    # 被自己的 API 测试抓到过（`test_tiers_endpoint_lists_all`）。
    @app.get("/api/v1/materials/tiers")
    async def materials_tiers():
        """层级定义（给 UI 直接用，避免前端再抄一份措辞）。"""
        return {"code": 200, "status": "success",
                "data": [{"tier": t, "label": mr.TIER_LABELS[t]} for t in mr.TIERS]}

    # ---------------------------------------------------------------- 单份材料
    @app.get("/api/v1/materials/{material_id}")
    async def materials_get(material_id: str):
        m = mr.get_material(material_id)
        if m is None:
            return json_error(404, "materials_not_found", f"材料不存在: {material_id}")
        m["chunk_count"] = mr.chunk_count(material_id)
        m["tier_label"] = mr.TIER_LABELS.get(m["source_tier"], m["source_tier"])
        m["dir"] = str(mr.materials_dir(m["project_id"]))
        return {"code": 200, "status": "success", "data": m}

    @app.get("/api/v1/materials/{material_id}/chunks")
    async def materials_chunks(material_id: str, offset: int = 0, limit: int = 50):
        """切片分页——**评审时必须能读到内容**（否则"批准"是盲签）。"""
        if mr.get_material(material_id) is None:
            return json_error(404, "materials_not_found", f"材料不存在: {material_id}")
        try:
            off = max(0, int(offset))
            lim = max(1, min(int(limit), 500))
        except (TypeError, ValueError):
            return json_error(422, "materials_bad_request", "offset/limit 必须是整数")
        all_chunks = mr.material_chunks(material_id)
        return {"code": 200, "status": "success",
                "data": {"total": len(all_chunks), "offset": off,
                         "chunks": all_chunks[off:off + lim]}}

    @app.post("/api/v1/materials/{material_id}/review")
    def materials_review(material_id: str, payload: dict):
        """批准/拒绝。这是**硬门的开关**：批准之后该材料才可能被检索到。

        ⚠ **批准会触发 Track L**（业主裁定 J5：采到库内没有的法规标准 → **评审通过后自动
        入库**）。三条纪律：
        1. **只有 `approved` 触发**（`rejected`/`pending` 一律不碰法条链）；
        2. Track L 的失败**不改写评审结果**（批准是用户对**材料**的判断，入库是它的**后果**）
           ——但必须出现在返回体的 `data.track_l` 里，**绝不静默**；
        3. 端点是 `def`（入库要写库、可能秒级；见 `collect` 端点关于单事件循环的说明）。
        """
        body = payload or {}
        status = body.get("status")
        if status not in ("pending", "approved", "rejected"):
            return json_error(422, "materials_bad_request",
                              "status 只能是 pending/approved/rejected")
        note = body.get("note")
        try:
            ok = mr.set_review(material_id, status, note=note)
        except ValueError as e:
            return json_error(422, "materials_bad_request", str(e))
        if not ok:
            return json_error(404, "materials_not_found", f"材料不存在: {material_id}")
        row = mr.get_material(material_id)
        if row is not None and status == "approved":
            outcome = _run_track_l(material_id)
            # ⚠ **必须重读**：Track L 成功后 `link_doc` 会写 `material.doc_id`，
            # 而上面那次读取发生在它之前——不重读就会把"已回指"显示成 `doc_id: null`
            # （本步的测试当场抓到了这个：入库成功、返回体却说自己没关联）。
            row = dict(mr.get_material(material_id) or row)
            # 放进 `data` **里面**（不是顶层）：主机侧 `mapProbe` 只转发 `body.data`，
            # 顶层字段会被**静默丢掉**（那是本战役反复打的"算了但看不见"的坑）。
            row["track_l"] = outcome
        return {"code": 200, "status": "success", "data": row}

    @app.post("/api/v1/materials/{material_id}/tier")
    async def materials_set_tier(material_id: str, payload: dict):
        """改**来源可信度**（轴 A）。业主明说用户可以改；`source='user'` 会留痕。"""
        body = payload or {}
        tier = body.get("tier")
        if not isinstance(tier, str):
            return json_error(422, "materials_bad_request", "缺少 tier（T0~T4）")
        try:
            ok = mr.set_tier(material_id, tier, source=str(body.get("source") or "user"),
                             reason=body.get("reason"))
        except ValueError as e:
            return json_error(422, "materials_bad_request", str(e))
        if not ok:
            return json_error(404, "materials_not_found", f"材料不存在: {material_id}")
        return {"code": 200, "status": "success", "data": mr.get_material(material_id)}

    @app.post("/api/v1/materials/{material_id}/role")
    async def materials_set_role(material_id: str, payload: dict):
        """声明**任务内效力**（轴 B）：criterion=本任务准则 / reference=参考 / null=撤销。"""
        body = payload or {}
        role = body.get("role")
        try:
            ok = mr.set_task_role(material_id, role)
        except ValueError as e:
            return json_error(422, "materials_bad_request", str(e))
        if not ok:
            return json_error(404, "materials_not_found", f"材料不存在: {material_id}")
        return {"code": 200, "status": "success", "data": mr.get_material(material_id)}

    @app.post("/api/v1/materials/{material_id}/lifecycle")
    async def materials_set_lifecycle(material_id: str, payload: dict):
        """`ephemeral`（默认，仅本次任务）↔ `promoted`（升为长期参考）。"""
        body = payload or {}
        try:
            ok = mr.set_lifecycle(material_id, str(body.get("lifecycle") or ""))
        except ValueError as e:
            return json_error(422, "materials_bad_request", str(e))
        if not ok:
            return json_error(404, "materials_not_found", f"材料不存在: {material_id}")
        return {"code": 200, "status": "success", "data": mr.get_material(material_id)}

    @app.delete("/api/v1/materials/{material_id}")
    async def materials_delete(material_id: str):
        if not mr.delete_material(material_id):
            return json_error(404, "materials_not_found", f"材料不存在: {material_id}")
        return {"code": 200, "status": "success", "data": {"deleted": material_id}}
