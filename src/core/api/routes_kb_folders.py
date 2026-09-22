"""知识库多级目录 API 路由（KB-FOLDER-PLAN §五第 2 步：**接口接通**）。

方案真源：``docs/KB-FOLDER-PLAN.md``。数据层在 ``src.core.knowledge.folder_store``
（第 1 步落地），本文件**只做 HTTP 外形**：入参校验、错误码映射、包装格式。

════════ 为什么单独一个文件、不塞进 server.py ════════

仓库既有风格是"一族端点一个 ``routes_*.py`` + ``register(app, json_error)``"
（``routes_law`` / ``routes_materials`` / ``routes_settings`` / …）。本族 13 条端点
自成一体（KB 目录的增删改查 + 待分类 + 范围），照那个风格单独成文件。

════════ 与收藏夹（``/api/v1/bookmark-folders``）的关系 ════════

**无关**（契约增量 33~35 号已写明）：那是单层收藏夹、``folder_id`` 前缀 ``bmf_``；
本族是无限层级知识库目录、前缀 ``fld_``，两张表各自表内引用，**任何查询不得跨表 join**。
路径也不同（``/kb/...`` vs ``/bookmark-folders``），不存在路由冲突。

════════ 端点声明成 ``def``（不是 ``async def``）════════

与仓库纪律一致（§10.86/§10.93）：这些端点全是**同步 SQLite 读写**（部分还要排序整层、
算子树计数），零有效 ``await`` ⇒ 必须 ``def``，让 FastAPI 把它们放进**有界的**
anyio 线程池（``THREADPOOL_TOKENS=16``），别占事件循环。
⚠ 也没有一条落进 ``HEAVY_PREFIXES``（那是给"解析 PDF / 渲染 / 逐点 LLM / 打整包"的）：
本族最重的一条是"列一层 + 算子树计数"，在 1127 个目录的真库上是毫秒级。

════════ 分页口径（本族统一，写进契约）════════

* 目录列表 ``GET /api/v1/kb/folders``：``?parent_id=``（**省略或空 = 顶层**）、
  ``limit``（默认 200，上限 500）、``offset``（默认 0）。
* 文件列表 ``.../items`` 与 ``/kb/inbox``：``limit``（默认 **50**）、``offset``。
⚠ 参数名一律 ``limit``/``offset``（**不叫** ``page_size``/``page``），与
``/materials/*`` 那一族一致；``folder_store`` 内部的 ``file_limit``/``file_offset``
在本文件里统一映射成 ``limit``/``offset``。
"""
from __future__ import annotations

import logging

from fastapi import Request

logger = logging.getLogger("ks.api.kb_folders")

#: 一页最多几个目录（真库最宽的一层 206 个 ⇒ 500 有充裕余量）
MAX_FOLDER_PAGE = 500
#: 一页最多几篇文件
MAX_FILE_PAGE = 200

#: 元数据字段的错误码 → HTTP 状态码（与 ``/bookmark-folders`` 同口径）
_STATUS = {
    "folder_not_found": 404,
    "doc_not_found": 404,
    "folder_name_conflict": 409,
    "folder_not_in_parent": 409,
    "folder_delete_mode_required": 409,
    "folder_top_level_no_parent": 409,
    "folder_cycle": 422,
    "invalid_folder_name": 422,
    "invalid_item_kind": 422,
    "invalid_delete_mode": 422,
    "invalid_pagination": 422,
    "invalid_stage": 422,
    "invalid_state_field": 422,
    "invalid_scope": 422,
    "invalid_decision": 422,
    "no_suggestion": 422,
    "folder_depth_exceeded": 422,
    "invalid_folder_key": 422,
    # 「补全分类号」（2026-09-22）：批次在跑 ⇒ 409（**不排队**，与 reingest 同口径）
    "ccs_backfill_busy": 409,
    "invalid_ccs_outcome": 422,
    "invalid_ccs_tag": 422,
}


