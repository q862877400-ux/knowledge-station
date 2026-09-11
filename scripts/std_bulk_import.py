# -*- coding: utf-8 -*-
"""国标批量入库 v2（覆盖式）：只入库 CSSN 已成功识别（results.jsonl found=True 且无 error）的国标 PDF。

v2 与 v1 的差异（2026-08 评审改版，用户指令"已入库就覆盖不要跳过"）：
- reingest=True 恒开：同 file_hash 不再报 duplicate、同标准号不再报 standard_exists，
  统一走"解析成功后删旧文档（用户资产按 clause_key 迁移）→ 单事务重建"的覆盖路径；
- 删除 done-set 断点跳过：进度文件只剩审计日志用途（记录每次成功与结果，不再用于跳过）；
  分段续跑改用确定性的 --start/--max 目录序切片（同一目录内容不变则切片稳定）；
- 标准名取 CSSN 官方名（raw.row.a298，31k 条全覆盖），文件名 stem 仅作兜底；
- 自动生成/复用 CCS 种子文件 <jsonl同级>/ccs_seed.json 并通过 KS_CCS_SEED_FILE 注入
  ccs_fetcher：入库时 CCS 直接本地命中免网络（避免对 3.1 万本逐本请求 cssn）；
- found 过滤放宽：found 且无 error 即算"CSSN完毕"（含 legal_status 未标注与 废止/被代替）。

流程：扫国标目录 → 文件名提取标准号 → 命中 CSSN 已识别集合 → run_full_ingest 逐本覆盖入库。

v3（2026-08-27 GPU 跑满改造，用户指令"要让GPU一直跑满"）：
- 预投递流水线：按窗口把文档先用 fitz 快速分文本层/扫描件（与解析器同一
  判定函数）——文本层直接 CPU 入库；扫描件立即投给常驻攒批 daemon 的队列；
  深度结果注入 run_parser_isolated monkeypatch，入库链零改动复用。

v4（2026-08-27 整片预投递）：v3 窗口级投递实测 GPU 在 99% 与 7% 之间锯齿
  （扫描件到达 ~1本/分，攒批窗只攒到 1 本）。改为开工时把整个切片一次性
  分拣并全量预投递——daemon 队列常年一两百本深，批次恒吃满，GPU 持续拉满。
  --lookahead 不再参与调度（保留参数兼容命令行）。

用法：
  python scripts/std_bulk_import.py --dir "<国标目录>" --jsonl "<体检结果>/results.jsonl"
      [--start K]      # 从确定性队列第 K 个开始（0 起，分段续跑）
      [--limit N]      # 只处理队列 [start, start+N)
      [--max N]        # 同 limit（兼容旧参数名，后台分批）
      [--lookahead N]  # 预投递窗口大小（0=关闭流水线，默认 24）
      [--dry-run]      # 只列将导入清单与计数
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.update.channels.base import norm_no  # noqa: E402

#: 文件名标准号提取（与 std_status_check.py 保持一致；兼容全角斜杠 ／）
_STD_RE = re.compile(
    r"^(GB\s*(?:[／/]Z|Z)?\s*(?:[／/]?\s*T)?)\s*(\d+(?:\.\d+)*)\s*[-—–]\s*(\d{4})")

SEED_NAME = "ccs_seed.json"


def _ensure_scnet_key() -> bool:
    r"""把用户配置的 SCNET_OCR_API_KEY 注入进程环境（子解析器继承）。

    顺序：当前进程已有 > 注册表 HKCU\Environment（setx/User 级）>
    HKLM 会话管理器 Environment（Machine 级）。**永不打印、不落盘密钥本身**，
    只报告来源作用域。OSI 调用时值仅透传给子进程环境。
    """
    if os.environ.get("SCNET_OCR_API_KEY"):
        return True
    try:
        import winreg
    except ImportError:          # 非 Windows（理论不会发生在本机）
        return False
    scopes = [
        (winreg.HKEY_CURRENT_USER, r"Environment", 0, "User"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
         winreg.KEY_WOW64_64KEY, "Machine"),
    ]
    for hive, path, extra, label in scopes:
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | extra) as k:
                val, _typ = winreg.QueryValueEx(k, "SCNET_OCR_API_KEY")
        except OSError:
            continue
        if isinstance(val, str) and val.strip():
            os.environ["SCNET_OCR_API_KEY"] = val.strip()
            print(f"[key] SCNET_OCR_API_KEY 取自 {label} 作用域"
                  f"（已注入，内容不回显）", flush=True)
            return True
    return False


def ensure_gpu_mode() -> None:
    """本地兜底解析默认走显卡（scnet 失败/低置信回退路径才真正用到）。"""
    os.environ.setdefault("MINERU_DEVICE_MODE", "cuda")


def load_cssn_info(jsonl: Path) -> dict[str, dict]:
    """CSSN 体检结果 → 归一号 {标准号: {name, ccs_code, ccs_name}}。

    过滤口径 v2：found 且无 error（不作 legal_status 要求——查到行但状态词未映射
    的同样算"识别成功"；废止/被代替/即将实施照常入库，有效性另存于库内字段）。
    同号多条（跨渠道补查场景）按最后一条为准，与体检断点逻辑一致。
    """
    info: dict[str, dict] = {}
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not d.get("found") or "error" in d:
            continue
        n = norm_no(d.get("standard_no") or "")
        if not n:
            continue
        info[n] = {
            "name": d.get("standard_name") or "",
            "ccs_code": d.get("ccs_code") or "",
            "ccs_name": d.get("ccs_name") or "",
        }
    return info


def write_ccs_seed(info: dict[str, dict], out_path: Path) -> int:
    """把体检已抓到的 CCS 写成种子文件（fetch_ccs 离线优先命中，免逐本打网络）。"""
    seed = {}
    for std, v in info.items():
        if v.get("ccs_code"):
            # 键 = 去空白归一形式（与 ccs_fetcher._seed_key 同一函数约定）
            key = std.upper().replace("／", "/").replace(" ", "")
            seed[key] = {"code": v["ccs_code"], "sub": v.get("ccs_name") or ""}
    out_path.write_text(json.dumps(seed, ensure_ascii=False, indent=0),
                        encoding="utf-8")
    return len(seed)


def scan_matching(root: Path, info: dict[str, dict]) -> tuple[list[tuple[str, Path, str]], int]:
    """扫目录 PDF，提取标准号并命中 CSSN 已识别集合。

    返回 [(标准号, pdf 路径, 标准名)]（确定性排序：sorted(rglob) 目录序），
    以及同标准号重复文件数（只导第一个，其余计为跳过重复）。
    """
    out: list[tuple[str, Path, str]] = []
    seen: set[str] = set()
    dup_files = 0
    for p in sorted(root.rglob("*.pdf")):
        m = _STD_RE.search(p.name)
        if not m:
            continue
        prefix = m.group(1).replace("／", "/").replace(" ", "").upper()
        std = f"{prefix} {m.group(2)}-{m.group(3)}"
        n = norm_no(std)
        if n not in info:
            continue                      # 未体检或查无 → 不属"CSSN完毕"，不入队
        meta = info[n]
        if n in seen:
            dup_files += 1                # 同标准多文件（不同副本/扫描版）只导第一个
            continue
        seen.add(n)
        out.append((std, p, meta.get("name") or p.stem))
    return out, dup_files


def _classify_text_layer(pdf: Path) -> bool:
    """快速文本层判定：与 parse_pdf_with_mineru 用同一个提取函数，口径一致。

    True = 有有效文本层（CPU 秒级入库，不占 GPU）；False = 扫描件（走 GPU 队列）。
    打不开/异常一律按扫描件处理，让深度路径去报真实错误。
    2026-08-28：PUA 错位字体（犌犅／犜）文本层不可用 → 按扫描件走 GPU。
    """
    from src.core.ingestion.mineru_adapter import (
        _extract_text_blocks, text_layer_pua_mangled)
    try:
        blocks = _extract_text_blocks(pdf)
        if not blocks or text_layer_pua_mangled(blocks):
            return False
        return True
    except Exception:  # noqa: BLE001
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--start", type=int, default=0,
                    help="从队列第 K 个开始（0 起；确定性目录序切片，供后台分批续跑）")
    ap.add_argument("--limit", type=int, default=0, help="最多处理 N 个（0=不限）")
    ap.add_argument("--max", type=int, default=0, help="同 limit（兼容旧参数名）")
    ap.add_argument("--lookahead", type=int, default=24,
                    help="预投递窗口大小（0=关闭流水线逐本同步；默认 24）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--progress", default=None,
                    help="审计日志路径（默认 <jsonl同级>/bulk_import_audit.log，仅记录不复用作跳过）")
    args = ap.parse_args()
    batch_cap = args.limit or args.max     # 0 = 不限

    info = load_cssn_info(Path(args.jsonl))
    print(f"[load] CSSN 已识别标准 {len(info)} 个", flush=True)

    seed_path = Path(args.jsonl).parent / SEED_NAME
    n_seed = write_ccs_seed(info, seed_path)
    os.environ["KS_CCS_SEED_FILE"] = str(seed_path)   # ccs_fetcher 离线优先命中
    print(f"[seed] CCS 种子已写 {n_seed} 条 → {seed_path}", flush=True)

    # OCR 选路（2026-08-27 用户规则）：scnet 云 API 主通道；失败/低置信才本地 GPU
    has_key = _ensure_scnet_key()
    ensure_gpu_mode()
    print("[ocr-mode] scnet API=主通道" + ("（键已就绪）" if has_key else
          "（⚠未见 Key——扫描件将整本走显卡兜底；配置方法见任务说明）")
          + " | 本地兜底设备=cuda（可用时）", flush=True)

    queue, dup_files = scan_matching(Path(args.dir), info)
    print(f"[scan] 目录内命中已识别国标 {len(queue)} 个"
          f"（同标准重复文件 {dup_files} 个仅导首个）", flush=True)
    end = args.start + batch_cap if batch_cap else len(queue)
    batch = queue[args.start:end]
    if not batch:
        # 战役驱动器契约：exit 3 = 队列已尽（start 超出确定性队列长度）
        print(f"[batch] 队列已到尾（start={args.start} ≥ {len(queue)}），无可处理项", flush=True)
        return 3
    print(f"[batch] 本次 {args.start}..{min(end, len(queue))} 共 {len(batch)} 个"
          f"（覆盖式：已入库文档将删除重建）", flush=True)

    if args.dry_run:
        for std, p, name in batch[:40]:
            nm = name[:30]
            print(f"  {std} | {p.name[:66]} | 官方名: {nm}")
        if len(batch) > 40:
            print(f"  ... 其余 {len(batch) - 40} 个略")
        return 0

    audit = Path(args.progress) if args.progress else \
        Path(args.jsonl).parent / "bulk_import_audit.log"

    # pipeline 在调用期才 import ccs_fetcher，env 已就位；此 import 放在 main 里防提前触发联网模块装配
    import src.core.ingestion.pipeline as _pl
    from src.core.ingestion.pipeline import run_full_ingest  # noqa: E402

    # ---- 深度结果注入：daemon 预解析完成的文档，跳过旧版逐本 spawn 解析 ----
    _pre_parsed: dict[str, dict] = {}
    _orig_rpi = _pl.run_parser_isolated

    def _rpi_with_injection(pdf_path, out_dir, force_deep=True):
        inj = _pre_parsed.pop(str(Path(pdf_path).resolve()), None)
        if inj is not None:
            # 2026-08-28 修复：注入字典必须补全 run_full_ingest 消费的完整
            # result 形状——L505 裸访问 result["geometries"]，缺键即
            # KeyError（daemon 修好后队列流动，⚡收割文档当场全灭）。
            from src.core.ingestion.mineru_adapter import extract_page_geometries
            inj.setdefault("geometries", extract_page_geometries(Path(pdf_path)))
            inj.setdefault("blocks", [])
            inj.setdefault("is_ocr", True)
            print(f"   ⚡ 复用 GPU 队列预解析结果", flush=True)
            return inj
        # 2026-08-28 修复（生产头号杀手）：必须用**关键字**传 force_deep——
        # 旧代码按位置传参，落进 run_parser_isolated 的第三参 timeout
        # （float(True)=1.0s）→ 所有非注入文档 1 秒被杀（审计 "(Trues)"），
        # 且 force_deep 恒 False → 文本层文档从不触发云 OCR/GPU 兜底。
        return _orig_rpi(pdf_path, out_dir, force_deep=force_deep)

    _pl.run_parser_isolated = _rpi_with_injection

    from src.core.config import get_settings  # noqa: E402
    from src.core.ingestion.deep_server import (  # noqa: E402
        deep_server_submit, deep_server_wait)

    audit = Path(args.progress) if args.progress else \
        Path(args.jsonl).parent / "bulk_import_audit.log"
    ok = fail = 0
    stats = {"gpu_docs": 0}

    def _ingest_and_audit(std: str, pdf: Path, name: str) -> None:
        """单本入库 + 审计 + 控制台（覆盖式语义与 v2 完全一致）。"""
        nonlocal ok, fail
        try:
            out = run_full_ingest(pdf, std, name, doc_type="standard",
                                  domain_tags=[], legal_hierarchy="GB",
                                  reingest=True)          # v2：恒覆盖
            status = out.get("status")
            if status == "ok":
                ok += 1
                warn = out.get("span_warning")
                with audit.open("a", encoding="utf-8") as pf:
                    pf.write(json.dumps({
                        "ts": datetime.now().isoformat(timespec="seconds"),
                        "std": std, "status": status,
                        "clauses": out.get("total_clauses"),
                        "reingested": bool(out.get("reingested")),
                    }, ensure_ascii=False) + "\n")
                print(f"   ✅ clauses={out.get('total_clauses')}"
                      + ("  ⚠span告警" if warn else ""), flush=True)
                if warn:
                    with audit.open("a", encoding="utf-8") as pf:
                        pf.write(json.dumps({"ts": datetime.now().isoformat(
                            timespec="seconds"), "std": std,
                            "status": "span_warning", "msg": warn},
                            ensure_ascii=False) + "\n")
            else:
                fail += 1
                msg = str(out.get("message", ""))[:120]
                with audit.open("a", encoding="utf-8") as pf:
                    pf.write(json.dumps({"ts": datetime.now().isoformat(
                        timespec="seconds"), "std": std, "status": status,
                        "pdf": str(pdf), "msg": msg}, ensure_ascii=False) + "\n")
                print(f"   ❌ {status}: {msg}", flush=True)
        except Exception as e:  # noqa: BLE001
            fail += 1
            with audit.open("a", encoding="utf-8") as pf:
                pf.write(json.dumps({"ts": datetime.now().isoformat(
                    timespec="seconds"), "std": std, "status": "exception",
                    "pdf": str(pdf), "msg": f"{type(e).__name__}: {e}"[:160]},
                    ensure_ascii=False) + "\n")
            print(f"   ❌ 异常: {type(e).__name__}: {str(e)[:110]}", flush=True)

    def _preflight_slice(batch: list) -> dict:
        """v4 整片预分拣 + 全量预投递（2026-08-27 实测驱动）。

        窗口级预投递（v3）下扫描件到达速率 ~1本/分 → daemon 攒批窗内只攒到
        1 本，GPU 占空比在 99%（批=10 的波峰）与 7%（断粮）之间锯齿。改为
        开工时把整个切片用 fitz 快速分文本层/扫描件（不解析，每本零点几秒），
        **全部扫描件一次性投进 GPU 队列**（一个切片通常一两百本）→ daemon
        队列常年数百本深，批次永远吃满 10 本；文本层随后纯 CPU 入库不占 GPU。
        返回 {pdf绝对路径: deep_server_submit 返回值}。
        """
        pre: dict[str, dict] = {}
        n_text = n_scan = 0
        for i, (std, pdf, name) in enumerate(batch, 1):
            if _classify_text_layer(pdf):
                n_text += 1
            else:
                out_dir = get_settings().data_dir / "parse_out" / \
                    f"pre_{time.time_ns():024d}"
                sub = deep_server_submit(pdf, out_dir)
                if sub is not None:        # None=开关关闭 → 留给旧路径逐本兜底
                    pre[str(pdf.resolve())] = sub
                    n_scan += 1
            if i % 100 == 0:
                print(f"   🔎 片区分拣 {i}/{len(batch)}"
                      f"（文本层 {n_text} / 扫描件 {n_scan}）", flush=True)
        stats["gpu_docs"] += n_scan
        print(f"[preflight] 片区分拣完成：文本层 {n_text} 本（CPU 直入）"
              f"｜扫描件 {n_scan} 本（已全部预投递 GPU 队列）", flush=True)
        return pre

    pre_subs = _preflight_slice(batch)

    def _handle_doc(std: str, pdf: Path, name: str) -> None:
        """单本处理：扫描件等预投递结果（通常已解析完）注入入库；文本层直入。"""
        key = str(pdf.resolve())
        sub = pre_subs.pop(key, None)
        if sub is not None:
            # 2026-08-28 修复：等待上限 3600→28800s。整片预投递下队列深达
            # 数千本，3600s 只够排到队头 ~120 本；其余全部超时 → 落 inline
            # 重复投递 + 再超时 → 文档假失败 + 队列雪崩式膨胀。FIFO 按序
            # 收割，结果一到即返回，8h 只是兜底上限。
            r = deep_server_wait(sub, timeout=28800.0)
            if r and r.get("output_dir"):
                _pre_parsed[key] = {"deep_output": str(r["output_dir"])}
            _ingest_and_audit(std, pdf, name)
            _pre_parsed.pop(key, None)    # 防串档：每本用完即清
        else:
            _ingest_and_audit(std, pdf, name)

    print(f"[flow] 整片预投递流水线：{len(batch)} 本"
          f"（GPU 队列已满载，按序收割入库）", flush=True)
    for std, pdf, name in batch:
        _handle_doc(std, pdf, name)

    with audit.open("a", encoding="utf-8") as pf:
        pf.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"),
                             "status": "batch_summary", "ok": ok, "fail": fail,
                             "gpu_docs": stats["gpu_docs"],
                             "range": [args.start, min(end, len(queue))]},
                            ensure_ascii=False) + "\n")
    print(f"\n完成: 成功 {ok} / 失败 {fail}（GPU 深度 {stats['gpu_docs']} 本）"
          f"（审计日志 {audit}；失败项可重跑该批——覆盖式不会漏也不会卡死序位）",
          flush=True)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
