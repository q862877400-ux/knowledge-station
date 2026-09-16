"""MinerU 通道/模式报告（2026-09-15 立，可复用）。

回答「最近 MinerU 走的什么通道什么模式」——按 parse_out 产物落位判定（产物是
权威证据，不依赖日志）：

- `blocks.json` 非空且无 mineru/ 产物 → **文本层直入**（未走 MinerU 深度）
- `mineru/cloud_<batch12>/auto/<stem>_layout.json` → **云通道**（MinerU 官方 API）
- `mineru/<jobid>/auto/<jobid>_middle.json` → **本地 GPU 攒批**（deep_server）

模式字段：云产物 `_version_name`/`_backend`（服务端版本与后端）；本地通道的
模型档位见 `deep_server.py` / `mineru_adapter.py` 的 `do_parse(..., lang=...)`。

用法：python var/ocr-loop/channel_report.py [--limit 200]
"""
from __future__ import annotations

import io
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "parse_out"


def classify(d: Path) -> tuple[str, str, int, int]:
    """→ (通道, 版本/后端, 块数, 页数)"""
    blocks = d / "blocks.json"
    nb = 0
    if blocks.exists():
        try:
            nb = len(json.loads(blocks.read_text(encoding="utf-8")))
        except Exception:
            nb = 0
    mid = d / "mineru"
    cloud = local = False
    layout = None
    if mid.is_dir():
        for sub in mid.iterdir():
            if not sub.is_dir():
                continue
            if sub.name.startswith("cloud_"):
                cloud = True
            else:
                local = True
            if layout is None:
                for pat in ("*_layout.json", "*_middle.json"):
                    hits = list(sub.rglob(pat))
                    if hits:
                        layout = hits[0]
                        break
    ver, pages = "?", 0
    if layout is not None:
        try:
            mj = json.loads(layout.read_text(encoding="utf-8"))
            ver = f"{mj.get('_version_name') or 'local'}/{mj.get('_backend') or '?'}"
            pages = len(mj.get("pdf_info") or [])
        except Exception:
            ver = "读取失败"
    chan = "云(cloud_*)" if cloud else ("本地GPU" if local
                                    else ("文本层直入" if nb > 0 else "无深度产物"))
    return chan, ver, nb, pages


def main() -> None:
    limit = 200
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    dirs = sorted((d for d in ROOT.iterdir() if d.is_dir()),
                  key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    cnt, vers = Counter(), Counter()
    local_runs = []
    for d in dirs:
        chan, ver, _nb, _pg = classify(d)
        cnt[chan] += 1
        vers[ver] += 1
        if chan == "本地GPU":
            local_runs.append(datetime.fromtimestamp(d.stat().st_mtime))
    print(f"parse_out 最近 {len(dirs)} 个任务：")
    for k, v in cnt.most_common():
        print(f"  {k:14} {v:4} 部（{v / max(len(dirs), 1):.0%}）")
    print("  版本/后端分布:", dict(vers.most_common(5)))
    if local_runs:
        print("  最近本地通道任务:", [t.strftime("%m-%d %H:%M") for t in local_runs[:5]])

    print("\n配置侧：")
    for k in ("KS_MINERU_CLOUD", "KS_MINERU_LOCAL", "KS_MINERU_DEEP",
              "KS_DEEP_SERVER", "KS_DEEP_BATCH_WAIT"):
        print(f"  {k} = {os.environ.get(k, '(未设置→代码默认)')}")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from src.core.ingestion.mineru_adapter import mineru_available
        from src.core.ingestion.mineru_cloud import mineru_cloud_available
        okc, why = mineru_cloud_available()
        print(f"  云通道可用 = {okc}（{why}）")
        print(f"  本地模型可用 = {mineru_available()}")
    except Exception as e:  # noqa: BLE001
        print(f"  可用性判定失败: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
