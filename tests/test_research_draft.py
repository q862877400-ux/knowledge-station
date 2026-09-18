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
    def test_只装配一次(self, project, monkeypatch):
        """**同源不变量的门禁**（§10.98，复核 b25 的 LOW-3）：起草全流程只能装配**一次**。

        若哪天有人在"调模型之前"和"校验引用之前"各装配一次，两次检索的命中顺序可能不同
        ⇒ `[[m:i]]` 编号漂移 ⇒ 把**合法引用**误判成"引用了不存在的材料"（或反过来漏判）。
        b25 是用 monkeypatch 计数器才钉住这一点的（代码里没有任何用例守着它）⇒ 现在补上。
        """
        from src.core.materials import authority as au

        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元。", tier="T1", role="criterion")
        calls = {"n": 0}
        real = au.assemble_evidence

        def counted(*a, **k):
            calls["n"] += 1
            return real(*a, **k)

        monkeypatch.setattr(au, "assemble_evidence", counted)
        cap: dict = {}
        _stub_llm(monkeypatch, cap, '{"derivation":"d","conclusion":"五百元 [[m:0]]"}')
        out = rd.draft_conclusion(pid, query="住宿标准")
        assert calls["n"] == 1, f"装配次数必须恰好 1（实测 {calls['n']}）"
        # 而且校验用的编号就是**那一次**的编号（引用合法 ⇒ 无 unknown）
        assert out["citations"]["material_refs"] == [0]
        assert out["citations"]["unknown"] == []

    def test_材料装配失败时报可操作错误码(self, project, monkeypatch):
        """§10.98（复核 b25 的 MEDIUM-1）：依据集取不到 ⇒ 500 `materials_load_failed`。

        原先 `assemble_evidence` **不在 try 里** ⇒ 异常穿过路由层那两个 `except`
        （只接 `ValueError`/`KnowledgeStationError`）变成**裸 500**：用户只看到
        "Internal Server Error"，真原因只在日志里。这条用例钉住"翻成可操作错误码"。
        """
        from src.core.materials import authority as au

        def boom(*_a, **_k):
            raise RuntimeError("数据库被锁死（模拟）")

        monkeypatch.setattr(au, "assemble_evidence", boom)
        with pytest.raises(KnowledgeStationError) as ei:
            rd.draft_conclusion(project["project_id"], query="住宿标准")
        assert ei.value.code == "materials_load_failed"
        assert "载入参考资料失败" in str(ei.value)
        assert "不会" in str(ei.value)          # 明说不会给"看着正常"的产物

    def test_项目不存在仍然按_ValueError_放行(self, project, monkeypatch):
        """⚠ 翻错误码**只翻"意外的失败"**：项目不存在那类 `ValueError` 必须照原样放行
        （路由层靠它翻 404）——否则会把"项目不存在"报成 500。"""
        from src.core.materials import authority as au

        def missing(*_a, **_k):
            raise ValueError("报告: 项目不存在: prj_x")

        monkeypatch.setattr(au, "assemble_evidence", missing)
        with pytest.raises(ValueError):
            rd.draft_conclusion(project["project_id"], query="住宿标准")

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

    def test_不喂法条时不该冒噪声警告_但出现法条编号要明说(self, project, monkeypatch):
        """§10.98（复核 b25 的 LOW-2）：**噪声警告换成准确的那一条**。

        取证链的提示词无条件要求 `[[c:i]]` 标记，而草稿**故意不喂法条** ⇒ 模型正确只引材料时
        也会吃一条 `llm_json_no_citation_marker`（实测在**正常路径**上就命中）。噪声的坏处是
        "以后用户不信真警告"。但"草稿里**出现** `[[c:i]]`"是真问题（那些编号无从核验）⇒
        滤掉不适用的那条、换成准确的那条（不是少报）。
        """
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元。", tier="T1", role="criterion")

        # ① 干净路径：谁都不提 `[[c:i]]` ⇒ 连取证链那条"没出现 [[c:i]]"都不会触发，警告应为空
        cap: dict = {}
        _stub_llm(monkeypatch, cap, '{"derivation":"d","conclusion":"五百元 [[m:0]]"}')
        clean = rd.draft_conclusion(pid, query="住宿标准")
        assert not any("no_citation_marker" in w for w in clean["warnings"]), clean["warnings"]
        assert clean["warnings"] == [], clean["warnings"]

        # ② **真模型会出现的形状**：提示词要求"引用处用 [[c:i]]"，于是结论里带了 `[[c:0]]`
        #    ⇒ 取证链会报 `llm_json_no_citation_marker`（derivation 里没有 `[[c:i]]`），
        #    而那条对"**没喂法条**的草稿"**不适用** ⇒ 必须被滤掉，换成准确的那一条。
        cap2: dict = {}
        _stub_llm(monkeypatch, cap2,
                  '{"derivation":"据材料可知。","conclusion":"据 [[c:0]] 与 [[m:0]] 可知五百元。"}')
        cited = rd.draft_conclusion(pid, query="住宿标准")
        assert not any("no_citation_marker" in w for w in cited["warnings"]), cited["warnings"]
        assert any("法条编号" in w and "无从核验" in w for w in cited["warnings"]), cited["warnings"]
        assert cited["citations"]["unchecked_law_refs"] == [0]


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
