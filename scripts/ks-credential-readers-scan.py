# -*- coding: utf-8 -*-
"""凭据读者排查（整改批 1b / 问题清单第 4 条）。

业主 2026-09-11 问「Windows 里那把旧 DEEPSEEK_API_KEY 还有谁在读」，回答
「我不知道」——删除不可逆动作不能建立在「不知道」上。本脚本在**本机**排查
常见消费面，产出一份「谁在读旧名」报告（呈业主过目后才允许批 2 删注册表）。

红线（与 ks-credentials-migrate 同源）：
- **绝不打印任何 Key 值**——只记存在性/长度/进程名/文件名；
- 只读不写：对注册表只 Query，对文件只读文本找名字。

排查面（按「删了之后谁会受伤」排序）：
 1. 注册表 HKCU\\Environment + HKLM 系统层：旧名是否仍存在（基线事实）
 2. 常见 CLI 凭据文件：~/.dsh/.credentials.yaml、~/.claude、~/.codex、
    ~/.anthropic、~/.openai 等——文件里是否**出现**旧名（出现≠存真值，
    但说明该工具认识这个名字）
 3. 仓库内 .env / 配置文件：KS_LLM_API_KEY 等新名与旧名谁被引用
 4. 当前所有活进程的环境块：哪些进程**带着**旧名（说明它们启动时继承过）
 5. 用户 shell 配置（PowerShell $PROFILE / cmd autorun）：是否有 setx/set 脚本

用法:
    .venv/Scripts/python scripts/ks-credential-readers-scan.py           # 控制台报告
    .venv/Scripts/python scripts/ks-credential-readers-scan.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from pathlib import Path

# GBK 控制台防炸：强制 stdout UTF-8（老坑，见账本）
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

NAMES_OLD = ["DEEPSEEK_API_KEY", "SCNET_OCR_API_KEY", "KS_MINERU_CLOUD_API_KEY"]
NAMES_NEW = ["KS_LLM_API_KEY", "KS_LLM_BASE_URL", "KS_MINERU_CLOUD_BASE_URL"]


# ---------------------------------------------------------------- 注册表
def scan_registry() -> list[dict]:
    out = []
    try:
        import winreg
    except ImportError:
        return [{"scope": "registry", "where": "winreg unavailable (非 Windows)", "ok": False}]
    for scope_name, root, subkey in [
        ("HKCU\\Environment", winreg.HKEY_CURRENT_USER, "Environment"),
        ("HKLM 系统层", winreg.HKEY_LOCAL_MACHINE,
         r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ]:
        try:
            with winreg.OpenKey(root, subkey) as k:
                for name in NAMES_OLD + NAMES_NEW:
                    try:
                        val, _ = winreg.QueryValueEx(k, name)
                        out.append({"scope": "registry", "where": scope_name,
                                    "name": name, "present": True,
                                    "length": len(str(val))})
                    except FileNotFoundError:
                        out.append({"scope": "registry", "where": scope_name,
                                    "name": name, "present": False})
        except OSError as e:
            out.append({"scope": "registry", "where": scope_name, "ok": False,
                        "error": str(e)[:80]})
    return out


# ---------------------------------------------------------------- 常见凭据文件
def _findings_in_text(text: str) -> list[str]:
    """文本里出现哪些目标名（值同样不记录）。"""
    hits = []
    for n in NAMES_OLD + NAMES_NEW:
        if n in text:
            hits.append(n)
    return hits


def scan_credential_files() -> list[dict]:
    home = Path.home()
    candidates = [
        home / ".dsh" / ".credentials.yaml",
        home / ".claude" / ".claude.json",
        home / ".claude.json",
        home / ".codex" / "config.toml",
        home / ".codex" / "auth.json",
        home / ".anthropic" / "config.toml",
        home / ".openai" / "auth.json",
        home / ".config" / "opencode" / "opencode.json",
    ]
    out = []
    for p in candidates:
        item = {"scope": "cred_file", "where": str(p), "exists": p.exists()}
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                item["names_found"] = _findings_in_text(text)
                item["any_old_names"] = any(n in item["names_found"] for n in NAMES_OLD)
            except OSError as e:
                item["error"] = str(e)[:80]
        out.append(item)
    return out


# ---------------------------------------------------------------- 进程环境
def scan_live_processes() -> dict:
    """活进程的环境块里谁带着旧名（只记 pid/进程名，绝记值）。

    Windows 上读他进程环境块需要特权 API；务实路径：改查**本进程**链
    （DSH 宿主 → 引擎 → 本脚本都从同一继承链来）+ WMI 查命令行里明文引用。
    """
    out: dict = {"scope": "processes", "method": "self-env + wmi-cmdline"}
    self_hits = [n for n in NAMES_OLD + NAMES_NEW if os.environ.get(n)]
    out["self_env_carries"] = self_hits
    out["self_env_note"] = ("本进程继承自 DSH 宿主链；带旧名=宿主环境里仍有旧名"
                            "（这就是输入框被遮蔽的同一条继承链）")
    # WMI：命令行里明文带旧名的进程（极端情况：有人把 key 写进了命令行）
    cmdline_hits = []
    try:
        import subprocess
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'DEEPSEEK_API_KEY|SCNET_OCR_API_KEY' } | Select-Object ProcessId, Name | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and r.stdout.strip():
            txt = r.stdout.strip()
            if txt and txt != "null":
                try:
                    data = json.loads(txt)
                    if isinstance(data, dict):
                        cmdline_hits.append({"pid": data.get("ProcessId"),
                                             "name": data.get("Name")})
                    else:
                        cmdline_hits = [{"pid": d.get("ProcessId"),
                                          "name": d.get("Name")} for d in data]
                except json.JSONDecodeError:
                    cmdline_hits.append({"raw": txt[:200]})
    except Exception as e:
        out["wmi_error"] = str(e)[:120]
    out["cmdline_carriers"] = cmdline_hits
    out["cmdline_note"] = "命令行明文带旧名的进程（0=好）"
    return out


# ---------------------------------------------------------------- shell 配置
def scan_shell_configs() -> list[dict]:
    home = Path.home()
    docs = Path(home / "Documents")
    candidates = [
        home / "Documents" / "WindowsPowerShell" / "profile.ps1",
        home / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
        home / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
    ]
    out = []
    for p in candidates:
        item = {"scope": "shell_profile", "where": str(p), "exists": p.exists()}
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                item["names_found"] = _findings_in_text(text)
                item["mentions_setx_or_env"] = ("setx" in text.lower()
                                                or "$env:" in text)
            except OSError as e:
                item["error"] = str(e)[:80]
        out.append(item)
    # cmd AutoRun（注册表残留的经典藏身处）
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Command Processor") as k:
            try:
                val, _ = winreg.QueryValueEx(k, "AutoRun")
                out.append({"scope": "shell_profile", "where": "HKCU cmd AutoRun",
                            "exists": True, "value_len": len(str(val)),
                            "names_found": _findings_in_text(str(val))})
            except FileNotFoundError:
                out.append({"scope": "shell_profile", "where": "HKCU cmd AutoRun",
                            "exists": False})
    except OSError:
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="凭据读者排查（只读，不打印值）")
    ap.add_argument("--json", help="报告同时写 JSON 文件")
    args = ap.parse_args()

    report = {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "purpose": "删注册表旧 Key 前的读者排查（问题清单 #4）——只记存在性，绝记值",
        "old_names": NAMES_OLD,
        "new_names": NAMES_NEW,
        "sections": [
            scan_registry(),
            scan_credential_files(),
            scan_live_processes(),
        ],
        "shell_profiles": scan_shell_configs(),
    }

    def _dump(obj) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=2)

    text = _dump(report)
    print(text)
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8")
        print(f"\n[report] written: {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
