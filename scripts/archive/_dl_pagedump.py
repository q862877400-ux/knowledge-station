# -*- coding: utf-8 -*-
"""取证：打开正常入库文档，dump 重建预览的页界（.page-break data-page）与条款页号（.fulltext-clause data-page）。"""
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

B4 = r"C:\Users\Zegel\AppData\Roaming\npm\node_modules\browser4-cli\bin\browser4-cli-win32-x64.exe"
URL = "http://127.0.0.1:5173"
STD = sys.argv[1] if len(sys.argv) > 1 else "GB/T10-2013"
SKEY = sys.argv[2] if len(sys.argv) > 2 else "10-2013"


def b4(*a):
    r = subprocess.run([B4, *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    return r.stdout or r.stderr


def ev(js):
    b = base64.b64encode(js.encode("utf-8")).decode()
    r = subprocess.run([B4, "eval", "--base64", b, "--json"],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    return r.stdout or r.stderr


def raw(js):
    try:
        return json.loads(ev(js))["output"]["result"]
    except Exception:
        return ev(js)


def q(s):
    return json.dumps(s)


def main():
    print("open", b4("open", "--headed", "--fresh", URL)[:50], flush=True)
    time.sleep(6)
    raw('()=>{const b=Array.from(document.querySelectorAll("button")).find(x=>x.textContent.trim()==="📚 文件目录"); if(b&&!document.querySelector(".toc-drawer")) b.click(); return "n";}')
    time.sleep(1)
    raw('()=>{const i=document.querySelector(".toc-drawer input"); if(!i) return "no-input"; const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,"value").set; s.call(i,' + q(SKEY) + '); i.dispatchEvent(new Event("input",{bubbles:true})); return "q";}')
    for _ in range(20):
        c = raw('''()=>{const d=document.querySelector(".toc-drawer"); if(!d) return 0; return Array.from(d.querySelectorAll(".toc-child")).filter(e=>String(e.textContent||"").replace(/[\\s/]+/g,"").includes(''' + q(SKEY) + ''')).length;}''')
        if c not in (0, "0"):
            break
        time.sleep(1)
    raw('''()=>{const d=document.querySelector(".toc-drawer"); const c=Array.from(d.querySelectorAll(".toc-child")).find(e=>String(e.textContent||"").replace(/[\\s/]+/g,"").includes(''' + q(SKEY) + ''')); if(c){c.click(); return "opened";} return "none";}''')
    for _ in range(30):
        if raw('()=>{return document.querySelectorAll(".fulltext-clause").length;}') not in (0, "0"):
            break
        time.sleep(1)
    time.sleep(1)
    d = raw('''()=>{const pv=document.querySelector(".fulltext"); if(!pv) return "no-fulltext"; const pbs=Array.from(pv.querySelectorAll(".page-break")).map(x=>x.dataset.page); const cs=Array.from(pv.querySelectorAll(".fulltext-clause")).map(c=>({no:(c.querySelector(".fulltext-cno")||{}).textContent, pg:c.dataset.page})); return JSON.stringify({page_break_marks:pbs, clause_pages:cs, pv_scrollHeight:pv.scrollHeight});}''')
    print("dump:", d, flush=True)


if __name__ == "__main__":
    main()
