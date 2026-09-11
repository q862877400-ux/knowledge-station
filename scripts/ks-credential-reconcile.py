# -*- coding: utf-8 -*-
"""引擎/DSH 凭据对账（整改批 2c / 问题清单 #6）。

背景：迁移删注册表后，引擎的 Key 权威在 `<data_dir>/secrets.json`（DPAPI），
DSH 自己的 Key 权威在 `~/.dsh/.credentials.yaml`——两边各自为政。若某天其中
一边换了值（比如在 DSH 设置页重新填了），另一边不会跟着变，可能出现
「插件能答、DSH 本体调用报错」的分叉，且此前没有任何工具能发现。

本工具：对齐「名字层面」+「值层面是否同源」：
- 名字对账：引擎加密存储里有哪些通道名；DSH credentials 文件里出现哪些名字；
- 值对账（安全方式）：两边都取 SHA-256 指纹（引擎侧在内存解密后哈希、DSH 侧
  直接读文件行哈希）——**绝不打印值，只比指纹**。指纹相同 = 同一把钥匙；
  指纹不同 = 已分叉，报告提示去哪边改。

用法:
    .venv/Scripts/python scripts/ks-credential-reconcile.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# 对账的名字集（引擎通道名 ↔ DSH 侧常见名，含改名映射）
PAIRS = [
    ("KS_LLM_API_KEY", "DEEPSEEK_API_KEY"),        # 引擎新名 ↔ DSH 侧沿用旧名
    ("KS_LLM_API_KEY", "DEEPSEEK_OFFICIAL_API_KEY"),  # DSH 侧官方渠道名
    ("KS_MINERU_CLOUD_API_KEY", "KS_MINERU_CLOUD_API_KEY"),  # 同名
]


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def engine_side() -> dict[str, str]:
    """引擎加密存储里的 {名字: 指纹}（内存解密后哈希，不打印值）。"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.core.settings import secret_store
    out: dict[str, str] = {}
    for n in secret_store.stored_names():
        v = secret_store.read_value(n)
        if v:
            out[n] = _sha(v)
    return out


def dsh_side() -> dict[str, str]:
    """~/.dsh/.credentials.yaml 里 {名字: 指纹}。

    YAML 解析不引依赖：逐行找 `  NAME: value` 模式，值哈希。
    文件不存在/解析不出 → 空 dict（如实报告）。
    """
    p = Path.home() / ".dsh" / ".credentials.yaml"
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_]+)\s*:\s*(\S+)\s*$", line)
        if m and not m.group(2).startswith("#"):
            out[m.group(1)] = _sha(m.group(2))
    return out


def main() -> int:
    eng = engine_side()
    dsh = dsh_side()

    print("=== 引擎 ↔ DSH 凭据对账（只比指纹，绝不打印值）===")
    print(f"引擎加密存储名字: {sorted(eng) or '（空）'}")
    print(f"DSH credentials 名字: {sorted(dsh) or '（空/文件不存在）'}")

    print("\n--- 通道对账 ---")
    findings: list[str] = []
    for eng_name, dsh_name in PAIRS:
        e_fp = eng.get(eng_name)
        d_fp = dsh.get(dsh_name)
        if e_fp is None and d_fp is None:
            print(f"  [{eng_name} ↔ {dsh_name}] 两边都未配置")
            continue
        if e_fp is None:
            print(f"  [{eng_name} ↔ {dsh_name}] 引擎未配置 / DSH 已配置")
            findings.append(f"{dsh_name}: DSH 有、引擎无（如需插件回答请去插件设置页配置）")
            continue
        if d_fp is None:
            print(f"  [{eng_name} ↔ {dsh_name}] 引擎已配置 / DSH 未配置")
            findings.append(f"{eng_name}: 引擎有、DSH 无（DSH 本体调用不受影响）")
            continue
        same = "指纹一致（同一把钥匙）" if e_fp == d_fp else "⚠ 指纹不同（两边已分叉！）"
        print(f"  [{eng_name} ↔ {dsh_name}] {same}")
        if e_fp != d_fp:
            findings.append(
                f"{eng_name}(引擎) 与 {dsh_name}(DSH) 值不同——"
                "若一边报错 401/invalid key，去报错那边的设置页重填即可（两边独立存储，互不覆盖）")

    print("\n=== 结论 ===")
    if findings:
        for f in findings:
            print(f"  · {f}")
    else:
        print("  两边同源一致，无分叉。")
    print("\n说明: 引擎与 DSH 的 Key 是两套独立存储（业主 2026-09-11 裁定的架构），")
    print("      本工具只发现分叉、不自动同步——以「哪边报错改哪边」为处置原则。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
