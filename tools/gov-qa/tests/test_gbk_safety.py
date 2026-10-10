"""测试：`audit-coverage.py` 的**每个**子命令都不得因 GBK 控制台崩掉。

## 为什么（spec 005 T108/T302）

本机控制台是 GBK，而该脚本的人看输出里有 `⚠` / `✓` / `←` 这类字符。
实测 `--answers` / `--targets` / `--fields` 三个子命令**直接 rc=1**
（`UnicodeEncodeError: 'gbk' codec can't encode character '\\u26a0'`）——
一个只读体检工具因为打不出一个符号就整个失败，**一条报告都出不来**。

⚠ T108 第一次只修了 `print(...)` 调用点，**漏了带 emoji 的变量**（`flag` 拼接进 f-string）
⇒ `--targets` 仍然崩。T302 才补齐。⇒ 本用例**逐个跑所有子命令**，
不依赖"我改了哪几行"。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT.parent.parent / ".venv" / "Scripts" / "python.exe"
SCRIPT = ROOT / "recon" / "audit-coverage.py"

SUBCMDS = ["--fields", "--answers", "--targets", "--dups", "--gate"]


def test_every_subcommand_survives_gbk_console():
    """**每个子命令**都必须 rc 0 或 1（1 = 它自己的"发现问题"退出码），**不得是 2**。

    实测崩掉时是 `rc=1` 且 stderr 有 `UnicodeEncodeError` ⇒ 所以还要查 stderr。
    """
    bad = []
    for a in SUBCMDS:
        r = subprocess.run([str(PY), str(SCRIPT), a], cwd=str(ROOT),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=600)
        err = (r.stderr or "")
        if "UnicodeEncodeError" in err or "codec can't encode" in err:
            bad.append((a, r.returncode, err.strip().splitlines()[-1:]))
        elif r.returncode not in (0, 1):
            bad.append((a, r.returncode, err.strip().splitlines()[-1:]))
    assert not bad, f"这些子命令崩了：{bad}"


def test_no_emoji_reaches_bare_print():
    """**结构判据**：带 emoji 的字符串不得直接进 `print(...)`。

    这条防的是 T108 的漏网形态 —— 当时我修了 `print("⚠ …")`，
    却漏了 `flag = "⚠ …"` 再 `print(f"…{flag}")` 的写法。
    """
    src = SCRIPT.read_text(encoding="utf-8")
    offenders = []
    for i, ln in enumerate(src.splitlines(), 1):
        code = ln.split("#", 1)[0]
        if "print(" not in code:
            continue
        if "safe_print(" in code:
            continue
        if any(ch in code for ch in ("⚠", "✅", "❌", "✓", "←", "→")):
            offenders.append(f"L{i}: {ln.strip()[:90]}")
    assert not offenders, "这些 print 里有 emoji，会 GBK 崩：\n" + "\n".join(offenders)
