# -*- coding: utf-8 -*-
"""云解析后端（mineru_cloud）单测：schema 守卫、归一化落位、zip-slip 防护、分发链。

零真实网络：httpx 与全流程函数均被替身。
"""
from __future__ import annotations

import json
import zipfile

import pytest

from src.core.ingestion import mineru_cloud
from src.core.ingestion.mineru_cloud import (
    MineruCloudError, _normalize_landing, _safe_extract, _validate_middle)


@pytest.fixture(autouse=True)
def _env_only_credentials(monkeypatch):
    """凭据只从环境变量读（屏蔽 HKCU 注册表回退），且 settings 不跨用例缓存。

    开发机可能已在「设置→API配置」配置真实云 Key（写 HKCU\\Environment）；
    不屏蔽的话 `_read_env_or_registry` 会读到它，使"未配置 Key"类用例
    语义反转（2026-09-08 真机实测踩到）。settings 重建保证用例内的
    monkeypatch.setenv 立即生效（无需每处显式 reset_settings）。
    """
    import os as _os

    from src.core import config

    def _env_only(name: str, default: str = "") -> str:
        return _os.environ.get(name, "").strip() or default

    monkeypatch.setattr(config, "_read_env_or_registry", _env_only)
    monkeypatch.setattr(config, "get_settings", lambda: config.Settings())
    yield


# ---------- schema 守卫 ----------
def _ok_middle(pages: int = 2) -> dict:
    return {"pdf_info": [
        {"page_idx": i, "para_blocks": None, "page_size": [595.0, 842.0]}
        for i in range(pages)]}


def test_validate_middle_passes(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_ok_middle()), encoding="utf-8")
    _validate_middle(p)  # 不抛即通过


def test_validate_middle_rejects_bad_json(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{not json", encoding="utf-8")
    # ⚠ 2026-10-09（第 17 轮）就地更正：这里原来 match `无法解析`，而实现（`mineru_cloud._validate_middle`
    #   → `middle_schema.load_middle_json`）**早就把文案改成了** `middle 产物读取/解析失败（m.json）: …`，
    #   外层再包一层「云产物 middle.json 非同构产物，拒绝消费…」⇒ 那条正则**永远匹配不上**、
    #   用例恒红（**判据与实现脱节**，不是实现坏了）。
    #   ⇒ 改成匹配**当前文案里真实存在**、且仍然专指"解析失败"的那一段。
    with pytest.raises(MineruCloudError, match="解析失败"):
        _validate_middle(p)


def test_validate_middle_rejects_missing_pdf_info(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"pages": []}), encoding="utf-8")
    with pytest.raises(MineruCloudError, match="pdf_info"):
        _validate_middle(p)


def test_validate_middle_rejects_empty_pages(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"pdf_info": []}), encoding="utf-8")
    with pytest.raises(MineruCloudError, match="pdf_info"):
        _validate_middle(p)


def test_validate_middle_rejects_missing_page_idx(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"pdf_info": [{"para_blocks": []}]}), encoding="utf-8")
    with pytest.raises(MineruCloudError, match="page_idx"):
        _validate_middle(p)


# ---------- 归一化落位 ----------
def test_normalize_landing_copies_and_prefixes(tmp_path):
    unpacked = tmp_path / "unpacked"
    (unpacked / "images").mkdir(parents=True)
    middle = unpacked / "middle.json"  # 云 zip 无前缀形态
    middle.write_text(json.dumps(_ok_middle()), encoding="utf-8")
    (unpacked / "images" / "abc.jpg").write_bytes(b"img")
    landing = _normalize_landing(unpacked, tmp_path, "gb24276", "batchid123456")
    auto = tmp_path / "mineru" / "cloud_batchid12345" / "auto"
    assert landing == str(auto.parent)
    m = auto / "gb24276_middle.json"  # 补 <stem>_ 前缀（rglob 契约）
    assert json.loads(m.read_text(encoding="utf-8"))["pdf_info"]
    assert (auto / "images" / "abc.jpg").read_bytes() == b"img"


