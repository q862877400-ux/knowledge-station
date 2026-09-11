# -*- coding: utf-8 -*-
"""把 API 密钥从 **Windows 系统层**搬进引擎自己的加密存储（2026-09-11 业主指令：不要动系统层）。

## 背景（真实事故）
2026-09-11 之前「设置→API 配置」把 Key 写进 `HKCU\\Environment`。而 DSH（DeepSeek Harness）
把**继承来的进程环境变量**当成最高优先级且只读的凭据来源、并在启动时冻结环境快照 ——
引擎一保存 Key，DSH 模型设置页的密钥输入框就被永久置灰（用户两次踩到）。
业主裁决：「不要动系统层」。引擎已改为把 Key 存进
`<data_dir>/secrets.json`（Windows DPAPI 用户态加密，见 `src/core/settings/secret_store.py`），
**保存动作再也不碰系统层**；本脚本负责把**已经写进去的旧条目**搬过来并清干净。

## ★ 搬完必须重启 DSH 宿主进程
删掉环境里的 `DEEPSEEK_API_KEY` 之后，**当前正在运行**的 DSH 宿主手里仍握着启动时那份
冻结的环境快照（DSH 源码 `packages/util/launch-environment/src/index.ts`：*Immutable
launch-time environment snapshot*）——所以它的模型设置页不会立刻变可写。请**重启 DSH 宿主**
（本项目的标准做法：桌面「DSH复活币X1」快捷方式）之后，DSH 才会重新读环境、落到它自己的
凭据文件（`~/.dsh/.credentials.yaml`）并把密钥输入框放开。**引擎侧不需要重启**。

## 用法（默认只打印计划，**零写入**）
    python scripts/ks-credentials-migrate.py                        # 看现状 + 计划
    python scripts/ks-credentials-migrate.py --apply                # 搬进加密存储（不删系统层）
    python scripts/ks-credentials-migrate.py --apply --clean-system  # 搬完并清掉系统层条目
    python scripts/ks-credentials-migrate.py --apply --clean-system --force
                                                                    # 冲突时也丢弃系统层旧值

安全设计：
* **先核对再删** —— 只有"加密存储里能读回、且与源值一致"的名字才允许从系统层删除；
  任何一步失败都中止删除，**不会**出现"删了但没搬成"。
* **不覆盖** —— 存储里已有值就保持不动（绝不把新 Key 冲回旧值），值不同则报冲突并拒绝删除。
* **只读回显** —— 全程只打印变量名与「在/不在/长度」，**绝不回显 Key 的值**。
* **进程环境变量删不掉** —— 本进程改不了别处的环境块；这些如实列在 `env_untouched` 里，
  请在「系统属性→环境变量」里手工删（或重启终端/宿主后再看）。
"""
from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":  # Windows spawn 会重导入本模块，入口必须守卫
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _plan(clean_system: bool, force: bool) -> list[str]:
    lines = [
        "权威存储: <data_dir>/secrets.json（Windows DPAPI 用户态加密，值不落明文）",
        "           —— 设置页保存的 Key 以后只写这里，系统层不再有一份",
        "系统层现状: HKCU\\Environment（引擎从此不再写入）",
    ]
    if clean_system:
        lines.append("动作: 搬进加密存储（先核对读回一致）→ 删除系统层里已验证的条目（破坏性）")
        lines.append("⚠ 删完请**重启 DSH 宿主进程**（桌面「DSH复活币X1」），"
                     "否则 DSH 仍握着启动时冻结的环境快照、其模型设置页不会放开")
        lines.append("⚠ 脚本不回显 Key：删系统层前请确认你有其它备份；回滚＝手工把值填回设置页")
    else:
        lines.append("动作: 只搬进加密存储；系统层条目原样保留（可随时回退，推荐先这样跑一次）")
        lines.append("提示: 想让 DSH 模型设置页恢复可写 → 需 --clean-system 清掉系统层，"
                     "并重启 DSH 宿主进程（桌面「DSH复活币X1」）")
    if force:
        lines.append("⚠ --force: 存储里已有不同值时，也丢弃系统层的旧值")
    return lines


