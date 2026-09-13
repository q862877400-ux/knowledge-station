# -*- coding: utf-8 -*-
"""MinerU 云解析后端（云优先通道；2026-09-01 架构反转，2026-09-08 通道优先级修订）。

设计（用户拍板 2026-09-01 / 修订 2026-09-08）：
- **用户在「设置→API 配置」配置了云解析 API Key 时，云是主通道**（云优先）；
- 云未配置、云调用失败、或显式 `KS_MINERU_CLOUD=0` 时，回落到本地
  MinerU（GPU 攒批服务 / 进程内 do_parse）；未配置 Key 时纯本地不外发；
- 云返回的 zip 产物**归一化成本地同构目录布局**（<stem>_middle.json + images/），
  下游 load_middle_items 只有一条解析路径，不感知云/本地（用户裁决：
  结构完全一致就不需要两套解析）；
- **schema 守卫**：云产物入口强校验 middle.json 结构，缺失/变形大声抛
  MineruCloudError（不静默降级）——提示服务端版本漂移需要人工介入；
- 全部云外发按红线登记 egress 审计。

官方 v4 协议（precision API）：
1. POST {base}/api/v4/file-urls/batch (Bearer token) → data.batch_id + file_urls[]
2. PUT file_urls[0] 上传 PDF（显式 Content-Length）
3. 轮询 GET {base}/api/v4/extract-results/batch/{batch_id} → state=done → full_zip_url
4. 下载 zip → 安全解压（防 zip-slip）→ schema 守卫 → 归一化落位
"""
from __future__ import annotations

import json
import logging
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import quote

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 5.0
DOWNLOAD_MAX_BYTES = 512 * 1024 * 1024


class MineruCloudError(RuntimeError):
    """云解析后端错误（配置/协议/产物守卫失败——大声报错不静默）。"""


def _resolve_settings() -> Tuple[str, str]:
    from src.core.config import get_settings
    s = get_settings()
    key = (s.mineru_cloud_api_key or "").strip()
    base = (s.mineru_cloud_base_url or "https://mineru.net").strip().rstrip("/")
    return key, base


def mineru_cloud_available() -> Tuple[bool, str]:
    """(可用?, Base URL 或未配置原因)。"""
    key, base = _resolve_settings()
    if not key:
        return False, "未配置云解析 API Key"
    if not base:
        return False, "未配置云解析 Base URL"
    return True, base


def _headers(key: str) -> Dict[str, str]:
    return {"Content-Type": "application/json",
            "Authorization": f"Bearer {key}"}


def _check_api_payload(payload: Any, op: str) -> None:
    if not isinstance(payload, dict):
        raise MineruCloudError(f"{op} 返回非对象: {payload!r}")
    code = payload.get("code", 0)
    if code not in (0, "0", None):
        raise MineruCloudError(f"{op} 失败: code={code} msg={payload.get('msg')!r}")


