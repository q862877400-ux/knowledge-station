# -*- coding: utf-8 -*-
"""浏览器探测：打开 app → 文件目录 → 搜索/点开文档 → 报告 .fulltext 状态。"""
import base64
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_B4 = (shutil.which("browser4-cli") or "")
if _B4 and _B4.lower().endswith(".cmd"):
    _B4 = str(Path(_B4).parent / "node_modules" / "browser4-cli" / "bin" / "browser4-cli-win32-x64.exe")

URL = "http://127.0.0.1:5173"


def b4(*args):
    r = subprocess.run([_B4, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    return (r.stdout or r.stderr)


def ev(js: str):
    return b4("eval", "--base64", base64.b64encode(js.encode("utf-8")).decode(), "--json")


def main():
    std = sys.argv[1] if len(sys.argv) > 1 else "GB/T10-2013"
    print("[1] open", URL, flush=True)
    print(b4("open", "--headed", "--fresh", URL)[:300])
    time.sleep(6)
    print("[2] click 文件目录", flush=True)
    print(ev('''() => { const b = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim()==='📚 文件目录'); if (b) { b.click(); return 'clicked'; } return 'notfound-btn'; }'''))
    time.sleep(1)
    q = std.replace(" ", "")
    qq = json.dumps(q)
    ss = json.dumps(std)
    print("[3] fill search", q, flush=True)
    print(ev('''() => { const i = document.querySelector('.toc-drawer input'); if(!i) return 'no-input'; const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(i,''' + qq + '''); i.dispatchEvent(new Event('input',{bubbles:true})); return 'filled'; }'''))
    time.sleep(1.5)
    print("[4] click leaf", flush=True)
    print(ev('''() => { const d = document.querySelector('.toc-drawer'); if(!d) return 'no-drawer'; const h = Array.from(d.querySelectorAll('*')).find(e => (e.textContent && e.textContent.trim()===''' + ss + ''') && e.children.length===0); if (h) { h.click(); return 'opened:'+h.textContent.trim(); } return 'no-leaf:'+String(d.textContent).slice(0,120); }'''))
    time.sleep(12)
    print("[5] DOM state", flush=True)
    print(ev('''() => { const r = {}; r.fulltext = !!document.querySelector('.fulltext'); r.clauses = document.querySelectorAll('.fulltext-clause').length; r.toc = !!document.querySelector('.toc-drawer'); const ph = document.querySelector('.law-placeholder'); r.placeholder = ph ? ph.textContent.trim().slice(0,80) : null; const pb = document.querySelector('.doc-body'); r.bodytext = pb ? pb.textContent.replace(/\\s+/g,' ').slice(0,80) : null; r.fullLoaded = document.body.textContent.includes('正在加载全文条款'); r.curDoc = document.querySelector('.pdf-header-meta') ? document.querySelector('.pdf-header-meta').textContent : null; return JSON.stringify(r); }'''))


if __name__ == "__main__":
    main()
