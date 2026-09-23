"""T11 Golden Set：标准问答（GB30871 真实库）。

标准问答基准：5 个问题，断言 top3 检索命中目标条款 + 占位/真实回答路径可用。
（LLM 断言仅限结构，不做真实调用——省额度。）
"""
import pytest

from pathlib import Path

QA_GOLDEN = [
    ("动火作业应有专人监护", "5.2.1"),
    ("受限空间作业人员应正确穿戴个体防护装备", "6.6"),
    ("进入受限空间作业前应保持空气流通", "6.2"),
    ("动火作业前应进行气体分析", "5.3.1"),
    ("监护人不应擅自离开作业现场", "6.8"),
]


@pytest.mark.skipif(
    not Path(__file__).resolve().parent.parent.joinpath(
        "var", "engine.log").exists() and False,
    reason="真实库检查走 DB 直接判定")
def test_qa_retrieval_hits_golden(_isolate_data_dir):
    """对真实库做检索命中基准（库含 GB30871 时启用）。"""
    from src.core.storage.sqlite_db import get_db_connection, init_schema
    init_schema()
    conn = get_db_connection()
    has_gb = conn.execute(
        "SELECT 1 FROM doc_meta WHERE standard_no='GB 30871-2022'").fetchone()
    if not has_gb:
        pytest.skip("真实库无 GB30871（CI/新环境）")
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    hits = 0
    for q, target in QA_GOLDEN:
        res = perform_hybrid_search(q, top_k=3)
        ids = {r.clause_number for r in res}
        if target in ids:
            hits += 1
    assert hits >= 4, f"Golden Set 检索命中不足: {hits}/5"


def test_golden_qa_api_structure(client, _isolate_data_dir):
    """问答 API 结构基准（不依赖真实库内容）。"""
    c, token = client
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": QA_GOLDEN[0][0], "top_k": 2, "query_mode": "guess"},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        assert r.status_code == 200
        events = []
        for line in r.iter_lines():
            if line.startswith("event: "):
                events.append(line[7:])
    assert events[0] == "evidence"
    assert events[-1] == "done"
    assert "verification" in events


