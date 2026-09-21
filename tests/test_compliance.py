"""T06a 合规审查测试：审查点抽取 / 法条匹配 / 三色判定 / API SSE 流。"""
import json

import pytest


@pytest.fixture(scope="module")
def law_db(_isolate_data_dir):
    """种入合成法律条款（legal 型，含主体/模态/但书）。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import init_schema, get_db_connection, write_transaction
    from src.core.domain.models import ClauseRevisionModel
    init_schema()
    conn = get_db_connection()
    if conn.execute("SELECT 1 FROM doc_meta WHERE doc_id='dlaw'").fetchone():
        yield conn
        return
    with write_transaction() as txn:
        clause_repo.insert_document(txn, dict(
            doc_id="dlaw", standard_no="个人信息保护法", standard_name="个人信息保护法",
            short_code="PIPL", current_revision_id="r", doc_type="法律法规",
            legal_hierarchy="法律", domain_tags=["数据安全"],
            file_path="law.pdf", file_hash="hl1"))
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id=f"lc{i}", doc_id="dlaw", clause_key=f"lk{i}",
            standard_no="个人信息保护法", clause_number=no, content_text=text,
            knowledge_type="legal", modality=mod,
            modality_strength=st, subject=subj, exception=exc,
            behavior_scope=bs, page_start=1, page_end=1)
        for i, (no, text, mod, st, subj, exc, bs) in enumerate([
            ("第七条", "经营者不得利用格式条款和技术手段，排除或者限制消费者权利。",
             "不得", 4, "经营者", None, "格式条款 消费者权利"),
            ("第五条", "处理敏感个人信息应当取得个人的单独同意。",
             "应当", 3, "个人信息处理者", None, "敏感个人信息 单独同意 人脸"),
            ("第九条", "消费者享有对商品和服务进行监督的权利，可以提出批评和建议。",
             "可以", 1, "消费者", None, "监督 批评 建议"),
        ])
    ])
    yield conn


CONTRACT = """甲方与乙方经协商一致，达成如下条款：
第一条 本协议最终解释权归甲方所有，乙方概不得异议。
第二条 任何一方违约的，违约金为合同总额的30%。
第三条 因本协议发生争议，由甲方所在地法院管辖。
第四条 消费者可以对服务提出批评和建议。"""


def test_extract_review_points(law_db):
    from src.core.compliance.engine import extract_review_points
    points = extract_review_points(CONTRACT, "contract")
    types = {p["point_type"] for p in points}
    assert "格式条款" in types, "最终解释权应识别为格式条款审查点"
    assert "违约金条款" in types
    assert "管辖条款" in types
    behavior = extract_review_points("在公司 App 收集用户人脸信息用于考勤", "behavior")
    assert len(behavior) == 1 and behavior[0]["point_type"] == "行为描述"


def test_judge_red_for_final_interpretation(law_db):
    from src.core.compliance.engine import judge_point_rule
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    matched = perform_hybrid_search("最终解释权 归甲方所有 排除消费者权利", top_k=5)
    v = judge_point_rule({"point_type": "格式条款",
                          "point_content": "本协议最终解释权归甲方所有"}, matched)
    assert v["verdict"] == "red", v["reason"]
    assert v["matched"] is not None


def test_judge_green_for_empowerment(law_db):
    from src.core.compliance.engine import judge_point_rule
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    matched = perform_hybrid_search("消费者可以对服务提出批评和建议", top_k=5)
    v = judge_point_rule({"point_type": "一般条款",
                          "point_content": "消费者可以对服务提出批评和建议"}, matched)
    assert v["verdict"] == "green", v["reason"]


def test_full_review_flow(law_db):
    from src.core.compliance.engine import create_review_task, execute_review
    out = create_review_task("contract", "测试合同", CONTRACT)
    assert out["status"] == "pending" and len(out["extracted_points"]) >= 3
    verdicts = list(execute_review(out["task_id"]))
    assert all(v["verdict"] in ("red", "yellow", "green") for v in verdicts)
    assert any(v["verdict"] == "red" for v in verdicts), "最终解释权条款应判 red"
    row = law_db.execute(
        "SELECT status, red_count, yellow_count, green_count, report_data FROM review_task"
        " WHERE task_id=?", (out["task_id"],)).fetchone()
    assert row["status"] == "completed"
    assert row["red_count"] + row["yellow_count"] + row["green_count"] == len(verdicts)
    assert json.loads(row["report_data"])["counts"]["red"] == row["red_count"]


def test_behavior_review_face_collection(law_db):
    """未取得单独同意的人脸收集 ⇒ 判决必须是 red。

    ⚠⚠ **2026-09-21（KB-FOLDER-PLAN 第 4 步复核）加的环境门槛**（门槛变更 ⇒ 必验）。
    这条**不是 flake**：它对"BGE 向量模型能不能加载"是**确定性依赖** ——
    模型可用 ⇒ 混合检索六路齐活 ⇒ 命中「处理敏感个人信息应当取得个人的单独同意」⇒ red；
    `embedder.is_available()` 为假（本机半死代理下下载 BGE 实测 2 分 25 秒后失败）⇒
    向量通道整条缺失 ⇒ 判决退化成 **yellow** 且**没有任何跳过** ⇒ 这一条**必红**。
    ⇒ 照 `tests/test_retrieval.py::test_vec_channel` 的**既有先例**如实跳过（R30 降级路径），
    **不改判据、不改成恒真、不强制离线**（强制离线会让它恒红，那是把门槛藏起来）。
    ⚠ 这条 nodeid 已登记进 `scripts/gates-baseline.json` 的 `environmental_skip_nodeids`
    （环境类 skip 白名单，代价 1 条），所以"模型不可用 ⇒ 跳过"不会被棘轮当成新跳过。
    """
    pytest.importorskip("fastembed")
    from src.core.retrieval import embedder
    if not embedder.is_available():
        pytest.skip("向量引擎不可用（BGE 未加载成功）⇒ 六路召回退化为 FTS ⇒ "
                    "这条判决必然落到 yellow；按 R30 降级路径如实跳过，不改判据")
    from src.core.compliance.engine import create_review_task, execute_review
    out = create_review_task("behavior", "人脸考勤",
                             "在公司 App 收集用户人脸信息用于考勤，未取得单独同意")
    verdicts = list(execute_review(out["task_id"]))
    assert verdicts[0]["verdict"] == "red", "未取得单独同意的人脸收集应判 red"


def test_review_api_sse(client, law_db):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/compliance/review", headers=headers,
               json={"review_type": "contract", "object_name": "API 测试合同",
                     "object_content": CONTRACT})
    assert r.status_code == 200
    task_id = r.json()["data"]["task_id"]
    events = []
    with c.stream("POST", f"/api/v1/compliance/review/{task_id}/execute",
                  headers=headers, json={"confirmed_point_ids": None}) as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if line.startswith("event: "):
                events.append(line[7:])
    assert events[0] == "point_verdict"
    assert events[-2] == "report_ready" and events[-1] == "done"
    # 未带 token 应 401
    assert c.post("/api/v1/compliance/review",
                  json={"review_type": "contract", "object_content": "x"}
                  ).status_code == 401