def probe_token() -> Dict[str, Any]:
    """活体探测：申请一次签名上传 URL 验证 token（不上传、不启动解析任务）。

    整改批 7（问题清单 #9）：探测也是真实出网调用（api/v4/file-urls/batch），
    按红线补登记 egress 审计——此前主链 3 处齐全、探测这一处无痕。
    **只在真的发出过 httpx 请求后才登记**（Key 未配置的提前返回没出网，
    登记反而制造假痕）；审计失败不阻塞探测结果。
    """
    ok_detail: Dict[str, Any] = {"ok": False, "detail": ""}
    went_on_the_wire = False    # 只有真正出网（httpx 已发出）才算云调用
    try:
        key, base = _resolve_settings()
        if not key:
            return {"ok": False, "detail": "云解析 API Key 未配置"}
        import httpx
        body = {"files": [{"name": "probe.pdf", "is_ocr": True}],
                "language": "ch", "enable_table": True, "enable_formula": True}
        went_on_the_wire = True
        r = httpx.post(f"{base}/api/v4/file-urls/batch", headers=_headers(key),
                       json=body, timeout=30.0)
        if r.status_code in (401, 403):
            ok_detail = {"ok": False, "detail": f"鉴权失败 (HTTP {r.status_code})，请检查 Key"}
        else:
            r.raise_for_status()
            payload = r.json() if r.text else {}
            _check_api_payload(payload, "探测申请上传地址")
            data = payload.get("data") or {}
            if data.get("batch_id") and data.get("file_urls"):
                ok_detail = {"ok": True, "detail": f"鉴权通过（batch {str(data['batch_id'])[:12]}…）"}
            else:
                ok_detail = {"ok": False, "detail": f"响应缺 batch_id/file_urls: {payload}"}
    except Exception as e:  # noqa: BLE001 —— 探测异常透出真实原因
        msg = str(e).strip().replace("\n", " ")[:200]
        ok_detail = {"ok": False, "detail": msg or type(e).__name__}
    finally:
        if went_on_the_wire:
            # 出网即登记（成功/失败/异常三态都留痕）；审计自身失败不阻塞探测。
            # 注意：finally 里只登记、**不 return**——finally 的 return 会吞掉
            # try 里的返回值与异常（Python 经典陷阱）。
            try:
                from src.core.llm.egress_audit import record_egress
                record_egress("mineru_cloud", "api/v4/file-urls/batch",
                              {"doc": "probe.pdf", "op": "probe"},
                              response_meta={"ok": bool(ok_detail.get("ok"))},
                              prompt_preview="[云解析(MinerU) 密钥探测]")
            except Exception:  # noqa: BLE001
                logger.warning("probe_token 的 egress 审计登记失败（继续）", exc_info=True)
    return ok_detail


def _apply_upload_url(key: str, base: str, upload_name: str) -> Tuple[str, str]:
    import httpx
    body = {"files": [{"name": upload_name, "is_ocr": True}],
            "language": "ch", "enable_table": True, "enable_formula": True}
    r = httpx.post(f"{base}/api/v4/file-urls/batch", headers=_headers(key),
                   json=body, timeout=30.0)
    r.raise_for_status()
    payload = r.json() if r.text else {}
    _check_api_payload(payload, "申请上传地址")
    data = payload.get("data") or {}
    batch_id = str(data.get("batch_id") or "")
    urls = data.get("file_urls") or []
    if not batch_id or not urls:
        raise MineruCloudError(f"申请上传地址响应缺 batch_id/file_urls: {payload}")
    u = urls[0]
    upload_url = str(u.get("url") or "") if isinstance(u, dict) else str(u or "")
    return batch_id, upload_url


def _poll_result(key: str, base: str, batch_id: str, upload_name: str,
                 deadline: float) -> str:
    import httpx
    poll_url = f"{base}/api/v4/extract-results/batch/{quote(batch_id, safe='')}"
    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"云解析轮询超时: {batch_id}")
        time.sleep(POLL_INTERVAL_S)
        r = httpx.get(poll_url, headers=_headers(key), timeout=30.0)
        r.raise_for_status()
        payload = r.json() if r.text else {}
        _check_api_payload(payload, "轮询解析结果")
        results = (payload.get("data") or {}).get("extract_result")
        if isinstance(results, dict):
            results = [results]
        if not isinstance(results, list):
            continue
        for it in results:
            if not isinstance(it, dict):
                continue
            fname = str(it.get("file_name") or "")
            if upload_name and fname and fname != upload_name:
                continue
            state = str(it.get("state") or "").lower()
            if state == "done":
                zurl = str(it.get("full_zip_url") or "")
                if not zurl:
                    raise MineruCloudError(
                        f"批次 {batch_id} 完成但缺 full_zip_url: {it}")
                return zurl
            if state == "failed":
                raise MineruCloudError(
                    f"批次 {batch_id} 解析失败: {it.get('err_msg') or it}")