def test_normalize_landing_keeps_existing_prefix(tmp_path):
    unpacked = tmp_path / "unpacked"
    unpacked.mkdir()
    (unpacked / "gb24276_middle.json").write_text(
        json.dumps(_ok_middle()), encoding="utf-8")
    landing = _normalize_landing(unpacked, tmp_path, "gb24276", "b123")
    assert (tmp_path / "mineru" / "cloud_b123" / "auto" /
            "gb24276_middle.json").exists()
    assert landing


def test_normalize_landing_no_middle_raises(tmp_path):
    unpacked = tmp_path / "unpacked"
    unpacked.mkdir()
    with pytest.raises(MineruCloudError, match="未找到 middle"):
        _normalize_landing(unpacked, tmp_path, "x", "b")


# ---------- zip 安全解压 ----------
def test_safe_extract_rejects_zip_slip(tmp_path):
    zp = tmp_path / "evil.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("../evil.txt", "boom")
    dest = tmp_path / "out"
    with pytest.raises(MineruCloudError, match="不安全路径"):
        _safe_extract(zp, dest)
    assert not (tmp_path / "evil.txt").exists()


def test_safe_extract_normal(tmp_path):
    zp = tmp_path / "ok.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("a/middle.json", "{}")
        zf.writestr("a/images/x.jpg", b"img")
    dest = tmp_path / "out"
    _safe_extract(zp, dest)
    assert (dest / "a" / "middle.json").exists()


# ---------- 可用性门 ----------
def test_available_false_without_key(monkeypatch):
    monkeypatch.delenv("KS_MINERU_CLOUD_API_KEY", raising=False)
    from src.core.config import reset_settings
    reset_settings()
    ok, why = mineru_cloud.mineru_cloud_available()
    assert not ok and "Key" in why


# ---------- 全流程（mock 网络层）----------
def test_submit_and_wait_end_to_end(tmp_path, monkeypatch):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    out_dir = tmp_path / "parse_out"

    def fake_apply(key, base, name):
        assert key == "tok" and name == "doc.pdf"
        return "batch-xyz", "https://upload.example/put"

    uploaded = {}

    def fake_put(url, content=None, headers=None, timeout=None):
        uploaded["url"] = url
        uploaded["data"] = content.read()

        class _R:
            status_code = 200

            def raise_for_status(self):
                pass

        return _R()

    def fake_poll(key, base, batch_id, name, deadline):
        assert batch_id == "batch-xyz"
        return "https://dl.example/zip"

    def fake_zip(url, dest):
        with zipfile.ZipFile(dest, "w") as zf:
            zf.writestr("doc_middle.json", json.dumps(_ok_middle()))
            zf.writestr("images/p1.jpg", b"img")

    monkeypatch.setattr(mineru_cloud, "_apply_upload_url", fake_apply)
    monkeypatch.setattr("httpx.put", fake_put)
    monkeypatch.setattr(mineru_cloud, "_poll_result", fake_poll)
    monkeypatch.setattr(mineru_cloud, "_download_zip", fake_zip)
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok")
    from src.core.config import reset_settings
    reset_settings()
    egress = []
    monkeypatch.setattr("src.core.llm.egress_audit.record_egress",
                        lambda *a, **k: egress.append((a, k)))

    r = mineru_cloud.mineru_cloud_submit_and_wait(pdf, out_dir)
    assert r and "output_dir" in r
    middle = list(out_dir.rglob("doc_middle.json"))
    assert len(middle) == 1
    assert (out_dir.rglob("images/p1.jpg").__next__().read_bytes() == b"img")
    assert uploaded["data"] == b"%PDF-fake"
    assert egress  # 外发审计已登记
    # 临时物已清理
    assert not (out_dir / "cloud_doc.zip").exists()
    assert not (out_dir / "cloud_doc_unpacked").exists()


