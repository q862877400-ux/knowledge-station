"""生成 `docs/INDEX.md`（文档的机械索引）——**生成物，勿手改**。

扫描 `docs/` 下全部 `.md`（排除 `INDEX.md` 自身），按目录分组成表，
每行给出文件名、一句话描述（取正文首个有意义的标题行）、体积。

用法：
    python scripts/docs/gen-doc-index.py

⚠ 改了 `docs/` 里的文档之后要重跑本脚本，否则索引与实际不一致。
   `scripts/run-gates.ps1` 会检查这一致性。
"""
import pathlib, re, subprocess, collections
root = pathlib.Path(".").resolve()
docs = sorted(p for p in (root/"docs").rglob("*.md") if p.name != "INDEX.md")
def first_desc(p):
    try: t = p.read_text(encoding="utf-8", errors="replace")
    except Exception: return ""
    # 第一个二级标题 或 第一行非标题非空
    for line in t.split("\n")[1:80]:
        s = line.strip()
        if not s: continue
        if s.startswith("#"): 
            s = s.lstrip("# ").strip()
            if s and not s.startswith("目录"): return s[:60]
        elif len(s) > 8 and not s.startswith((">","-","|","`")): return s[:60]
    return ""
def lastc(p):
    r = subprocess.run(["git","log","-1","--format=%ad","--date=format:%Y-%m-%d",str(p.relative_to(root))],
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip() or "未提交"
rows = []
for p in docs:
    rel = str(p.relative_to(root)).replace("\\","/")
    rows.append((rel, round(p.stat().st_size/1024), lastc(p), first_desc(p)))
groups = collections.defaultdict(list)
for rel,kb,lc,d in rows:
    if "/archive/" in rel: g = "归档"
    elif "/research/channels/" in rel or "CHANNEL" in rel: g = "渠道与巡检"
    elif "/research/dsh-official/" in rel or "DSH" in rel or "ERRATA" in rel or "REALIGN" in rel: g = "DSH 研究与对齐"
    elif "/verify-briefs/" in rel: g = "复核任务书"
    elif re.search(r"RETRIEVAL|LAY-|lay-|WIKIDATA|jev-mem|rag-encyclopedia|weknora|RETRIEVAL|vision|plan-vs-reality|agent-memory|solutions-for|four-layer|cross-language|golden|STEP6|FINDINGS", rel): g = "检索与通用化研究"
    elif re.search(r"UI-|INTERACTION|ROADMAP|frontend|design", rel): g = "界面与交互"
    elif re.search(r"POLICY|MATERIALS|KB-FOLDER|INGEST|LAW_SOURCE|AUTO-|AUTORUN|EXECUTION|HANDOVER|ENGLISH|ENCYCLOPEDIA|INTRODUCTION|VISION", rel): g = "方案与台账"
    else: g = "根文档与其他"
    groups[g].append((rel,kb,lc,d))
order = ["方案与台账","检索与通用化研究","渠道与巡检","界面与交互","DSH 研究与对齐","复核任务书","根文档与其他","归档"]
out = ["# docs/ 总索引（机械生成，勿手改）","",
       "> 生成脚本见本文末尾命令。**只列文件名、体积、最后提交日、一句话**；正文各自住在原文件里。",
       f"> 共 **{len(rows)} 份** / **{sum(k for _,k,_,_ in rows)} KB**。", ""]
for g in order:
    if g not in groups: continue
    items = sorted(groups[g], key=lambda x:-x[1])
    out.append(f"## {g}（{len(items)} 份 / {sum(i[1] for i in items)} KB）")
    out.append("")
    out.append("| 文档 | KB | 最后改 | 一句话 |")
    out.append("|---|---:|---|---|")
    for rel,kb,lc,d in items:
        out.append(f"| `{rel}` | {kb} | {lc} | {d} |")
    out.append("")
out += ["---","","生成命令（机械、可重跑）：`python scripts/docs/gen-doc-index.py`",""]
(root/"docs"/"INDEX.md").write_text("\n".join(out), encoding="utf-8")
print("已生成 docs/INDEX.md:", len("\n".join(out)), "字符")
print("分组统计:")
for g in order:
    if g in groups: print(f"   {g:<18} {len(groups[g]):>3} 份  {sum(i[1] for i in groups[g]):>6} KB")