def register(app, json_error) -> None:
    from src.core.exceptions import KnowledgeStationError
    from src.core.knowledge import folder_store as fs

    def _fail(e: KnowledgeStationError):
        return json_error(_STATUS.get(e.code, 422), e.code, str(e))

    def _int(raw, default: int) -> int:
        try:
            return int(str(raw)) if raw not in (None, "") else default
        except (TypeError, ValueError):
            raise KnowledgeStationError(f"必须是整数，收到 {raw!r}", code="invalid_pagination")

    def _body(payload) -> dict:
        if not isinstance(payload, dict):
            raise KnowledgeStationError("请求体必须是一个 JSON 对象", code="invalid_decision")
        return payload

    def _items(payload) -> list[dict]:
        """批量端点共用的 ``items`` 解析（必须是非空数组，每项要有 kind+id）。"""
        body = _body(payload)
        raw = body.get("items")
        if not isinstance(raw, list) or not raw:
            raise KnowledgeStationError("items 必须是非空数组", code="invalid_decision")
        out: list[dict] = []
        for i, it in enumerate(raw):
            if not isinstance(it, dict):
                raise KnowledgeStationError(f"items[{i}] 必须是对象", code="invalid_decision")
            kind = str(it.get("kind") or "")
            item_id = str(it.get("id") or "")
            if kind not in fs.ITEM_KINDS or not item_id:
                raise KnowledgeStationError(
                    f"items[{i}] 需要 kind ∈ {list(fs.ITEM_KINDS)} 与非空 id",
                    code="invalid_decision")
            out.append({"kind": kind, "id": item_id})
        return out

    # ═════════════════════════ 列某一级 / 某一级的文件 ═════════════════════════

    @app.get("/api/v1/kb/folders")
    def kb_list_folders(request: Request):
        """列**某一级**的下级目录（含"更深层的文件数"）+ 面包屑。

        ``?parent_id=`` 省略/空 = 库的顶层。返回 ``data``：``folder``（本级；
        顶层为 null）、``breadcrumb``（从顶层到本级）、``subfolders``（每个带
        ``file_count_direct`` / ``file_count_deep`` / ``folder_count_deep``）、
        ``total`` / ``offset`` / ``limit`` / ``has_more``。**空目录 ⇒ ``subfolders: []``**。
        """
        qp = request.query_params
        try:
            parent_id = str(qp.get("parent_id") or "") or None
            limit = _int(qp.get("limit"), 200)
            offset = _int(qp.get("offset"), 0)
            if limit <= 0 or limit > MAX_FOLDER_PAGE:
                raise KnowledgeStationError(f"limit 必须在 1~{MAX_FOLDER_PAGE}",
                                            code="invalid_pagination")
            if offset < 0:
                raise KnowledgeStationError("offset 不能为负", code="invalid_pagination")
            info = fs.list_folder(parent_id, file_limit=1, unfiled=False)
        except KnowledgeStationError as e:
            return _fail(e)
        subs = info["subfolders"]
        return {"code": 200, "status": "success", "data": {
            "folder": info["folder"], "breadcrumb": info["breadcrumb"],
            "subfolders": subs[offset:offset + limit],
            "total": len(subs), "offset": offset, "limit": limit,
            "has_more": offset + limit < len(subs)}}

    @app.get("/api/v1/kb/folders/flat")
    def kb_flat_folders(request: Request):
        """**整棵目录树的扁平清单**（每行带显示路径）—— 「放进哪个目录」的选择器用。

        ``?q=``（名字/路径大小写不敏感包含）、``limit``（默认 0 = 不限）、``offset``。
        返回 ``data.{items:[{folder_id,parent_id,name,path,depth}],total,sep}``。
        ⚠ 真库 **1127 个目录**时整棵树约 **80KB** —— 与方案 §七那条"不许一次把整库
        **文件**元数据（~9.7MB）发给页面"的红线不同量级：那条管的是文件列表。
        选择器要的是"按名字找"，一层层点四层在 1127 个目录上不可用。
        """
        qp = request.query_params
        try:
            limit = _int(qp.get("limit"), 0)
            offset = _int(qp.get("offset"), 0)
            if limit < 0 or limit > MAX_FOLDER_PAGE * 20:
                raise KnowledgeStationError(f"limit 必须在 0~{MAX_FOLDER_PAGE * 20}"
                                            "（0 = 不限）", code="invalid_pagination")
            if offset < 0:
                raise KnowledgeStationError("offset 不能为负", code="invalid_pagination")
            data = fs.list_all_folders(q=str(qp.get("q") or ""), limit=limit, offset=offset)
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": data}

    @app.get("/api/v1/kb/folders/{folder_id}/items")
    def kb_folder_items(folder_id: str, request: Request):
        """这一级**直接**放的文件（**不含**下级目录里的），分页（默认 50）。

        顶层（``folder_id='root'``）给的是"还没进任何目录"的文件。返回
        ``items`` / ``total`` / ``offset`` / ``limit`` / ``has_more``。
        ⚠ 空目录 ⇒ ``items: []``、``total: 0``（**不是 404**）。目录不存在 ⇒ 404。
        """
        qp = request.query_params
        try:
            limit = _int(qp.get("limit"), 50)
            offset = _int(qp.get("offset"), 0)
            if limit <= 0 or limit > MAX_FILE_PAGE:
                raise KnowledgeStationError(f"limit 必须在 1~{MAX_FILE_PAGE}",
                                            code="invalid_pagination")
            if offset < 0:
                raise KnowledgeStationError("offset 不能为负", code="invalid_pagination")
            fid = None if folder_id in ("root", "null") else folder_id
            info = fs.list_folder(fid, file_offset=offset, file_limit=limit)
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": {
            "folder": info["folder"], "breadcrumb": info["breadcrumb"],
            "items": info["files"], "total": info["files_total"],
            "offset": info["file_offset"], "limit": info["file_limit"],
            "has_more": info["has_more"]}}

    # ═════════════════════════ 建 / 改名 / 挪 / 复制 / 删 ═════════════════════════

    @app.post("/api/v1/kb/folders")
    def kb_create_folder(payload: dict | None = None):
        """建目录 ``{parent_id, name}``（``parent_id`` 省略/null = 顶层）。

        同名同层拒绝（含根层）⇒ 409；空名/超长 ⇒ 422；上级不存在 ⇒ 404。
        ⚠ **不限制顶层名字**：四个预建顶层（标准/法律法规/公司制度/待分类）只是
        ``scripts/apply-folder-filing.py`` 初次归位时建的，用户之后再加顶层目录是
        合法操作（那个脚本判"是否已归位"看的是**它自己那棵树**，不看根层有几个）。
        """
        try:
            body = _body(payload)
            parent_id = body.get("parent_id")
            parent_id = None if parent_id in (None, "", "root") else str(parent_id)
            name = str(body.get("name") or "").strip()
            data = fs.create_folder(name, parent_id, sort=int(body.get("sort") or 0))
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": data}

    @app.put("/api/v1/kb/folders/{folder_id}")
    def kb_rename_folder(folder_id: str, payload: dict | None = None):
        """改目录名 ``{name}`` —— **只改库里的名字，绝不动磁盘文件**（方案 §二第 1 条）。"""
        try:
            body = _body(payload)
            data = fs.rename_folder(folder_id, str(body.get("name") or ""))
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": data}

    @app.post("/api/v1/kb/folders/{folder_id}/move")
    def kb_move_folder(folder_id: str, payload: dict | None = None):
        """挪目录 ``{from_parent_id, to_parent_id}``（按"从哪一处 → 到哪一处"）。

        ``from_parent_id`` 省略 ⇒ 取当前主位置（= "把这个目录挪到别处"）；
        ``to_parent_id`` 为 null ⇒ **真的挪到顶层**（``parent_id`` 置 NULL —— 库里
        "在顶层"的判定口径就是它，见 ``folder_store`` 模块开头；同时删掉源边与旧主位置
        那条边，所以它**在顶层目录列表里出现、旧父目录里不再有它**）。
        把一个"同时挂在两处的目录"从一个**目录**挪到另一个**目录**：补新边（挪到哪儿
        就在哪儿出现），但**不动** ``parent_id``（不会把"主位置"悄悄改掉；
        第 2 步修准 + 2026-09-21 复核裁定的口径）。
        """
        try:
            body = _body(payload)
            frm = body.get("from_parent_id")
            to = body.get("to_parent_id")
            data = fs.move_folder(
                folder_id,
                None if to in (None, "", "root") else str(to),
                from_parent_id=None if frm in (None, "", "root") else str(frm))
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": data}

    @app.post("/api/v1/kb/folders/{folder_id}/copy")
    def kb_copy_folder(folder_id: str, payload: dict | None = None):
        """复制目录到 ``{to_parent_id, name?}`` —— 新目录**共享成员**（同一批
        ``item_id``），**不拷文件、不拷下级目录的副本**（方案 §三复制语义）。"""
        try:
            body = _body(payload)
            to = body.get("to_parent_id")
            data = fs.copy_folder(
                folder_id,
                None if to in (None, "", "root") else str(to),
                new_name=(str(body["name"]) if body.get("name") else None))
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": data}

    @app.get("/api/v1/kb/folders/{folder_id}/delete-preview")
    def kb_describe_delete(folder_id: str):
        """删目录**前**"先问一句"要的数字（只读；界面照这些数字问业主）。

        ``reparent_available=False`` ⇔ 一级目录（没有上一层 ⇒ 只给 purge 与取消）。
        """
        try:
            data = fs.describe_folder_delete(folder_id)
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": data}

    @app.delete("/api/v1/kb/folders/{folder_id}")
    def kb_delete_folder(folder_id: str, request: Request):
        """删目录 ``?mode=reparent|purge``。

        * 空目录 ⇒ **直接删**（``mode`` 可省；返回 ``mode='empty'``）。
        * 非空 + 不给 ``mode`` ⇒ 409 ``folder_delete_mode_required``（**不替调用方选**）。
        * 一级目录 + ``reparent`` ⇒ 409 ``folder_top_level_no_parent``（**不静默降级**）。
        * ``purge`` ⇒ 只有"在**所有**目录里都不再出现"的文件才真删；还挂在别处的只丢归属。
        """
        qp = request.query_params
        mode = str(qp.get("mode") or "") or None
        try:
            data = fs.delete_folder(folder_id, mode=mode)
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": data}

    # ═════════════════════════ 成员：批量加 / 拿掉 / 挪 / 复制 ═════════════════════════

    @app.post("/api/v1/kb/members")
    def kb_add_members(payload: dict | None = None):
        """批量加成员 ``{folder_id, items:[{kind,id}]}``（上传后落位用）。

        已经在该目录里的**幂等跳过**（返回 ``skipped``，不报错、不加重复行）。
        """
        try:
            body = _body(payload)
            folder_id = str(body.get("folder_id") or "")
            if not folder_id:
                raise KnowledgeStationError("缺少 folder_id", code="invalid_decision")
            items = _items(payload)
            added = skipped = 0
            for it in items:
                if fs.add_member(folder_id, it["kind"], it["id"])["added"]:
                    added += 1
                else:
                    skipped += 1
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": {
            "folder_id": folder_id, "added": added, "skipped": skipped,
            "total": len(items)}}

    @app.post("/api/v1/kb/members/remove")
    def kb_remove_members(payload: dict | None = None):
        """从**这一处**拿掉 ``{folder_id, items}`` —— 只删归属行，**不删文件**。"""
        try:
            body = _body(payload)
            folder_id = str(body.get("folder_id") or "")
            if not folder_id:
                raise KnowledgeStationError("缺少 folder_id", code="invalid_decision")
            items = _items(payload)
            removed = 0
            for it in items:
                if fs.remove_member(folder_id, it["kind"], it["id"])["removed"]:
                    removed += 1
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": {
            "folder_id": folder_id, "removed": removed, "total": len(items)}}

    @app.post("/api/v1/kb/members/move")
    def kb_move_members(payload: dict | None = None):
        """批量挪 ``{items, from_folder_id, to_folder_id}``（同一事务，逐条搬）。"""
        try:
            body = _body(payload)
            frm = str(body.get("from_folder_id") or "")
            to = str(body.get("to_folder_id") or "")
            if not frm or not to:
                raise KnowledgeStationError("缺少 from_folder_id / to_folder_id",
                                            code="invalid_decision")
            items = _items(payload)
            moved = 0
            for it in items:
                fs.move_member(it["kind"], it["id"], frm, to)
                moved += 1
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": {
            "from_folder_id": frm, "to_folder_id": to, "moved": moved,
            "total": len(items)}}

    @app.post("/api/v1/kb/members/copy")
    def kb_copy_members(payload: dict | None = None):
        """批量复制 ``{items, to_folder_id}``（**多一处位置**，不是多一份文件）。"""
        try:
            body = _body(payload)
            to = str(body.get("to_folder_id") or "")
            if not to:
                raise KnowledgeStationError("缺少 to_folder_id", code="invalid_decision")
            items = _items(payload)
            added = skipped = 0
            for it in items:
                if fs.copy_member(it["kind"], it["id"], to)["added"]:
                    added += 1
                else:
                    skipped += 1
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": {
            "to_folder_id": to, "added": added, "skipped": skipped,
            "total": len(items)}}

    # ═════════════════════════ 「待分类」 ═════════════════════════

    @app.get("/api/v1/kb/inbox")
    def kb_inbox(request: Request):
        """「待分类」列表：**还没归位**的文件，每篇带
        ``stage`` / ``confidence`` / ``failure_kind`` / ``suggested_folder_id`` /
        ``suggested_path`` / ``suggest_new_parent_id`` / ``suggest_new_name`` /
        ``catalog_hidden``。

        ``suggested_folder_id`` 是**现算的**（库里存的建议优先，否则按现有分类口径
        在**已有目录**里找最近的一层）——**只匹配现有目录，绝不自行新建**。
        ``suggest_new_parent_id`` / ``suggest_new_name``（第 4 步补）是"该新建什么目录"的
        那两个真值：分类口径算出来的落点**比命中的现有目录更深**时，缺的那一段就是新目录名。
        两个都是 null 时，界面上**不许**渲染「接受建议 / 在建议位置新建」这类按钮
        （兜底桶那 379 篇就是这样：按下去会 422 ``no_suggestion``）。
        ``catalog_hidden`` 表示这篇**不在目录里**（正文条款为零 ⇒ pipeline 的目录卫生）
        —— 它照样出现在这里（识别失败的那一批必须能被看到，否则修不了）。

        ⚠ **2026-09-22 补**：每篇再带分类号查询的底细，因为"没有建议"有两种完全不同的
        原因，界面必须能说清是哪一种（业主口径「**界面把原因说清**」）：
        ``ccs_tag``（已经有了的分类号，null = 没有）/ ``ccs_outcome``（
        found|not_found|network_failed|parse_failed，null = **还没查过**）/
        ``ccs_outcome_label`` / ``ccs_reason``（一句人话）/ ``ccs_source``
        （命中的是哪一层）/ ``ccs_checked_at``。这几个字段来自
        ``doc_ccs_state``（``ccs_store``），**不是**在这里现编的。
        """
        qp = request.query_params
        try:
            limit = _int(qp.get("limit"), 50)
            offset = _int(qp.get("offset"), 0)
            if limit <= 0 or limit > MAX_FILE_PAGE:
                raise KnowledgeStationError(f"limit 必须在 1~{MAX_FILE_PAGE}",
                                            code="invalid_pagination")
            if offset < 0:
                raise KnowledgeStationError("offset 不能为负", code="invalid_pagination")
            page = fs.list_pending_filing(offset=offset, limit=limit)
        except KnowledgeStationError as e:
            return _fail(e)
        from src.core.knowledge import ccs_store
        from src.core.knowledge.ccs_fetcher import OUTCOME_LABELS
        index = fs.folder_tree_index()
        states = ccs_store.ccs_states_for([r["doc_id"] for r in page["items"]])
        items = []
        for row in page["items"]:
            sug = fs.suggest_folder_for_doc(row, index=index)
            tag = ccs_store.ccs_tag_of(row.get("domain_tags"))
            st = states.get(row["doc_id"]) or {}
            items.append({
                "doc_id": row["doc_id"],
                "standard_no": row.get("standard_no"),
                "standard_name": row.get("standard_name"),
                "stage": row.get("stage"),
                "stage_label": fs.STAGE_LABELS.get(str(row.get("stage") or ""), ""),
                "confidence": row.get("confidence"),
                "failure_kind": row.get("failure_kind"),
                "suggested_folder_id": (sug or {}).get("folder_id"),
                "suggested_path": (sug or {}).get("path"),
                "suggest_new_parent_id": (sug or {}).get("suggest_new_parent_id"),
                "suggest_new_name": (sug or {}).get("suggest_new_name"),
                "suggest_new_path": row.get("suggest_new_path"),
                "catalog_hidden": row.get("catalog_hidden"),
                # ── 分类号这条线的底细（见 docstring）──
                "ccs_tag": tag,
                "ccs_outcome": st.get("outcome"),
                "ccs_outcome_label": OUTCOME_LABELS.get(str(st.get("outcome") or ""), None),
                "ccs_reason": st.get("reason"),
                "ccs_source": st.get("source"),
                "ccs_checked_at": st.get("checked_at"),
            })
        return {"code": 200, "status": "success", "data": {
            "items": items, "total": page["total"], "offset": page["offset"],
            "limit": page["limit"],
            "has_more": page["offset"] + len(items) < page["total"]}}

    @app.get("/api/v1/kb/stage-labels")
    def kb_stage_labels():
        """处理状态五枚举的**中文标签**（``folder_store.STAGE_LABELS`` 是唯一所有者）。

        ⚠ 为什么要这个端点（2026-09-21 第 4 步）：以前界面里**抄了一份**镜像
        （``KsKnowledgePage.tsx`` 的 ``STAGE_LABELS``）⇒ 后端改了档位文字、界面不跟着变，
        而且没有任何东西会响。现在标签**由接口下发**，界面只兜底。
        """
        return {"code": 200, "status": "success", "data": {
            "labels": dict(fs.STAGE_LABELS), "stages": list(fs.STAGES),
            "unfiled": list(fs.UNFILED_STAGES)}}

    @app.post("/api/v1/kb/inbox/reingest")
    def kb_inbox_reingest(payload: dict | None = None):
        """**重来一次**：把这几篇**已经在库里**的文件重新解析（``{doc_ids:[…]}``）。

        沿用既有的 ``run_full_ingest(..., reingest=True)``（不另写一套解析）；真解析
        要几十秒到几十分钟 ⇒ 起后台线程、**立刻**返回
        ``{queued, started:[…], skipped:[{doc_id,reason}]}``。进度看每一篇的
        ``doc_filing_state.stage``（``recognizing`` → ``confirming`` / ``failed``），
        ``GET /kb/inbox/reingest/status`` 给最近一批的逐篇结果。
        同一时刻只跑一批 ⇒ 已有批次在跑回 **409 ``reingest_busy``**。
        """
        from src.core.ingestion import reingest as reingest_mod
        try:
            body = _body(payload)
            raw = body.get("doc_ids")
            if isinstance(raw, str):
                raw = [raw]
            if not isinstance(raw, list) or not raw:
                raise KnowledgeStationError("doc_ids 必须是非空数组",
                                            code="invalid_decision")
            ids = [str(x) for x in raw if str(x).strip()]
            data = reingest_mod.start_reingest(ids)
        except KnowledgeStationError as e:
            return _fail(e)
        except ValueError as e:
            return json_error(422, "invalid_decision", str(e))
        except RuntimeError as e:
            if "reingest_busy" in str(e):
                return json_error(409, "reingest_busy",
                                  "已经有一批「重来一次」在跑；等它跑完再点（不许排队等）")
            raise
        return {"code": 200, "status": "success", "data": data}

    @app.get("/api/v1/kb/inbox/reingest/status")
    def kb_inbox_reingest_status():
        """最近一批「重来一次」的进度（**如实**：running/total/done + 逐篇结果）。"""
        from src.core.ingestion import reingest as reingest_mod
        return {"code": 200, "status": "success", "data": reingest_mod.reingest_status()}

    # ═════════════════════════ 「补全分类号」（自愈机制） ═════════════════════════
    #
    # 业主 2026-09-22 口径：「这 380 篇**不要手动去补**……你要找的是**修机制**，然后让插件
    # **自己能靠自己的机制完成工作**。」⇒ 这一族端点就是那个"机制"，界面上的按钮调它。
    # 形状与「重来一次」同款（起后台线程、立刻返回、进度另查、同一时刻只跑一批），
    # 但**不共用**那把锁：查分类号（几秒一篇）与重新解析（几十分钟一篇）该能各自跑。

    @app.get("/api/v1/kb/ccs/summary")
    def kb_ccs_summary():
        """分类号这件事的**现状**：还缺几篇 + 台账里各结论各几篇（只读，零网络）。

        返回 ``data``：``missing``（全库 ``doc_type='standard'`` 且 ``domain_tags`` 里
        没有 ``CCS:`` 的篇数——**现算的**，不是计数器）、``by_outcome``（台账按结论计数）、
        ``backfill``（最近一批进度，见 ``/kb/ccs/backfill/status``）、
        ``outcome_labels`` / ``source_labels``（中文说法，由后端下发，界面只兜底）。
        """
        from src.core.knowledge import ccs_backfill as bf
        from src.core.knowledge import ccs_store
        from src.core.knowledge.ccs_fetcher import (OUTCOME_LABELS, SOURCE_LABELS,
                                                    SOURCES)
        return {"code": 200, "status": "success", "data": {
            "missing": bf.missing_ccs_count(),
            "by_outcome": ccs_store.counts_by_outcome(),
            "max_batch": bf.MAX_BACKFILL_DOCS,
            "default_batch": bf.DEFAULT_BACKFILL_DOCS,
            "outcome_labels": dict(OUTCOME_LABELS),
            "source_labels": dict(SOURCE_LABELS),
            "sources": list(SOURCES),
            "backfill": bf.ccs_backfill_status()}}

    @app.get("/api/v1/kb/ccs/plan")
    def kb_ccs_plan(request: Request):
        """**只读预览**：这一批会补哪些篇（不写库、不联网、不起线程）。

        ``?limit=``（0 = 不限，默认 0）、``?force=``（true = 连已经有分类号的也重查）。
        返回 ``data.{candidates:[{doc_id,standard_no,standard_name}], total, already_have,
        limit, truncated}`` —— 「补全分类号」按下去之前先看这个。
        """
        from src.core.knowledge import ccs_backfill as bf
        qp = request.query_params
        try:
            limit = _int(qp.get("limit"), 0)
            force = str(qp.get("force") or "").lower() in ("1", "true", "yes")
            data = bf.plan_ccs_backfill(limit=limit, force=force)
        except ValueError as e:
            return json_error(422, "invalid_pagination", str(e))
        return {"code": 200, "status": "success", "data": data}

    @app.post("/api/v1/kb/ccs/backfill")
    def kb_ccs_backfill(payload: dict | None = None):
        """**补全分类号**：扫出没有分类号的标准，用三层链逐篇补（后台跑，立刻返回）。

        body（都可省）：``{doc_ids?: [...], limit?: 50, force?: false}``。
        返回 ``data.{queued, started:[…], skipped:[…], plan:{…}}``；进度看
        ``/kb/ccs/backfill/status``。同一时刻只跑一批 ⇒ 已有批次在跑回 **409
        ``ccs_backfill_busy``**（**不排队**）。
        """
        from src.core.knowledge import ccs_backfill as bf
        try:
            body = payload if isinstance(payload, dict) else {}
            raw = body.get("doc_ids")
            ids = None
            if raw is not None:
                if isinstance(raw, str):
                    raw = [raw]
                if not isinstance(raw, list):
                    raise KnowledgeStationError("doc_ids 必须是数组", code="invalid_decision")
                ids = [str(x) for x in raw if str(x).strip()]
                if not ids:
                    raise KnowledgeStationError("doc_ids 不能是空数组",
                                                code="invalid_decision")
            limit = _int(body.get("limit"), bf.DEFAULT_BACKFILL_DOCS)
            if limit <= 0 or limit > bf.MAX_BACKFILL_DOCS:
                raise KnowledgeStationError(
                    f"limit 必须在 1~{bf.MAX_BACKFILL_DOCS}", code="invalid_pagination")
            force = bool(body.get("force"))
            data = bf.start_ccs_backfill(doc_ids=ids, limit=limit, force=force)
        except KnowledgeStationError as e:
            return _fail(e)
        except ValueError as e:
            return json_error(422, "invalid_decision", str(e))
        except RuntimeError as e:
            if "ccs_backfill_busy" in str(e):
                return json_error(409, "ccs_backfill_busy",
                                  "已经有一批「补全分类号」在跑；等它跑完再点（不许排队等）")
            raise
        return {"code": 200, "status": "success", "data": data}

    @app.get("/api/v1/kb/ccs/backfill/status")
    def kb_ccs_backfill_status():
        """最近一批「补全分类号」的进度（**如实**：running/done/total + 逐篇结果 + 失败清单）。

        ``failures`` 是**没补到的那一批**（每篇带 ``outcome`` 与 ``reason``）——
        业主/审计靠它看"还剩哪些、为什么"；``missing`` 是现算的"全库还缺几篇"。
        """
        from src.core.knowledge import ccs_backfill as bf
        return {"code": 200, "status": "success", "data": bf.ccs_backfill_status()}

    @app.post("/api/v1/kb/ccs/backfill/cancel")
    def kb_ccs_backfill_cancel():
        """按「停」：本批**跑完当前这一篇就停**，已补好的不丢。

        返回 ``{cancel_requested, running, done, total}`` —— 还没真停时 ``running`` 仍是
        true，界面**不许**在这一刻显示"已停止"。
        """
        from src.core.knowledge import ccs_backfill as bf
        return {"code": 200, "status": "success", "data": bf.cancel_ccs_backfill()}

    @app.post("/api/v1/kb/inbox/confirm")
    def kb_inbox_confirm(payload: dict | None = None):
        """批量确认归位 ``{decisions:[{doc_id, action, target_folder_id?,
        new_parent_id?, new_name?}]}``，``action`` ∈ ``accept|existing|new``。

        ``new`` 会在指定父目录下**新建**再放进去（业主那句「将在 XXX 目录下新建 XXX
        文件夹存放此文件」）；确认后 ``stage='filed'`` **并自动挪出「待分类」**。
        **一个事务**：整批全成或全败。
        """
        try:
            body = _body(payload)
            decisions = body.get("decisions")
            if not isinstance(decisions, list) or not decisions:
                raise KnowledgeStationError("decisions 必须是非空数组",
                                            code="invalid_decision")
            data = fs.confirm_inbox_decisions(decisions)
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": data}

    # ═════════════════════════ 范围集合（范围提问用） ═════════════════════════

    @app.post("/api/v1/kb/scope/resolve")
    def kb_scope_resolve(payload: dict | None = None):
        """``{folder_ids:[]}`` ⇒ "这些目录**及其所有下级**"的集合 + 命中文件数。

        返回 ``folder_ids`` / ``doc_ids``（**已排序**，去重：一个文件挂多处只算一次）
        与 ``folder_count`` / ``doc_count``。**任一目录不存在 ⇒ 404**（绝不静默返回
        空范围 —— 空范围会让"在此范围内提问"悄悄变成全库提问）。
        """
        try:
            body = _body(payload)
            roots = body.get("folder_ids")
            if isinstance(roots, str):
                roots = [roots]
            if not isinstance(roots, list) or not roots:
                raise KnowledgeStationError("folder_ids 必须是非空数组",
                                            code="invalid_scope")
            scope = fs.folder_scope([str(r) for r in roots])
        except KnowledgeStationError as e:
            return _fail(e)
        return {"code": 200, "status": "success", "data": {
            "folder_ids": sorted(scope["folder_ids"]),
            "doc_ids": sorted(scope["doc_ids"]),
            "folder_count": len(scope["folder_ids"]),
            "doc_count": len(scope["doc_ids"]),
            "roots": scope["roots"]}}