def main(argv: list[str]) -> int:
    apply_ = "--apply" in argv
    clean_system = "--clean-system" in argv
    force = "--force" in argv
    if clean_system and not apply_:
        print("拒绝：--clean-system 必须与 --apply 同时使用（防误删系统层变量）。")
        return 2
    if force and not clean_system:
        print("拒绝：--force 只与 --clean-system 搭配使用（否则无意义且危险）。")
        return 2

    from src.core.settings.api_credentials import (
        adopt_legacy, clean_system_layer, import_system_layer, stored_channels,
        system_layer_status,
    )

    print("=== 系统层现状（只报存在性与长度，不显示值）===")
    rows = system_layer_status()
    for r in rows:
        if r["in_env"] or r["in_registry"]:
            print(f"  {r['name']}: 进程环境={'在' if r['in_env'] else '不在'} "
                  f"注册表={'在' if r['in_registry'] else '不在'} 长度={r['length']}")
    present = [r["name"] for r in rows if r["in_env"] or r["in_registry"]]
    print("  （无可搬条目）" if not present else f"  共 {len(present)} 条需要处理")

    print("\n=== 加密存储现状（只报布尔）===")
    for ch, st in stored_channels().items():
        print(f"  {ch}: api_key={'已存' if st['api_key'] else '未存'} "
              f"base_url={'已存' if st['base_url'] else '未存'}")

    print("\n=== 计划 ===")
    for line in _plan(clean_system, force):
        print("  " + line)

    if not apply_:
        print("\n（默认只打印计划，零写入。加 --apply 才执行。）")
        return 0

    res_llm = adopt_legacy("llm", delete_legacy=False, force=force)   # DEEPSEEK_* → KS_LLM_*
    res_imp = {ch: import_system_layer(ch, force=force)
               for ch in ("llm", "mineru_cloud")}                     # 同名搬家

    copied = list(dict.fromkeys(res_llm["copied"] + [n for r in res_imp.values() for n in r["copied"]]))
    verified = set(res_llm["verified"]) | {n for r in res_imp.values() for n in r["verified"]}
    skipped = list(dict.fromkeys(res_llm["skipped_kept"] + [n for r in res_imp.values() for n in r["skipped_kept"]]))
    conflicts = list(dict.fromkeys(res_llm["conflicts"] + [n for r in res_imp.values() for n in r["conflicts"]]))

    print("\n=== 结果 ===")
    print(f"  搬进加密存储: {copied or '（无）'}")
    print(f"  读回核对一致: {sorted(verified) or '（无）'}")
    if skipped:
        print(f"  保持不动（存储里已有值，绝不覆盖）: {skipped}")
    if conflicts:
        print(f"  ⚠ 冲突（存储与系统层值不同）: {conflicts}")

    deleted: list[str] = []
    env_untouched: list[str] = []
    if clean_system:
        # **先核对再删**：只有"加密存储里能读回、且与源值一致"（verified）的名字才允许删。
        # 存储里本来就有不同值的（skipped_kept/conflicts）默认不删——那是唯一样本；
        # 确实要丢弃系统层那份旧值时才加 --force。
        row_names = [r["name"] for r in rows]
        targets: set[str] = {n for n in row_names if n in verified}
        for old, new in (("DEEPSEEK_API_KEY", "KS_LLM_API_KEY"),
                         ("DEEPSEEK_BASE_URL", "KS_LLM_BASE_URL")):
            if new in verified:
                targets.add(old)
        if force:
            targets |= {n for n in row_names if n in skipped}
            targets |= {n for n in row_names if n in conflicts}
        out = clean_system_layer(sorted(targets))
        deleted, env_untouched = out["deleted"], out["env_untouched"]
        print(f"  已从系统层删除: {deleted or '（无）'}")
        if env_untouched:
            print(f"  ⚠ 仍在进程环境变量里、本脚本删不掉: {env_untouched}")
            print("     → 请在「系统属性→环境变量」里手工删除这些用户变量。")

    print("  未回显任何 Key 值。")
    if deleted:
        print("\n★ 下一步（必做）: 重启 DSH 宿主进程（桌面「DSH复活币X1」快捷方式），"
              "DSH 才会重新读环境、模型设置页的密钥输入框才恢复可写。引擎侧无需重启。")
    elif copied:
        print("\n提示: 系统层条目仍在 → DSH 仍可能把它们当只读凭据；"
              "要彻底清干净需 --clean-system（并重启 DSH 宿主）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
