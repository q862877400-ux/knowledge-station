"""渠道台账状态快照（§11.0 R3c）：把实机库里的渠道台账导成**人可读**的 Markdown。

三个用途：
1. 业主**今天**就能看（面板 R4 还没做，且端点要等引擎重启才对外）；
2. 它是 R4 面板的**列定义草案**——面板要显示的列就是本表这些列；
3. 每次跑都是"当时的实测状态"，所以它必须带生成时间与数据来源（不许当成长期结论）。

用法：`.venv\\Scripts\\python.exe scripts\\channel-status-report.py [输出路径]`
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import get_settings  # noqa: E402
from src.core.storage import channel_repo as cr  # noqa: E402
from src.core.update import channel_probe as cp  # noqa: E402

CAT_LABEL = {
    "law": "法规", "std_gb": "国标", "std_hb": "行标", "std_db": "地标", "std_tb": "团标",
    "std_intl": "国际", "aggregator": "聚合入口", "tool": "工具/Skill",
    "internal": "我方通路", "other": "其他",
}
WIRING_LABEL = {
    "wired": "✅ 已接线（在 routing 链上）",
    "unwired": "⚪ 未接线（注册了但巡检不调用）",
    "broken": "❌ 已知失效（在链上但实测不工作）",
    "user": "👤 用户自加",
    "seed_only": "📋 仅登记（调研得来，尚未接线）",
}
STATE_LABEL = {"ok": "🟢 可抓", "suspicious": "🟡 可疑", "down": "🔴 不可抓",
               "unknown": "⚪ 未探"}


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        ROOT / "docs" / "research" / "channels" / "REGISTRY-STATUS.md")
    rows = cr.list_channels()
    s = cr.summary()
    targets = cp.load_targets()
    lines: list[str] = [
        "# 渠道台账状态快照（自动生成，勿手改）",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}（本地）"
        f" · 数据来源：`{get_settings().db_path}` 的 `update_channel` 表",
        f"- 台账 **{s['total']}** 条 · 启用 {s['enabled']} 条 · "
        f"**能干活（wired）{s['by_wiring']['wired']}** 条 · "
        f"已知失效 **{s['by_wiring']['broken']}** 条 · 仅登记 {s['by_wiring']['seed_only']} 条",
        f"- 已实测：🟢 {s['by_state']['ok']} / 🟡 {s['by_state']['suspicious']} / "
        f"🔴 {s['by_state']['down']} / ⚪ 未探 {s['by_state']['unknown']}",
        "",
        "> ⚠ 两个数字**必须分开读**：`台账条数` 是「我们知道多少渠道」，`能干活条数` 才是"
        "「今天真的能用几条」。R1 的实测教训（G5/G6）：13 个适配器只有 8 个在链上，"
        "而在链上的 `web`/`govcn` 两根兜底棒在真实 HTML 下恒 miss。",
        "",
        "## 一、我方通路（适配器与采集链路）",
        "",
        "| 渠道 | 接线 | 有效性 | 上次成功 | 失败原因 | 链接 |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted([r for r in rows if r["category"] == "internal"],
                    key=lambda r: (r["wiring"] != "wired", r["channel_id"])):
        lines.append(
            f"| `{r['channel_id']}` {r['name']} | {WIRING_LABEL.get(r['wiring'], r['wiring'])} | "
            f"{STATE_LABEL.get(r['state'], r['state'])} | {r['last_ok_at'] or '—'} | "
            f"{(r['last_error'] or '—')[:60]} | {(r['url'] or '—')[:70]} |")

    lines += ["", "## 二、外部渠道（按类别）", ""]
    for cat in cr.CATEGORIES:
        group = [r for r in rows if r["category"] == cat and r["category"] != "internal"]
        if not group:
            continue
        lines += [f"### {CAT_LABEL.get(cat, cat)}（{len(group)} 条）", "",
                  "| 渠道 | 有效性 | 上次成功 | 探针 | 链接 |",
                  "|---|---|---|---|---|"]
        for r in sorted(group, key=lambda r: (r["state"] != "ok", r["name"])):
            has = "有" if r["channel_id"] in targets else "—"
            lines.append(
                f"| {r['name']} | {STATE_LABEL.get(r['state'], r['state'])} | "
                f"{r['last_ok_at'] or '—'} | {has} | {(r['url'] or '—')[:66]} |")
        lines.append("")

    if s["by_wiring"]["broken"]:
        lines += ["## 三、已知失效（**这些会让覆盖率虚高，优先修/换**）", ""]
        for r in rows:
            if r["wiring"] == "broken":
                lines.append(f"- `{r['channel_id']}` **{r['name']}**：{r['note'] or '（无说明）'}")
        lines.append("")

    unknown = [r for r in rows if r["state"] == "unknown"]
    # ⚠ 三种处境的**判据要与数据层一致**（独立复核 b28-fix 的 N1）：不能只用"有没有目标"来分，
    #   因为"有目标、但只探连通性"的目标一旦回 200 就会合法地记 unknown/no_anchor_configured
    #   ——那种情况写成"还没实测/欠账"就把话说反了。
    connectivity_only = [r for r in unknown if r["channel_id"] in targets
                         and r.get("last_error_code") == "no_anchor_configured"]
    pending = [r for r in unknown if r["channel_id"] in targets
               and r.get("last_error_code") != "no_anchor_configured"]
    notarget = [r for r in unknown if r["channel_id"] not in targets]
    lines += ["## 四、还没定论的渠道（⚠ 三种处境**必须分开读**）", "",
              f"- **已配探针、还没探过**：{len(pending)} 条 —— 这是「欠账」，下一轮就该探完；",
              f"- **只探到连通性**：{len(connectivity_only)} 条 —— 渠道**回 200 了**，但我们没给它配"
              "语义期望（失败原因列写 `no_anchor_configured`）⇒ 它**不算「可抓」**，也不算欠账；",
              f"- **按设计没有探针目标**：{len(notarget)} 条 —— 代码仓库（tool）/我方代码通路（internal）等，",
              "  它们不是「没轮到」，而是「这个对象没有独立可探的页面/接口」；",
              f"- 合计 ⚪ 未探 **{len(unknown)}** 条（面板上对最后一种会标「无探针」）。",
              "",
              "下一步（R6 起）：按类别优先级补探针——**锚点必须实测看到过**（逐字子串，不许实体解码/折叠空白）；",
              "可重复生成：`.venv\\Scripts\\python.exe scripts\\channel-anchor-measure.py <channel_id>`。",
              ""]
    if notarget:
        lines += ["按设计无探针的渠道：", ""]
        for r in sorted(notarget, key=lambda r: (r["category"], r["channel_id"])):
            lines.append(f"- `{r['channel_id']}`（{CAT_LABEL.get(r['category'], r['category'])}）{r['name']}")
        lines.append("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # ⚠ 传**相对**输出路径时 `relative_to(ROOT)` 会抛 ValueError（文件已写出、退出码却非 0）
    #   —— 独立复核 b28-fix2 的既存脚注，顺手按"打印失败不影响产物"修掉。
    try:
        shown = out.relative_to(ROOT)
    except ValueError:
        shown = out
    print(f"写出 {shown}（{out.stat().st_size} bytes，{len(lines)} 行）")
    print(f"台账 {s['total']} / 能干活 {s['by_wiring']['wired']} / "
          f"已实测 ok {s['by_state']['ok']} / 可疑 {s['by_state']['suspicious']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