def test_submit_and_wait_guard_failure_raises(tmp_path, monkeypatch):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")

    monkeypatch.setattr(mineru_cloud, "_apply_upload_url",
                        lambda *a: ("b", "https://u"))
    monkeypatch.setattr("httpx.put", lambda *a, **k: type("R", (), {
        "status_code": 200, "raise_for_status": lambda self: None})())
    monkeypatch.setattr(mineru_cloud, "_poll_result", lambda *a: "https://z")
    monkeypatch.setattr(mineru_cloud, "_download_zip",
                        lambda url, dest: None)
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok")
    from src.core.config import reset_settings
    reset_settings()

    def bad_extract(zp, dest):
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "junk.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(mineru_cloud, "_safe_extract", bad_extract)
    with pytest.raises(MineruCloudError, match="middle"):
        mineru_cloud.mineru_cloud_submit_and_wait(pdf, tmp_path / "out")


def test_submit_and_wait_network_failure_returns_none(tmp_path, monkeypatch):
    import httpx
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok")
    from src.core.config import reset_settings
    reset_settings()

    def boom(*a, **k):
        raise httpx.ConnectError("net down")

    monkeypatch.setattr(mineru_cloud, "_apply_upload_url", boom)
    r = mineru_cloud.mineru_cloud_submit_and_wait(pdf, tmp_path / "out")
    assert r is None  # 网络类失败 → 降级 None（上层维持既有链路）


# ---------- probe_token ----------
def test_probe_token_ok(monkeypatch):
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok")
    from src.core.config import reset_settings
    reset_settings()

    class _R:
        status_code = 200
        text = json.dumps({"code": 0, "data": {
            "batch_id": "b1", "file_urls": ["https://u"]}})

        def raise_for_status(self):
            pass

        def json(self):
            return json.loads(self.text)

    monkeypatch.setattr("httpx.post", lambda *a, **k: _R())
    r = mineru_cloud.probe_token()
    assert r["ok"] is True


def test_probe_token_bad_auth(monkeypatch):
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "bad")
    from src.core.config import reset_settings
    reset_settings()

    class _R:
        status_code = 401
        text = ""

    monkeypatch.setattr("httpx.post", lambda *a, **k: _R())
    r = mineru_cloud.probe_token()
    assert r["ok"] is False and "鉴权" in r["detail"]


# ---------- adapter 分发链 ----------
def test_adapter_uses_cloud_when_local_missing(monkeypatch, tmp_path):
    """本地未装 MinerU + 配了云 Key → 走云兜底（产物路径透传）。"""
    from src.core.ingestion import mineru_adapter
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok")
    from src.core.config import reset_settings
    reset_settings()
    monkeypatch.setattr(mineru_adapter, "mineru_available", lambda: False)
    calls = []
    monkeypatch.setattr("src.core.ingestion.mineru_cloud.mineru_cloud_submit_and_wait",
                        lambda pdf, out: calls.append((pdf, out)) or
                        {"output_dir": str(tmp_path / "landing")})
    r = mineru_adapter._mineru_deep_analyze(tmp_path / "doc.pdf", tmp_path / "out")
    assert r == {"output_dir": str(tmp_path / "landing")}
    assert len(calls) == 1


def test_adapter_no_local_no_key_returns_none(monkeypatch, tmp_path):
    from src.core.ingestion import mineru_adapter
    monkeypatch.delenv("KS_MINERU_CLOUD_API_KEY", raising=False)
    from src.core.config import reset_settings
    reset_settings()
    monkeypatch.setattr(mineru_adapter, "mineru_available", lambda: False)
    r = mineru_adapter._mineru_deep_analyze(tmp_path / "doc.pdf", tmp_path / "out")
    assert r is None


