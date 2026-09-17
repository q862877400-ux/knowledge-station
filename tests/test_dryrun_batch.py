"""D 组 + F 组（只读端点）：批量分桶语义与 HTTP 契约。

## 分桶守恒
`ok + warn + block == evaluated` 必须恒成立（决策 2 的"总账"不能丢件）；
单文件失败**不得中断整批**（沿用 `bulk.parse_loop` 的既有范式）。

## 抽样确定性
`sample` 用**确定性等距抽样**（字典序 + 等步长），不用随机 + seed：
这样才能精确断言"抽到的就是那几个"，两次跑结果必须完全相同。

## HTTP 契约
坏文档**不是 HTTP 错误**（解析失败也返回 200，由 `verdict="block"` 表达）——
否则"100% 拦截"会退化成"看到一个报错但不知道拦了什么"。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.core.ingestion import dry_run

# 复用合成 PDF 工具（pytest 默认 importmode=prepend 会把 tests/ 目录加入 sys.path；
# 本仓库 tests/ 不是包，所以按模块名直接导入而不是 tests.xxx）
import test_dryrun_report as pdfkit  # noqa: E402

_mk_good_pdf = pdfkit._mk_good_pdf
_mk_scan_pdf = pdfkit._mk_scan_pdf
_mk_sparse_pdf = pdfkit._mk_sparse_pdf
_mk_broken_file = pdfkit._mk_broken_file

HDR = {"Authorization": "Bearer test-token-123"}


@pytest.fixture()
def batch_dir(tmp_path):
    """5 本好 + 1 本稀疏(block) + 1 个非法文件(block) + 1 本扫描(warn)。"""
    d = tmp_path / "inbox"
    d.mkdir()
    for i in range(5):
        _mk_good_pdf(d, f"good_{i}.pdf")
    _mk_sparse_pdf(d, "sparse.pdf")
    _mk_broken_file(d, "broken.pdf")
    _mk_scan_pdf(d, "scan.pdf")
    return d


# --------------------------------------------------------------------------- #
# D 组：批量分桶
# --------------------------------------------------------------------------- #
def test_batch_buckets_conserve(db, batch_dir):
    paths = dry_run.scan_preview_dir(batch_dir)
    out = dry_run.preview_batch(paths, sample=0)  # 0 = 不抽样（全量）
    assert out["evaluated"] == len(paths) == 8, (out["evaluated"], len(paths))
    assert out["conservation_ok"] is True
    b = out["buckets"]
    assert b["ok"] + b["warn"] + b["block"] == out["evaluated"]
    assert b["block"] >= 2, b          # 稀疏 + 非法文件
    assert b["warn"] >= 1, b           # 扫描件
    assert b["ok"] >= 5, b             # 5 本好文档
    assert out["egress"] == "none"


def test_batch_single_failure_does_not_abort(db, batch_dir):
    """把坏文件排到第 2 位，后面 6 个仍必须全部被评估。"""
    paths = sorted(dry_run.scan_preview_dir(batch_dir))
    # broken.pdf 与 good_*.pdf 字典序下 broken 很靠前；显式再插一个非法文件到第 2 位
    bad = batch_dir / "aaa_first.pdf"
    bad.write_bytes(b"garbage" * 10)
    paths = sorted([bad] + paths, key=lambda p: p.name.lower())
    assert "aaa_first" in paths[0].name
    out = dry_run.preview_batch(paths, sample=0)
    assert out["evaluated"] == len(paths), (out["evaluated"], len(paths))
    assert out["buckets"]["block"] >= 1
    # 首个（非法）文件的 error 必须如实记下，而不是被吞
    first = out["files"][0]
    assert first["path"].endswith("aaa_first.pdf")
    assert first["verdict"] == "block"


def test_batch_sample_is_deterministic_stride(db, batch_dir):
    """sample=5 抽 5 本，且两次跑结果完全相同（确定性等距）。"""
    paths = dry_run.scan_preview_dir(batch_dir)
    a = dry_run.preview_batch(paths, sample=5)
    b = dry_run.preview_batch(paths, sample=5)
    assert a["sampled"] == b["sampled"] == 5
    assert [f["path"] for f in a["files"]] == [f["path"] for f in b["files"]]
    assert a["unprocessed"] == len(paths) - 5
    # 等距：首尾必选
    picked = [f["path"] for f in a["files"]]
    assert picked[0] == str(paths[0]) and picked[-1] == str(paths[-1])


def test_batch_sample_zero_or_none_means_all(db, batch_dir):
    paths = dry_run.scan_preview_dir(batch_dir)
    assert dry_run.preview_batch(paths, sample=0)["sampled"] == len(paths)
    assert dry_run.preview_batch(paths, sample=99)["sampled"] == len(paths)


def test_batch_no_db_write(db, batch_dir):
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    names = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    before = {n: conn.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0] for n in names}
    dry_run.preview_batch(dry_run.scan_preview_dir(batch_dir), sample=0)
    after = {n: conn.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0] for n in names}
    assert after == before


def test_batch_limit_files_truncates(db, batch_dir):
    paths = dry_run.scan_preview_dir(batch_dir)
    out = dry_run.preview_batch(paths, sample=0, limit_files=3)
    assert out["truncated"] is True and out["evaluated"] <= 3
    assert out["total_candidates"] == len(paths)


def test_batch_rows_are_thin(db, batch_dir):
    """每行只有摘要字段（不回传全文——payload 红线）。"""
    out = dry_run.preview_batch(dry_run.scan_preview_dir(batch_dir), sample=0)
    expected = {"path", "file_name", "verdict", "grade", "pages", "total_clauses",
                "doc_confidence", "one_line", "reasons", "error"}
    for row in out["files"]:
        assert set(row) == expected, set(row) ^ expected


def test_batch_scan_preview_dir_missing(tmp_path):
    with pytest.raises(NotADirectoryError):
        dry_run.scan_preview_dir(tmp_path / "不存在")


def test_batch_scan_preview_dir_sorted_and_filtered(batch_dir):
    (batch_dir / "note.txt").write_text("x")
    (batch_dir / "sub").mkdir()
    _mk_good_pdf(batch_dir / "sub", "inner.pdf")
    flat = dry_run.scan_preview_dir(batch_dir)
    assert all(p.suffix == ".pdf" for p in flat)
    assert [p.name for p in flat] == sorted((p.name for p in flat), key=str.lower)
    assert not any("inner" in p.name for p in flat)          # 不递归
    assert any("inner" in p.name for p in dry_run.scan_preview_dir(batch_dir, recursive=True))


def test_batch_never_asks_for_deep(db, batch_dir, monkeypatch):
    """**批量路径默认不外发**：不传 deep_fallback 时每个文件都必须以 False 解析。

    这是 verifier 审计 P0-2 的回归网（2026-09-11）。2026-09-17 D5 后口径由
    "结构性禁止"改为"**默认安全 + 显式可开 + 如实标注**"，但**本条不变**：
    默认必须是 False，否则就是静默外发。
    """
    from src.core.ingestion import parser_worker
    calls: list[dict] = []

    def _fake(pdf_path, output_dir, timeout=900, force_deep=False, deep_fallback=True):
        calls.append({"force_deep": force_deep, "deep_fallback": deep_fallback})
        return {"blocks": [{"page_number": 1, "text": "5.1 动火作业应有专人监护。",
                            "bbox": [0.0, 0.0, 100.0, 20.0], "source": "pymupdf"}],
                "geometries": {1: {"width": 595.0, "height": 842.0, "rotation": 0,
                                   "crop_box": [], "media_box": []}},
                "is_ocr": False, "deep_output": None,
                "text_layer_state": "ok", "deep_fallback_skipped": False}

    monkeypatch.setattr(parser_worker, "run_parser_isolated", _fake)
    out = dry_run.preview_batch(dry_run.scan_preview_dir(batch_dir), sample=3)
    assert calls, "批量预览必须真的调用解析"
    assert all(c == {"force_deep": False, "deep_fallback": False} for c in calls), calls
    assert out["egress"] == "none"


def test_batch_deep_switch_defaults_off_and_optin_really_wires_through(
        db, batch_dir, monkeypatch):
    """D5 后的新契约（**替代**原 `test_batch_preview_batch_has_no_deep_switch`）。

    原来靠"函数签名里**不接受** deep_fallback"来保证批量路径不外发——安全，但
    代价是**永久封死**该能力。2026-09-11 审计当时担心的其实是"改了默认值会**静默**
    外发、而批量侧没有测试网"。D5 改为把**缺的那张网补上**，能力交还调用方：

      ① 参数存在，但**默认必须为 False**（防静默外发——这条替代了"结构性禁止"）；
      ② **显式传 True 必须真的透传**到解析层（防"参数加了却不接线"这种假修）；
      ③ 开启了就必须**如实标注**（`egress != "none"`，红线 4 / D2：不禁止但必须留痕）。
    """
    import inspect

    from src.core.ingestion import parser_worker

    # ① 默认必须为 False
    sig = inspect.signature(dry_run.preview_batch)
    assert "deep_fallback" in sig.parameters, list(sig.parameters)
    assert sig.parameters["deep_fallback"].default is False, (
        "preview_batch 的 deep_fallback 默认值必须是 False，否则默认路径会静默外发")

    # ② 显式 True 必须真的到达解析层
    calls: list[dict] = []

    def _fake(pdf_path, output_dir, timeout=900, force_deep=False, deep_fallback=True):
        calls.append({"force_deep": force_deep, "deep_fallback": deep_fallback})
        return {"blocks": [{"page_number": 1, "text": "5.1 动火作业应有专人监护。",
                            "bbox": [0.0, 0.0, 100.0, 20.0], "source": "pymupdf"}],
                "geometries": {1: {"width": 595.0, "height": 842.0, "rotation": 0,
                                   "crop_box": [], "media_box": []}},
                "is_ocr": False, "deep_output": None,
                "text_layer_state": "ok", "deep_fallback_skipped": False}

    monkeypatch.setattr(parser_worker, "run_parser_isolated", _fake)
    out = dry_run.preview_batch(dry_run.scan_preview_dir(batch_dir), sample=3,
                                deep_fallback=True)
    assert calls, "批量预览必须真的调用解析"
    assert all(c["deep_fallback"] is True for c in calls), (
        f"显式开启没有透传到解析层（假修）：{calls}")
    # ③ 开启了必须如实标注，不能还报 none
    assert out["egress"] != "none", out.get("egress")


def test_batch_limit_files_negative_is_clamped(db, batch_dir):
    """负的 limit_files 不得静默"从尾部砍"（审计 P2-2）：夹到 0 → 一个都不评估。"""
    paths = dry_run.scan_preview_dir(batch_dir)
    out = dry_run.preview_batch(paths, sample=0, limit_files=-5)
    assert out["limit_files"] == 0 and out["evaluated"] == 0, out



# --------------------------------------------------------------------------- #
# F 组：HTTP 契约（只读端点）
# --------------------------------------------------------------------------- #
def test_api_preview_ok_envelope(client, db, tmp_path):
    c, token = client
    p = _mk_good_pdf(tmp_path, "api_ok.pdf")
    r = c.post("/api/v1/ingest/preview", json={"path": str(p)}, headers=HDR)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == 200 and body["status"] == "success"
    data = body["data"]
    for key in ("schema_version", "status", "source", "pages", "total_clauses", "grade",
                "grade_reasons", "doc_confidence", "verdict", "verdict_reasons",
                "head_samples", "tail_samples", "ocr_suspects", "knowledge_type_distribution",
                "typing_quality", "legal_elements", "recognition", "layout",
                "standard_no_guess", "standard_name_guess", "duplicate",
                "quarantine_candidate", "deep_fallback_disabled", "deep_fallback_skipped",
                "egress", "elapsed_ms", "error_code", "error_message"):
        assert key in data, key
    assert data["source"]["file_hash"] == hashlib.sha256(p.read_bytes()).hexdigest()
    # 请求级：预览禁用深度通道（恒 True）；文档级：文本层文档不需要跳过（False）——两者都如实报
    assert data["egress"] == "none" and data["deep_fallback_disabled"] is True
    assert data["deep_fallback_skipped"] is False


def test_api_preview_bad_requests(client, db, tmp_path):
    c, token = client
    assert c.post("/api/v1/ingest/preview", json={}, headers=HDR).status_code == 422
    assert c.post("/api/v1/ingest/preview", json={"path": "   "}, headers=HDR).status_code == 422
    missing = c.post("/api/v1/ingest/preview",
                     json={"path": str(tmp_path / "没有这个.pdf")}, headers=HDR)
    assert missing.status_code == 404, missing.text
    docx = tmp_path / "a.docx"
    docx.write_bytes(b"x")
    assert c.post("/api/v1/ingest/preview", json={"path": str(docx)},
                  headers=HDR).status_code == 422
    assert c.post("/api/v1/ingest/preview", json={"path": str(tmp_path)},
                  headers=HDR).status_code == 422


def test_api_preview_requires_token(client, db, tmp_path):
    c, _ = client
    p = _mk_good_pdf(tmp_path, "api_auth.pdf")
    assert c.post("/api/v1/ingest/preview", json={"path": str(p)}).status_code == 401
    assert c.post("/api/v1/ingest/preview", json={"path": str(p)},
                  headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_api_blocked_doc_is_200_not_5xx(client, db, tmp_path):
    """坏文档 → HTTP 200 + verdict=block（不是 500，也不是 4xx）。"""
    c, token = client
    p = _mk_sparse_pdf(tmp_path, "api_block.pdf")
    r = c.post("/api/v1/ingest/preview", json={"path": str(p)}, headers=HDR)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["verdict"] == "block" and data["grade"] == "D"
    assert data["quarantine_candidate"] is True


def test_api_preview_allow_deep_is_wired_and_reported(client, db, tmp_path):
    """D5：`allow_deep=true` 从"422 拒绝"改为**真接线 + 如实标注**（替代原
    `test_api_preview_deep_not_supported`）。

    原契约是"显式要求深度通道 → 明确拒绝"，本意是**不偷偷外发**。D5 后安全性由
    三条共同保证，而不是靠拒绝：
      ① 不传 `allow_deep` ⇒ `egress == "none"`（默认绝不外发）；
      ② 传了 `allow_deep=true` ⇒ 请求被接受（不再 422）；
      ③ 此时 `egress` **必须如实变成非 `none`**，且 `deep_fallback_disabled is False`
         —— 即"不禁止，但必须留痕"（红线 4 / D2）。**偷偷外发仍然是被禁止的**。
    """
    c, token = client
    p = _mk_good_pdf(tmp_path, "api_deep.pdf")

    # ① 默认：不外发
    r0 = c.post("/api/v1/ingest/preview", json={"path": str(p)}, headers=HDR)
    assert r0.status_code == 200, r0.text
    d0 = r0.json()["data"]
    assert d0["egress"] == "none", d0.get("egress")
    assert d0["deep_fallback_disabled"] is True

    # ②③ 显式开启：接受 + 如实标注
    r = c.post("/api/v1/ingest/preview",
               json={"path": str(p), "allow_deep": True}, headers=HDR)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["egress"] != "none", data.get("egress")
    assert data["deep_fallback_disabled"] is False, data.get("deep_fallback_disabled")


def test_api_preview_allow_deep_non_bool_is_rejected(client, db, tmp_path):
    """`allow_deep` 必须**严格布尔**，且**只有真布尔 true 才开启**（独立复核 F4）。

    原实现是 `bool(body.get("allow_deep") or False)` ⇒ JSON 字符串 `"false"`
    是**真值**，于是"传了 false"反而**开启了外发**——与"默认安全"的设计意图直接冲突。
    同文件对 `paths`/`sample`/`limit_files`/`batch_size` 都做了严格校验，这里是唯一破口。
    ⇒ 非布尔一律 422（与其余字段的错误码一致：`preview_bad_request`）。
    """
    c, token = client
    p = _mk_good_pdf(tmp_path, "api_deep_type.pdf")

    for bad in ("false", "true", 1, 0, [], {}):
        r = c.post("/api/v1/ingest/preview",
                   json={"path": str(p), "allow_deep": bad}, headers=HDR)
        assert r.status_code == 422, f"allow_deep={bad!r} 应被拒绝，实际 {r.status_code}"
        assert "preview_bad_request" in r.text, r.text

    # 真布尔 true 仍然正常工作（不能被这次收紧误伤）
    r2 = c.post("/api/v1/ingest/preview",
                json={"path": str(p), "allow_deep": True}, headers=HDR)
    assert r2.status_code == 200, r2.text
    assert r2.json()["data"]["egress"] != "none"


def test_api_preview_accepts_extensionless_pdf(client, db, tmp_path):
    """**无扩展名的 PDF 必须被接受**（真机发现）：DSH 附件是哈希文件名。

    实测库内 `doc_meta.file_path` 形如 `…/Attachments/files/2026-09-01/1788220822060-cf6fe615`，
    按 `.pdf` 卡会把真实语料整片误拒 → 改为按魔数判定。
    """
    c, token = client
    src = _mk_good_pdf(tmp_path, "src.pdf")
    naked = tmp_path / "1788220822060-cf6fe615"
    naked.write_bytes(src.read_bytes())
    r = c.post("/api/v1/ingest/preview", json={"path": str(naked)}, headers=HDR)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["verdict"] in ("ok", "warn")


def test_api_preview_rejects_non_pdf_content(client, db, tmp_path):
    """内容是垃圾、后缀也不是 .pdf → 请求级 422（判定权在 dry_run，路由不重复实现）。"""
    c, token = client
    bogus = tmp_path / "notreally.bin"
    bogus.write_bytes(b"this is not a pdf at all")
    r = c.post("/api/v1/ingest/preview", json={"path": str(bogus)}, headers=HDR)
    assert r.status_code == 422, r.text
    assert "preview_unsupported_type" in r.text


def test_api_batch_and_inbox(client, db, batch_dir):
    c, token = client
    r = c.post("/api/v1/ingest/preview/batch",
               json={"dir": str(batch_dir), "sample": 0}, headers=HDR)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["conservation_ok"] is True
    assert sum(data["buckets"].values()) == data["evaluated"] > 0

    inbox = c.get(f"/api/v1/ingest/preview/inbox?dir={batch_dir}", headers=HDR)
    assert inbox.status_code == 200, inbox.text
    assert inbox.json()["data"]["count"] == data["total_candidates"]

    assert c.post("/api/v1/ingest/preview/batch", json={}, headers=HDR).status_code == 422
    assert c.post("/api/v1/ingest/preview/batch", json={"dir": str(batch_dir), "sample": -1},
                  headers=HDR).status_code == 422
    assert c.post("/api/v1/ingest/preview/batch",
                  json={"paths": "not-a-list"}, headers=HDR).status_code == 422
    assert c.get("/api/v1/ingest/preview/inbox?dir=Z:/没有", headers=HDR).status_code == 404
    empty = batch_dir / "empty"
    empty.mkdir()
    assert c.post("/api/v1/ingest/preview/batch", json={"dir": str(empty)},
                  headers=HDR).status_code == 404
