# -*- coding: utf-8 -*-
"""**结论草稿**测试（`src/core/exports/research_draft.py` + `POST /report/research/draft`，§10.96）。

守四件事：
  1. **没有可承重材料 ⇒ 一次 LLM 都不调**（绝不靠常识硬写）；
  2. **草稿的引用校验与报告同源**：同一个 `assemble_evidence()` 结果 ⇒ 编号一致，
     判据与措辞都是 `research_report.check_conclusion_citations()`（唯一所有者）；
  3. **不许静默降级**：LLM 不可用 ⇒ 抛 `llm_unavailable`；空输出 ⇒ 空草稿 + 警告；
     引用不成立 ⇒ 草稿**原样保留** + 警告逐条列出；
  4. **草稿不是依据**：`status == "unapproved_draft"` 是契约，端点必须原样带出。
"""
from __future__ import annotations

import pytest

from src.core.exceptions import KnowledgeStationError
from src.core.exports import research_draft as rd
from src.core.llm import ks_answer as ka
from src.core.storage import material_repo as mr

HDR = {"Authorization": "Bearer test-token-123"}


@pytest.fixture()
def project(db):
    return mr.create_project("结论草稿测试")


def _add(pid, title, text, *, tier="T1", domain=None, role=None,
         review="approved", origin="user"):
    m = mr.add_material(pid, title, origin=origin, source_tier=tier,
                        domain=domain, url=None if origin == "user" else "https://a.example/1")
    mr.add_chunks(m["material_id"], [{"text": text, "char_start": 0,
                                      "char_end": len(text), "page": 1}])
    if role:
        mr.set_task_role(m["material_id"], role)
    mr.set_review(m["material_id"], review)
    return m


def _stub_llm(monkeypatch, captured: dict, text: str) -> None:
    """替身：记录 messages 并**一次**产出 `text`（零真实 LLM 消耗）。"""
    def fake_stream(messages, **_kw):
        captured.setdefault("calls", []).append(messages)
        yield text
    monkeypatch.setattr(ka, "_stream_llm", fake_stream)


class TestGuards:
    def test_没有可承重材料时一次_LLM_都不调(self, project, monkeypatch):
        """只有 T3 单一来源（仅线索）⇒ 可承重集合为空 ⇒ **不许**调模型。"""
        pid = project["project_id"]
        _add(pid, "某论坛帖", "住宿标准据说每晚八百元", tier="T3", domain="bbs.example")
        cap: dict = {}
        _stub_llm(monkeypatch, cap, '{"derivation":"x","conclusion":"y"}')

        out = rd.draft_conclusion(pid, query="住宿标准")
        assert out["llm_called"] is False
        assert cap.get("calls") is None, "没有可承重材料时**不许**调用模型"
        assert out["draft_md"] == ""
        assert out["usable_indices"] == []
        assert out["counts"]["leads_only"] == 1
        assert any("没有起草" in w for w in out["warnings"]), out["warnings"]

    def test_项目不存在时_ValueError(self, project):
        with pytest.raises(ValueError):
            rd.draft_conclusion("prj_不存在", query="住宿标准")

    def test_LLM_不可用时报可操作的错误(self, project, monkeypatch):
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元", tier="T1", role="criterion")

        def boom(_messages, **_kw):
            raise KnowledgeStationError("DEEPSEEK_API_KEY 未配置", code="llm_error")

        monkeypatch.setattr(ka, "_stream_llm", boom)
        with pytest.raises(KnowledgeStationError) as ei:
            rd.draft_conclusion(pid, query="住宿标准")
        assert ei.value.code == "llm_unavailable"
        assert "配置" in str(ei.value)          # 可操作：告诉用户去配置 Key
        assert "凭常识作答" in str(ei.value)     # 并说明**不会**降级

    def test_空输出不是成功(self, project, monkeypatch):
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元", tier="T1", role="criterion")
        cap: dict = {}
        _stub_llm(monkeypatch, cap, "")
        out = rd.draft_conclusion(pid, query="住宿标准")
        assert out["llm_called"] is True
        assert out["draft_md"] == ""
        assert any("没有产出结论段" in w for w in out["warnings"]), out["warnings"]