def test_adapter_no_key_uses_local_and_skips_cloud(monkeypatch, tmp_path):
    """未配置云 Key → 纯本地，云绝不被调用（2026-09-08 修订后语义）。"""
    from src.core.ingestion import mineru_adapter
    monkeypatch.delenv("KS_MINERU_CLOUD_API_KEY", raising=False)
    from src.core.config import reset_settings
    reset_settings()

    class _FakeDS:
        @staticmethod
        def deep_server_submit_and_wait(pdf, out, timeout=0):
            return {"output_dir": str(tmp_path / "local")}

    monkeypatch.setattr(mineru_adapter, "mineru_available", lambda: True)
    import sys
    fake_mod = type(sys)("src.core.ingestion.deep_server")
    fake_mod.deep_server_submit_and_wait = _FakeDS.deep_server_submit_and_wait
    monkeypatch.setitem(sys.modules,
                        "src.core.ingestion.deep_server", fake_mod)
    warned = []
    monkeypatch.setattr(
        "src.core.ingestion.mineru_cloud.mineru_cloud_submit_and_wait",
        lambda *a: warned.append(1))
    r = mineru_adapter._mineru_deep_analyze(tmp_path / "doc.pdf", tmp_path / "out")
    assert r == {"output_dir": str(tmp_path / "local")}
    assert not warned, "未配置 Key 时不应触云"


def test_adapter_ks_mineru_local_zero_forces_cloud(monkeypatch, tmp_path):
    """KS_MINERU_LOCAL=0（用户机器跑不动）→ 即使本地装了也直接走云。"""
    from src.core.ingestion import mineru_adapter
    monkeypatch.setenv("KS_MINERU_LOCAL", "0")
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok")
    from src.core.config import reset_settings
    reset_settings()
    monkeypatch.setattr(mineru_adapter, "mineru_available", lambda: True)
    calls = []
    monkeypatch.setattr(
        "src.core.ingestion.mineru_cloud.mineru_cloud_submit_and_wait",
        lambda pdf, out: calls.append(1) or {"output_dir": str(tmp_path)})
    r = mineru_adapter._mineru_deep_analyze(tmp_path / "doc.pdf", tmp_path / "out")
    assert r == {"output_dir": str(tmp_path)}
    assert calls == [1]


def test_egress_recorded_when_guard_fails_after_upload(tmp_path, monkeypatch):
    """P0 门禁（verifier F2）：PDF 字节已外发后产物守卫失败 → 仍登记外发审计
    （红线「云调用必走 egress_audit」；原实现只在全流程成功时登记）。"""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    egress = []
    monkeypatch.setattr("src.core.llm.egress_audit.record_egress",
                        lambda ch, path, meta, **kw: egress.append((ch, meta, kw)))
    monkeypatch.setattr(mineru_cloud, "_apply_upload_url", lambda *a: ("b", "https://u"))
    monkeypatch.setattr("httpx.put", lambda *a, **k: type("R", (), {
        "status_code": 200, "raise_for_status": lambda self: None})())
    monkeypatch.setattr(mineru_cloud, "_poll_result", lambda *a: "https://z")
    monkeypatch.setattr(mineru_cloud, "_download_zip", lambda url, dest: None)
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok")
    from src.core.config import reset_settings
    reset_settings()

    def bad_extract(zp, dest):
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "junk.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(mineru_cloud, "_safe_extract", bad_extract)
    with pytest.raises(MineruCloudError):
        mineru_cloud.mineru_cloud_submit_and_wait(pdf, tmp_path / "out")
    assert egress, "上传后失败必须留审计痕迹"
    meta = egress[-1][2].get("response_meta") or {}
    assert meta.get("ok") is False and "MineruCloudError" in str(meta.get("reason"))


def test_egress_recorded_when_poll_fails_after_upload(tmp_path, monkeypatch):
    """上传成功但轮询超时（网络类失败 → 返回 None）同样必须留审计。"""
    import httpx
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-fake")
    egress = []
    monkeypatch.setattr("src.core.llm.egress_audit.record_egress",
                        lambda ch, path, meta, **kw: egress.append((ch, meta, kw)))
    monkeypatch.setattr(mineru_cloud, "_apply_upload_url", lambda *a: ("b", "https://u"))
    monkeypatch.setattr("httpx.put", lambda *a, **k: type("R", (), {
        "status_code": 200, "raise_for_status": lambda self: None})())
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok")
    from src.core.config import reset_settings
    reset_settings()

    def poll_boom(*a):
        raise httpx.ReadTimeout("poll timeout")

    monkeypatch.setattr(mineru_cloud, "_poll_result", poll_boom)
    assert mineru_cloud.mineru_cloud_submit_and_wait(pdf, tmp_path / "out") is None
    assert egress, "上传后轮询失败必须留审计痕迹"
    meta = egress[-1][2].get("response_meta") or {}
    assert meta.get("ok") is False and "ReadTimeout" in str(meta.get("reason"))