def _download_zip(url: str, dest: Path) -> None:
    import httpx
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    # 2026-09-14（执行计划 v3 阶段 2c 排障）：trust_env=False 显式绕过
    # 本地代理（HTTP_PROXY/ALL_PROXY 指向 127.0.0.1:7897 clash 类）。
    # 实测：矿大 OSS/CDN 国内直连可用，经代理 CONNECT 反而被间歇性
    # SSL UNEXPECTED_EOF 掐断（原生 socket TLS ok vs httpx 走 env 代理必断）。
    # 三处 API 调用（file-urls/extract-results/OSS PUT）同为国内端点，
    # 统一豁免；如未来有海外端点需求，须重新评估。
    with httpx.Client(trust_env=False, timeout=120.0,
                      follow_redirects=True) as _client:
        with _client.stream("GET", url) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(256 * 1024):
                    total += len(chunk)
                    if total > DOWNLOAD_MAX_BYTES:
                        raise MineruCloudError(
                            f"云解析产物超过 {DOWNLOAD_MAX_BYTES} 字节上限")
                    f.write(chunk)


def _safe_extract(zip_path: Path, dest: Path) -> None:
    """解压（防 zip-slip：每项 resolve 后必须落在 dest 内）。"""
    dest.mkdir(parents=True, exist_ok=True)
    dest_res = str(dest.resolve())
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            target = str((dest / info.filename).resolve())
            if not target.startswith(dest_res):
                raise MineruCloudError(f"zip 内不安全路径: {info.filename}")
        zf.extractall(dest)


def _validate_middle(path: Path) -> None:
    """schema 守卫：云产物 middle.json 必须与本地同构（大声报错不静默）。

    同构判据（load_middle_items 消费的最小充分结构）：
    - JSON 对象；pdf_info 是非空列表；
    - 每页是 dict 且带 page_idx（para_blocks 允许 None——空页合法）。
    """
    try:
        mj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        raise MineruCloudError(
            f"云产物 middle.json 无法解析（服务端产物结构可能已变更）: {e}") from e
    pages = mj.get("pdf_info") if isinstance(mj, dict) else None
    if not isinstance(pages, list) or not pages:
        raise MineruCloudError(
            "云产物 middle.json 缺 pdf_info 列表（非同构产物，拒绝消费）")
    for i, page in enumerate(pages):
        if not isinstance(page, dict) or "page_idx" not in page:
            raise MineruCloudError(
                f"云产物 pdf_info[{i}] 缺 page_idx（非同构产物，拒绝消费）")


def _find_middle(unpacked: Path) -> Path:
    # 2026-09-14（阶段 2c 实测）：MinerU 云产物 zip 已不再带 *_middle.json，
    # 同构产物改名 layout.json（pdf_info/_backend/_version_name 结构一致，
    # 实测 batch 93f04cb7 产物）。按序尝试：middle 老命名 → layout 新命名。
    for pattern in ("*_middle.json", "middle.json", "layout.json"):
        cands = sorted(unpacked.rglob(pattern))
        if cands:
            return cands[0]
    cands = [p for p in unpacked.rglob("*.json") if "middle" in p.name.lower()]
    if cands:
        return cands[0]
    raise MineruCloudError(
        "云产物 zip 内未找到 middle.json/layout.json（服务端产物结构可能已变更，需要人工介入）")


def _normalize_landing(unpacked: Path, output_dir: Path, stem: str,
                       batch_id: str) -> str:
    """云产物归一化落位为本地 deep 同构布局。

    目标: output_dir/mineru/cloud_<batch12>/auto/<stem>_middle.json + images/…
    pipeline 消费契约 rglob("*_middle.json") → 文件名必须带 <stem>_ 前缀；
    middle 内 image_path 相对引用 images/<hash>.jpg → images/ 同层同摆。
    """
    middle = _find_middle(unpacked)
    _validate_middle(middle)
    auto = output_dir / "mineru" / f"cloud_{batch_id[:12]}" / "auto"
    auto.mkdir(parents=True, exist_ok=True)
    stem_pfx = f"{stem}_"
    name = middle.name
    if not name.startswith(stem_pfx):
        name = f"{stem}_{name}"
    shutil.copy2(middle, auto / name)
    for img_dir in unpacked.rglob("images"):
        if img_dir.is_dir():
            img_dest = auto / "images"
            img_dest.mkdir(parents=True, exist_ok=True)
            for f in img_dir.iterdir():
                if f.is_file():
                    shutil.copy2(f, img_dest / f.name)
            break
    return str(auto.parent)