class TestHappyPath:
    def test_草稿带未批准标记且引用校验与报告同源(self, project, monkeypatch):
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元，自下月起执行。",
             tier="T1", role="criterion")
        cap: dict = {}
        _stub_llm(monkeypatch, cap,
                  '{"derivation":"按公司制度 [[m:0]]。",'
                  '"conclusion":"住宿标准每晚不超过五百元 [[m:0]]。"}')

        out = rd.draft_conclusion(pid, query="住宿标准")
        assert out["status"] == "unapproved_draft"          # **契约**：调用方必须能一眼看出
        assert "未经用户批准" in out["disclaimer"]
        assert "五百元" in out["draft_md"]
        assert out["llm_called"] is True
        assert out["usable_indices"] == [0]
        # 引用校验：与报告**同一个函数**的同一套结构化字段
        assert out["citations"]["material_refs"] == [0]
        assert out["citations"]["unknown"] == []
        assert out["citations"]["not_load_bearing"] == []
        assert not any("不存在" in w for w in out["warnings"]), out["warnings"]

    def test_提示词里材料另起一节且编号与校验同一套(self, project, monkeypatch):
        """**同源不变量**：提示词里的 `[[m:i]]` 编号必须与校验用的 assembled 是同一个。"""
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元", tier="T1", role="criterion")
        cap: dict = {}
        _stub_llm(monkeypatch, cap, '{"derivation":"d","conclusion":"c [[m:0]]"}')

        out = rd.draft_conclusion(pid, query="住宿标准")
        user_msg = cap["calls"][0][1]["content"]
        assert "参考资料" in user_msg                    # 材料另起一节（取证链的构造器）
        assert "[[m:0]]" in user_msg                     # 编号由 render_evidence 分配
        assert ka.MATERIAL_SYSTEM_ADDENDUM in cap["calls"][0][0]["content"]
        assert out["citations"]["material_refs"] == [0]  # 同一个编号在**校验**里也成立


class TestCitationWarnings:
    def test_不存在的编号_草稿原样保留且两层都报警(self, project, monkeypatch):
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元。", tier="T1")
        cap: dict = {}
        _stub_llm(monkeypatch, cap,
                  '{"derivation":"d","conclusion":"据 [[m:7]] 可知，每晚不超过五百元。"}')

        out = rd.draft_conclusion(pid, query="住宿标准")
        assert out["citations"]["unknown"] == [7]
        assert any("不存在" in w for w in out["warnings"]), out["warnings"]
        # 取证链自带的**越界**检查也在（两层判据各自报各自的，互补不重复）
        assert any("out_of_range" in w for w in out["warnings"]), out["warnings"]
        assert "[[m:7]]" in out["draft_md"], "草稿必须**原样保留**（不许静默删改模型写的东西）"

    def test_引用仅线索的材料会被列出来(self, project, monkeypatch):
        """可作依据的 T1 在前面、仅线索的 T3 在后面 ⇒ 引用后者必须被点名。"""
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元。", tier="T1", role="criterion")
        _add(pid, "某论坛帖", "住宿标准据说每晚八百元。", tier="T3", domain="bbs.example")
        cap: dict = {}
        _stub_llm(monkeypatch, cap,
                  '{"derivation":"d","conclusion":"据 [[m:1]] 可知八百元。"}')

        out = rd.draft_conclusion(pid, query="住宿标准")
        # T3 单一来源 ⇒ 仅线索（不进承重集合），但**仍然**出现在依据集里（可见性）
        assert out["usable_indices"] == [0]
        assert out["citations"]["material_refs"] == [1]
        assert [b["group"] for b in out["citations"]["not_load_bearing"]] == ["leads_only"]
        assert any("不得" in w and "承重" in w for w in out["warnings"]), out["warnings"]


class TestEndpoint:
    def test_缺少_query_是_422(self, client, project):
        c, _ = client
        r = c.post("/api/v1/report/research/draft",
                   json={"project_id": project["project_id"]}, headers=HDR)
        assert r.status_code == 422, r.text
        assert r.json()["error"] == "materials_bad_request"

    def test_缺少_project_id_是_422(self, client):
        c, _ = client
        r = c.post("/api/v1/report/research/draft", json={"query": "x"}, headers=HDR)
        assert r.status_code == 422, r.text

    def test_项目不存在_404(self, client):
        c, _ = client
        r = c.post("/api/v1/report/research/draft",
                   json={"project_id": "prj_没有", "query": "住宿标准"}, headers=HDR)
        assert r.status_code == 404, r.text
        assert r.json()["error"] == "materials_not_found"

    def test_正常路径_200_且带未批准标记(self, client, project, monkeypatch):
        c, _ = client
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元。", tier="T1", role="criterion")
        cap: dict = {}
        _stub_llm(monkeypatch, cap,
                  '{"derivation":"d","conclusion":"每晚不超过五百元 [[m:0]]。"}')
        r = c.post("/api/v1/report/research/draft",
                   json={"project_id": pid, "query": "住宿标准"}, headers=HDR)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["status"] == "unapproved_draft"
        assert data["draft_md"] and data["citations"]["material_refs"] == [0]
        assert "files" not in data, "草稿**不落盘**（与 /report/research 的关键区别）"

    def test_LLM_不可用_500_llm_unavailable(self, client, project, monkeypatch):
        c, _ = client
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元。", tier="T1", role="criterion")

        def boom(_messages, **_kw):
            raise KnowledgeStationError("DEEPSEEK_API_KEY 未配置", code="llm_error")

        monkeypatch.setattr(ka, "_stream_llm", boom)
        r = c.post("/api/v1/report/research/draft",
                   json={"project_id": pid, "query": "住宿标准"}, headers=HDR)
        assert r.status_code == 500, r.text
        assert r.json()["error"] == "llm_unavailable"
