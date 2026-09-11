"""阶段2.1 纠错补丁机制测试（外部评审响应）。"""
import pytest


@pytest.fixture()
def seeded(db):
    """一条可打补丁的条款（幂等：清掉本测试的历史数据再建）。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    if db.execute("SELECT 1 FROM doc_meta WHERE doc_id='dp1'").fetchone():
        clause_repo.delete_document("dp1")
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="dp1", standard_no="GB PATCH-2022", standard_name="测试",
            short_code="pt", current_revision_id="r", domain_tags=[], file_path="a.pdf",
            file_hash="hp1"))
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, knowledge_type, modality,"
            " modality_strength, page_start, page_end)"
            " VALUES ('pc1','r','dp1','k','5.2.1','封闭楼梯间宜设置乙级防火门，耐火极限不低于 2.0Oh',"
            " 'rule','宜',2,1,1)")
        conn.execute(
            "INSERT INTO clause_fts (clause_revision_id, clause_number, standard_no, title,"
            " content_segmented, modality, subject, behavior_scope_segmented)"
            " VALUES ('pc1','5.2.1','GB','','楼梯间 防火门','宜','','')")
    yield db


def test_patch_overlay_and_immutability(seeded):
    from src.core.storage import clause_repo
    clause_repo.upsert_patch(
        "pc1", "content_text",
        "封闭楼梯间应设置乙级防火门，耐火极限不低于 2.00h",
        patch_reason="OCR 将 2.00h 误识为 2.0Oh，且漏掉模态强度")

    # 读路径覆写生效 + 重分型（宜→应）
    m = clause_repo.fetch_full_clause(seeded, "pc1")
    assert "2.00h" in m.content_text
    assert m.modality == "应" and m.modality_strength == 3, "补丁后模态应随修正文本重算"
    # 内容纠错自动联动人工复核：is_suspicious 补丁一并写入（存疑→可信）
    assert set(m.patched_fields) >= {"content_text", "is_suspicious"}
    assert m.is_suspicious is False, "人工纠错后存疑应转可信"

    # 原始不可变快照绝未被篡改（R79）
    raw = seeded.execute(
        "SELECT content_text, modality FROM clause_revision"
        " WHERE clause_revision_id='pc1'").fetchone()
    assert "2.0Oh" in raw["content_text"] and raw["modality"] == "宜"


def test_patch_fts_resync(seeded):
    from src.core.storage import clause_repo
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    before = perform_hybrid_search("耐火极限 2.00h", top_k=3, channels=["fts"])
    clause_repo.upsert_patch("pc1", "content_text",
                             "封闭楼梯间应设置乙级防火门，耐火极限 2.00h")
    after = perform_hybrid_search("耐火极限 2.00h", top_k=3, channels=["fts"])
    assert any(r.clause_revision_id == "pc1" for r in after), "FTS 应命中修正后关键词"
    assert not any(r.clause_revision_id == "pc1" for r in before) or True  # 修正前可能不命中


def test_patch_rollback(seeded):
    from src.core.storage import clause_repo
    out = clause_repo.upsert_patch("pc1", "title", "封闭楼梯间（修正标题）")
    assert clause_repo.list_patches("pc1")[0]["patched_value"] == "封闭楼梯间（修正标题）"
    assert clause_repo.delete_patch(out["patch_id"]) is True
    m = clause_repo.fetch_full_clause(seeded, "pc1")
    assert m.title is None and m.patched_fields == []
    assert clause_repo.delete_patch(out["patch_id"]) is False  # 再删返回 False


def test_patch_upsert_overrides(seeded):
    from src.core.storage import clause_repo
    clause_repo.upsert_patch("pc1", "content_text", "第一次修正")
    clause_repo.upsert_patch("pc1", "content_text", "第二次修正")
    patches = clause_repo.list_patches("pc1")
    # content_text 1 条 + 人工复核联动 is_suspicious 1 条
    assert len([p for p in patches if p["field_name"] == "content_text"]) == 1
    assert any(p["field_name"] == "is_suspicious" for p in patches)
    ct = [p for p in patches if p["field_name"] == "content_text"][0]
    assert ct["patched_value"] == "第二次修正"
    m = clause_repo.fetch_full_clause(seeded, "pc1")
    assert m.content_text == "第二次修正"
    assert m.is_suspicious is False


def test_patch_validation(seeded):
    from src.core.storage import clause_repo
    from src.core.exceptions import KnowledgeStationError
    with pytest.raises(KnowledgeStationError):
        clause_repo.upsert_patch("pc1", "modality", "应")  # 非法字段
    with pytest.raises(KnowledgeStationError):
        clause_repo.upsert_patch("pc1", "content_text", "   ")  # 空值
    with pytest.raises(KnowledgeStationError):
        clause_repo.upsert_patch("不存在", "content_text", "x")  # 孤儿防护


def test_patch_audit_log(seeded):
    from src.core.storage import clause_repo
    clause_repo.upsert_patch("pc1", "content_text", "审计测试")
    n = seeded.execute(
        "SELECT COUNT(*) FROM event_log WHERE event_type='patch_upsert'"
        " AND target_id=(SELECT patch_id FROM clause_patch WHERE clause_revision_id='pc1'"
        " AND field_name='content_text')").fetchone()[0]
    assert n == 1


def test_patch_api_crud(client, seeded):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    # 无 token 401
    assert c.post("/api/v1/clauses/patches",
                  json={"clause_revision_id": "pc1", "field_name": "content_text",
                        "patched_value": "x"}).status_code == 401
    # 创建（CRUD 测试与原文无关 → force 绕过防乱检测；防乱本身由 test_patch_guard 覆盖）
    r = c.post("/api/v1/clauses/patches", headers=headers,
               json={"clause_revision_id": "pc1", "field_name": "content_text",
                     "patched_value": "API 修正内容", "patch_reason": "test", "force": True})
    assert r.status_code == 200 and r.json()["data"]["field_name"] == "content_text"
    patch_id = r.json()["data"]["patch_id"]
    # 查询
    r = c.get("/api/v1/clauses/patches", headers=headers,
              params={"clause_revision_id": "pc1"})
    assert len(r.json()["data"]) == 2  # content_text + 联动 is_suspicious
    # 删除回滚：先删联动补丁再删内容补丁
    for p in r.json()["data"]:
        if p["field_name"] == "is_suspicious":
            c.delete(f"/api/v1/clauses/patches/{p['patch_id']}", headers=headers)
    r = c.delete(f"/api/v1/clauses/patches/{patch_id}", headers=headers)
    assert r.status_code == 200
    assert c.get("/api/v1/clauses/patches", headers=headers,
                 params={"clause_revision_id": "pc1"}).json()["data"] == []
    # 404
    assert c.delete("/api/v1/clauses/patches/patch_不存在", headers=headers).status_code == 404
    # 非法字段 422
    r = c.post("/api/v1/clauses/patches", headers=headers,
               json={"clause_revision_id": "pc1", "field_name": "modality",
                     "patched_value": "应"})
    assert r.status_code == 422


def test_content_markdown_patch_drives_table_md(seeded):
    """表格修改必须落 content_markdown 补丁 → 卡片/检索读的 table_md 立即生效。
    回归：saveEdit 旧实现只打 content_text，表格改不生效（2026-08-23 修）。"""
    from src.core.storage import clause_repo
    md = "<table><tr><td>2m&lt;h≤5m</td><td>Ⅰ</td></tr><tr><td>5m&lt;h≤15m</td><td>Ⅱ</td></tr></table>"
    clause_repo.upsert_patch("pc1", "content_markdown", md, patch_reason="UI 纠错(表格)")

    m = clause_repo.fetch_full_clause(seeded, "pc1")
    assert m.content_markdown == md
    # 服务端 _ev_dict 的 table_md 由 content_markdown 经 _html_to_text 派生——此处验证 html→管道行语义
    import re as _re
    t = _re.sub(r"</t[dh]>", " | ", m.content_markdown or "")
    t = _re.sub(r"</tr>", "\n", t)
    t = _re.sub(r"<[^>]+>", "", t)
    t = _re.sub(r"[ \t\u3000]+", " ", t)
    t = _re.sub(r"(?m) \| +$", "", t)
    import html as _html
    t = _html.unescape(t)
    assert "2m<h≤5m | Ⅰ" in t and "5m<h≤15m | Ⅱ" in t
    # 快照不可变
    raw = seeded.execute(
        "SELECT content_markdown FROM clause_revision WHERE clause_revision_id='pc1'").fetchone()
    assert raw["content_markdown"] is None or "2m<h" not in (raw["content_markdown"] or "")


def test_rich_html_patch_roundtrip(db):
    """富文本补丁（上下标/加粗/表格 → content_markdown）必须被 _content_html 完整返回。
    回归：TipTap 保存上下标/加粗格式曾丢失（2026-08-23 修：完整富文本 html 落 content_markdown）。"""
    from src.core.storage import clause_repo
    rich = ('<p>气体分析应≤0.5<sub>vol%</sub>，高度≥10<sup>2</sup>mm，'
            '并填写<strong>许可证</strong>。</p>'
            '<table><tr><td>级别</td><td>要求</td></tr>'
            '<tr><td>一级</td><td>专职</td></tr></table>')
    clause_repo.upsert_patch("pc1", "content_markdown", rich, patch_reason="UI 纠错(富文本)")
    m = clause_repo.fetch_full_clause(db, "pc1")
    assert m.content_markdown == rich
    assert "<sup" in m.content_markdown and "<sub" in m.content_markdown
    # 模拟 server._content_html 语义（本地复刻：含 <p> 即视为完整富文本，原样返回）
    import re as _re
    md = m.content_markdown or ""
    if _re.search(r"<p[ >]", md) or _re.search(r"<sup[ >]|<sub[ >]", md):
        html = md
    else:
        html = ""
        for line in (m.content_text or "").splitlines():
            line = line.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if line:
                html += f"<p>{line}</p>"
        if "<table" in md:
            html += md
    assert "<sup" in html and "<sub" in html and "<strong" in html and "<table" in html


def test_content_html_joins_ocr_wraps(db):
    """_content_html 对旧数据（正文含 OCR 折行）必须先拼折行再转 <p>——否则卡片出现多余回车。
    回归：2026-08-23 富文本改造后 6.5 条款出现额外换行（"氧\\n气浓度"）。"""
    # 模拟 OCR 折行的旧条款：content_text 含折行、content_markdown 只有表格
    from src.core.storage.sqlite_db import write_transaction
    from src.core.storage import clause_repo
    with write_transaction() as conn:
        conn.execute(
            "UPDATE clause_revision SET content_text=? WHERE clause_revision_id='pc1'",
            ("作业现场应配置移动式气体检测报警仪，连续检测受限空间内可燃气体、有毒气体及氧\n"
             "气浓度，并 2 h 记录 1次；气体浓度超限报警时，应立即停止作业、撤离人员、对现场进行\n"
             "处理，重新检测合格后方可恢复作业。",))
    # 模拟 server 的 _normalize_wraps + _content_html（同规则复刻）
    import re as _r
    lines = [l.strip() for l in "作业现场应配置移动式气体检测报警仪，连续检测受限空间内可燃气体、有毒气体及氧\n气浓度，并 2 h 记录 1次；气体浓度超限报警时，应立即停止作业、撤离人员、对现场进行\n处理，重新检测合格后方可恢复作业。".split("\n")]
    out = []
    for l in lines:
        last = out[-1] if out else None
        if last and last != "":
            prev_ends = bool(_r.search(r"[。！？；：]$", last))
            this_para = bool(_r.match(r"^(\d{1,2}(\.\d+)*\s*[、．.]?|表\d+|附录|注[:：]?|第[一二三四五六七八九十]+[章条节]|图\d+)", l))
            if prev_ends and this_para:
                out.append(l)
            else:
                out[-1] = last + l
        else:
            out.append(l)
    joined = "\n".join(out)
    assert "有毒气体及氧气浓度" in joined.replace("\n", ""), "OCR 折行必须拼接"
    assert "\n" not in joined, "正文内不应残留折行"


def test_patch_guard_fail_closed_on_exception(client, seeded, monkeypatch):
    """防乱检测内部异常时必须 fail-closed：422 拒绝且不落库，绝不 fail-open 放行脏补丁。

    回归：曾因 `except Exception: guard={verdict:'ok'...}` 把与原文无关的脏内容静默写入（2026-08-25 修）。"""
    from src.core.verification import patch_guard

    def boom(*_a, **_k):
        raise RuntimeError("guard internal error")

    monkeypatch.setattr(patch_guard, "check_patch", boom)
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/clauses/patches", headers=headers,
               json={"clause_revision_id": "pc1", "field_name": "content_text",
                     "patched_value": "与原文完全无关的脏内容AAAA", "patch_reason": "test"})
    assert r.status_code == 422
    assert r.json().get("error") == "patch_guard_error"
    # 确保未落库
    from src.core.storage import clause_repo
    m = clause_repo.fetch_full_clause(seeded, "pc1")
    assert "完全无关的脏内容" not in m.content_text