def _record_egress_safe(pdf_name: str, batch_id: str, landing: str,
                        ok: bool, reason: str | None = None) -> None:
    """外发审计登记（红线：云调用必走 egress_audit）。审计失败不阻塞入库。

    2026-09-08 修复（verifier F2）：原实现只在**全流程成功**后登记——PDF 字节
    在 httpx.put 时就已外发，此后的产物守卫失败/轮询超时/网络失败全部无痕，
    恰是最需要留证的情形。现由调用方按 uploaded 标记在成功与失败两条路径都登记。
    """
    try:
        from src.core.llm.egress_audit import record_egress
        record_egress("mineru_cloud", "api/v4/extract",
                      {"doc": pdf_name, "batch_id": batch_id},
                      response_meta={"landing": landing, "ok": ok, "reason": reason},
                      prompt_preview=f"[云解析(MinerU) 入库直读] {pdf_name}")
    except Exception:  # noqa: BLE001 —— 审计失败不阻塞入库
        logger.warning("egress 审计登记失败（继续入库）", exc_info=True)


def mineru_cloud_submit_and_wait(pdf_path: Path, output_dir: Path,
                                 timeout: float = 1800.0) -> Dict[str, Any] | None:
    """云解析全流程（与 deep_server_submit_and_wait 同构语义）。

    返回 {"output_dir": <landing>}；网络类失败 → 记日志返回 None（调用方
    维持既有降级链路）；产物守卫失败 → 抛 MineruCloudError（大声不静默）。
    """
    import httpx
    key, base = _resolve_settings()
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    tmp_zip = output_dir / f"cloud_{pdf_path.stem}.zip"
    unpacked = output_dir / f"cloud_{pdf_path.stem}_unpacked"
    batch_id = ""
    landing = ""
    uploaded = False   # PDF 字节已外发的标记（此后任何失败都要留审计）
    try:
        batch_id, upload_url = _apply_upload_url(key, base, pdf_path.name)
        if not upload_url:
            raise MineruCloudError("申请上传地址响应缺上传 URL")
        size = pdf_path.stat().st_size
        with open(pdf_path, "rb") as f:
            r = httpx.put(upload_url, content=f,
                          headers={"Content-Length": str(size)}, timeout=600.0)
        r.raise_for_status()
        uploaded = True
        zurl = _poll_result(key, base, batch_id, pdf_path.name, deadline)
        _download_zip(zurl, tmp_zip)
        if unpacked.exists():
            shutil.rmtree(unpacked)
        _safe_extract(tmp_zip, unpacked)
        landing = _normalize_landing(unpacked, output_dir, pdf_path.stem, batch_id)
    except MineruCloudError as e:
        if uploaded:
            _record_egress_safe(pdf_path.name, batch_id, landing, ok=False,
                                reason=f"MineruCloudError: {e}")
        raise
    except (httpx.HTTPError, TimeoutError, OSError) as e:  # noqa: BLE001
        logger.warning("云解析失败（网络/超时类，回退上层降级链路）: %s", e)
        if uploaded:
            _record_egress_safe(pdf_path.name, batch_id, landing, ok=False,
                                reason=f"{type(e).__name__}: {e}")
        return None
    finally:
        for p in (tmp_zip, unpacked):
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                elif p.exists():
                    p.unlink()
            except OSError:
                pass
    _record_egress_safe(pdf_path.name, batch_id, landing, ok=True)
    logger.info("云解析完成 batch=%s landing=%s (%s)",
                batch_id, landing, pdf_path.name)
    return {"output_dir": landing}