def test_429_backs_off_and_retries_once(tmp_path, monkeypatch):
    """**限流 429 要原地退避重试一次**，而不是直接当网络失败返回 None。

    现场（2026-09-16 批 8/9 实测）：启动瞬间 24 并发齐射 → `file-urls/batch` 返回
    429，**一分钟内 87 条秒败**（`wall_s` 中位 0.2s），全部需重投 = 纯浪费，
    且秒败瞬间占满并发槽位。单账号探针已证明限流是**按速率**而非并发上限
    （单账号 24 并发持续 40 部零 429）→ 短暂退避即可恢复，不必降并发。

    本用例把退避的 `time.sleep` 换掉（否则测试要真等 5–10 秒），
    断言：**第一次抛 429 → 退避 → 第二次成功**，且**只重试一次**。
    """
    import httpx

    from src.core.config import reset_settings
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok")
    monkeypatch.setenv("KS_MINERU_CLOUD_BASE_URL", "https://example.invalid")
    reset_settings()

    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))

    calls = {"n": 0}

    def apply_upload_url(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.HTTPStatusError(
                "429 Too Many Requests", request=httpx.Request("POST", "https://x"),
                response=httpx.Response(429))
        return ("batch-1", "https://upload.invalid/put")

    monkeypatch.setattr(mineru_cloud, "_apply_upload_url", apply_upload_url)
    monkeypatch.setattr("httpx.put", lambda *a, **k: type("R", (), {
        "status_code": 200, "raise_for_status": lambda self: None})())
    monkeypatch.setattr(mineru_cloud, "_poll_result", lambda *a, **k: "https://zip.invalid/z")
    monkeypatch.setattr(mineru_cloud, "_download_zip", lambda *a, **k: None)
    monkeypatch.setattr(mineru_cloud, "_safe_extract", lambda *a, **k: None)
    monkeypatch.setattr(mineru_cloud, "_normalize_landing", lambda *a, **k: str(tmp_path / "land"))
    monkeypatch.setattr(mineru_cloud, "_record_egress_safe", lambda *a, **k: None)

    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4 minimal")
    r = mineru_cloud.mineru_cloud_submit_and_wait(pdf, tmp_path / "out")
    assert r is not None, "429 退避后应成功，而不是返回 None"
    assert calls["n"] == 2, f"应恰好重试一次（实际 {calls['n']} 次）"
    assert len(sleeps) == 1, f"应恰好退避一次（实际 {len(sleeps)} 次）"
    assert 5.0 <= sleeps[0] <= 10.0, f"退避应有 5–10s 抖动，实测 {sleeps[0]}"


def test_429_backoff_is_not_infinite(tmp_path, monkeypatch):
    """**429 持续存在时不许无限重试**——退避一次后仍失败就返回 None（交上层换 key）。

    判据靠显式参数 `_retried_429`（**不是 `locals()` 探测**——递归是新 scope，
    探测必然失效；写的时候踩过这个坑）。
    """
    import httpx

    from src.core.config import reset_settings
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok")
    monkeypatch.setenv("KS_MINERU_CLOUD_BASE_URL", "https://example.invalid")
    reset_settings()

    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    calls = {"n": 0}

    def always_429(*_a, **_k):
        calls["n"] += 1
        raise httpx.HTTPStatusError(
            "429 Too Many Requests", request=httpx.Request("POST", "https://x"),
            response=httpx.Response(429))

    monkeypatch.setattr(mineru_cloud, "_apply_upload_url", always_429)
    monkeypatch.setattr(mineru_cloud, "_record_egress_safe", lambda *a, **k: None)
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4 minimal")
    assert mineru_cloud.mineru_cloud_submit_and_wait(pdf, tmp_path / "out") is None
    assert calls["n"] == 2, f"应恰尝试 2 次（1 + 1 次退避重试），实际 {calls['n']}"
    assert len(sleeps) == 1, f"只许退避一次，实际 {len(sleeps)}"


def test_non_429_network_error_does_not_backoff(tmp_path, monkeypatch):
    """**反向对照：非 429 的网络错误不许退避**（它们不是速率问题，退避无益且白等）。

    尤其 `httpx.ConnectError` 没有 `response` → `status_code` 取不到 → 必须走原路径。
    """
    import httpx

    from src.core.config import reset_settings
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok")
    monkeypatch.setenv("KS_MINERU_CLOUD_BASE_URL", "https://example.invalid")
    reset_settings()

    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(mineru_cloud, "_record_egress_safe", lambda *a, **k: None)

    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4 minimal")
    for make_exc in (
        lambda: httpx.ConnectError("conn reset"),
        lambda: httpx.HTTPStatusError("500 oops", request=httpx.Request("POST", "https://x"),
                                      response=httpx.Response(500)),
    ):
        def boom(*_a, _mk=make_exc, **_k):
            raise _mk()

        monkeypatch.setattr(mineru_cloud, "_apply_upload_url", boom)
        assert mineru_cloud.mineru_cloud_submit_and_wait(pdf, tmp_path / "out") is None
    assert sleeps == [], f"非 429 不应退避，实测退避了 {sleeps}"


def test_explicit_api_key_overrides_global(tmp_path, monkeypatch):
    """**显式 `api_key` 必须覆盖全局 settings 的 key**（竞态治本的关键）。

    现场（2026-09-16 实测）：批量侧靠 `vlm_ocr.use_key()` 写**全局 settings**，
    而 key 在提交那一刻才读 → 24 线程各自 use_key 后并发提交，**线 A 设的 key
    被线 B 覆盖**。实测后果：
      · key 用量失衡到 `project 2037 / loop2 232 / loop3 6`（轮转形同虚设）；
      · 别名与实发 key 错配（日志 `key=project sk-HWq…`——project 配了 loop2 的 key）。
    本用例断言：**全局设的是 A、显式传的是 B → 实发必须是 B**。
    """
    from src.core.config import reset_settings
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "GLOBAL-KEY")
    monkeypatch.setenv("KS_MINERU_CLOUD_BASE_URL", "https://example.invalid")
    reset_settings()

    seen: list[str] = []
    monkeypatch.setattr(mineru_cloud, "_apply_upload_url",
                        lambda key, base, name: (seen.append(key), ("b", "https://u"))[1])
    monkeypatch.setattr("httpx.put", lambda *a, **k: type("R", (), {
        "status_code": 200, "raise_for_status": lambda self: None})())
    monkeypatch.setattr(mineru_cloud, "_poll_result", lambda *a, **k: "https://zip.invalid/z")
    monkeypatch.setattr(mineru_cloud, "_download_zip", lambda *a, **k: None)
    monkeypatch.setattr(mineru_cloud, "_safe_extract", lambda *a, **k: None)
    monkeypatch.setattr(mineru_cloud, "_normalize_landing", lambda *a, **k: str(tmp_path / "l"))
    monkeypatch.setattr(mineru_cloud, "_record_egress_safe", lambda *a, **k: None)

    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4 minimal")

    # 显式传 B → 实发必须是 B
    mineru_cloud.mineru_cloud_submit_and_wait(pdf, tmp_path / "o1",
                                              api_key="EXPLICIT-KEY")
    assert seen == ["EXPLICIT-KEY"], f"显式 key 未生效，实发 {seen}"

    # **反向对照**：不传 → 仍走全局（保证既有调用方语义不变）
    seen.clear()
    mineru_cloud.mineru_cloud_submit_and_wait(pdf, tmp_path / "o2")
    assert seen == ["GLOBAL-KEY"], f"未传时应沿用全局，实发 {seen}"

    # 传空串应视为"未指定"（走全局），而不是把 key 置空
    seen.clear()
    mineru_cloud.mineru_cloud_submit_and_wait(pdf, tmp_path / "o3", api_key="")
    assert seen == ["GLOBAL-KEY"], f"空串应回退全局，实发 {seen}"
