# -*- coding: utf-8 -*-
"""决定性探针：open → 查 hook/抽屉 → fill 搜索 → 轮询等 .toc-child → 点击 → 轮询等 .fulltext。"""
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

B4 = r"C:\Users\Zegel\AppData\Roaming\npm\node_modules\browser4-cli\bin\browser4-cli-win32-x64.exe"
STD = sys.argv[1] if len(sys.argv) > 1 else "GB/T10-2013"
SKEY = sys.argv[2] if len(sys.argv) > 2 else "10-2013"
URL = "http://127.0.0.1:5173"


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
    s = ev(js)
    try:
        return json.loads(s)["output"]["result"]
    except Exception:
        return s


def q(s):
    return json.dumps(s)


def main():
    print("open", b4("open", "--headed", "--fresh", URL)[:60], flush=True)
    time.sleep(7)
    print("hook:", repr(raw('()=>{return typeof window.__ksOpenDoc;}')))
    print("drawer:", repr(raw('()=>{return !!document.querySelector(".toc-drawer");}')))
    raw('()=>{const b=Array.from(document.querySelectorAll("button")).find(x=>x.textContent.trim()==="📚 文件目录"); if(b&&!document.querySelector(".toc-drawer")) b.click(); return "n";}')
    time.sleep(1)
    raw('()=>{const i=document.querySelector(".toc-drawer input"); if(!i) return "no-input"; const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,"value").set; s.call(i,' + q(SKEY) + '); i.dispatchEvent(new Event("input",{bubbles:true})); return "q";}')
    # 轮询等 toc-child
    found = None
    for k in range(20):
        c = raw('''()=>{const d=document.querySelector(".toc-drawer"); if(!d) return -1; const cc=Array.from(d.querySelectorAll(".toc-child")).filter(e=>String(e.textContent||"").replace(/[\\s/]+/g,"").includes(''' + q(SKEY) + ''')); return cc.length;}''')
        if c not in (-1, 0, "-1", "0"):
            found = c
            print("toc-child found at loop", k, "count", c, flush=True)
            break
        time.sleep(1)
    if found is not None:
        click = raw('''()=>{const d=document.querySelector(".toc-drawer"); const c=Array.from(d.querySelectorAll(".toc-child")).find(e=>String(e.textContent||"").replace(/[\\s/]+/g,"").includes(''' + q(SKEY) + ''')); if(c){c.click(); return "clicked:"+String(c.textContent||"").slice(0,44);} return "none";}''')
        print("click:", repr(click), flush=True)
    else:
        print("toc-child NOT found", flush=True)
    # 等 fulltext-clause
    for k in range(30):
        n = raw('()=>{return document.querySelectorAll(".fulltext-clause").length;}')
        try:
            n = int(n)
        except Exception:
            n = 0
        if n > 0:
            print("fulltext clauses rendered:", n, flush=True)
            break
        time.sleep(1)
    print("final:", repr(raw('''()=>{const r={}; r.clauses=document.querySelectorAll(".fulltext-clause").length; r.fulltext=!!document.querySelector(".fulltext"); const ph=document.querySelector(".law-placeholder"); r.ph=ph?ph.textContent.trim().slice(0,60):null; return JSON.stringify(r);}''')))


if __name__ == "__main__":
    main()
