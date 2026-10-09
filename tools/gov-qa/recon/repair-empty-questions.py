r"""修复「问题为空但答复有内容」的记录 —— 按 `url` 重取明细，回填 `question`。

## 为什么会有这种记录

`recon/field-audit.py` 报「问题为空但答复有内容：N 条」。
根因是**解析漏了问题正文**，不是站点没有 —— 实测 `sd-jining` id=67876：
站点明细页**明确有**「内容 您好，我于 10 月份家里喜添新丁…」，
但落盘的 `question` 是空串。

★ 可疑根因：**问题正文里含 `<出生证明>` 这类尖括号**，
被「去标签」的正则 `<[^>]+>` 当成 HTML 标签吃掉了
（本条恰好整段只剩那个「标签」，于是成了空串）。
⇒ 只去标签、不还原实体、也不做「尖括号是不是标签」的判断，是有代价的。

## 本工具做什么

1. 扫全库找「`question` 空 且 `answer` 非空」的记录
2. 按 `url` **重新抓一次**明细页
3. 从页面里抠出正文（策略见 `extract()`）
4. **就地改写那一行**（只改 `question` 字段，其余字节不动）
5. 先备份原文件到 `recon/state/repair-backup-<ts>/`

## 用法

```bash
.venv/Scripts/python.exe tools/gov-qa/recon/repair-empty-questions.py --dry-run
.venv/Scripts/python.exe tools/gov-qa/recon/repair-empty-questions.py
```

⚠ 一次只处理**少量**记录（默认上限 20），逐条打印取到的正文供人工确认。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx                                                          # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
BACKUP_DIR = HERE / "state"

TAG_RE = re.compile(r"<[^>]+>")
#: ★ **只把「`<` 后紧跟 ASCII 字母或 `/`」的当标签**。
#:   实测教训：济宁这条问题正文里含 **`<出生证明>`** ——
#:   用通用的 `<[^>]+>` 去标签会把它**整段吃掉**，正文就没了（这正是本条 question 为空的原因）。
#:   真标签（`<p>` `<br/>` `</span>` `<font …>`）`<` 后一定是 ASCII 字母或 `/`。
REAL_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
#: 「内容 / 诉求内容 / 来信内容」标签单元格 → 其后第一个 `contentspan`
BODY_PAT = re.compile(
    r">\s*(?:内\s*容|诉求内容|来信内容|咨询内容)\s*<"
    r".*?<span[^>]*class=\"contentspan\"[^>]*>(.*?)</span>", re.S)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def _clean(s: str) -> str:
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(REAL_TAG_RE.sub(" ", s))).strip()


def extract(page: str) -> str:
    """从明细页里抠问题正文。"""
    m = BODY_PAT.search(page or "")
    if m:
        t = _clean(m.group(1))
        if len(t) >= 8:
            return t
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max", type=int, default=20)
    args = ap.parse_args()

    targets: list[tuple[Path, int, dict]] = []
    for f in sorted(DATA.glob("*.jsonl")):
        for i, line in enumerate(f.read_text(encoding="utf-8",
                                             errors="replace").splitlines(), 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:                                             # noqa: BLE001
                continue
            if not (r.get("question") or "").strip() and (r.get("answer") or "").strip():
                targets.append((f, i, r))
    print(f"待修 {len(targets)} 条（本次最多处理 {args.max} 条）")
    targets = targets[:args.max]

    if not targets:
        return 0

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = BACKUP_DIR / f"repair-backup-{ts}"
    bdir.mkdir(parents=True, exist_ok=True)

    patched: dict[Path, dict[int, str]] = {}
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        for f, lineno, r in targets:
            url = r.get("url") or ""
            print(f"\n{f.name} 第 {lineno} 行  id={r.get('id')}")
            print(f"  url={url[:100]}")
            if not url:
                print("  ⚠ 无 url，跳过")
                continue
            try:
                rr = c.get(url, timeout=25)
                page = rr.text or ""
            except Exception as e:                                        # noqa: BLE001
                print(f"  ⚠ 抓取失败 {type(e).__name__}")
                continue
            q = extract(page)
            if not q:
                print(f"  ⚠ 抠不出正文（HTTP {rr.status_code} len={len(page)}）")
                continue
            print(f"  ✅ 取到：{q[:120]}")
            patched.setdefault(f, {})[lineno] = q
            time.sleep(0.5)

    if not patched:
        print("\n无改动")
        return 1

    if args.dry_run:
        print(f"\n[DRY-RUN] 将修改 {sum(len(v) for v in patched.values())} 行")
        return 0

    for f, repl in patched.items():
        shutil.copy2(f, bdir / f.name)          # 先备份
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        for lineno, q in repl.items():
            r = json.loads(lines[lineno - 1])
            r["question"] = q
            r.setdefault("extra", {})["question_repaired"] = "recon/repair-empty-questions.py"
            lines[lineno - 1] = json.dumps(r, ensure_ascii=False)
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"已改写 {f.name}（{len(repl)} 行）  备份 → {bdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
