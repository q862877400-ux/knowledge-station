# -*- coding: utf-8 -*-
"""自助截图核对：browser4 驱动，批量截关键区（公式/图/表）→ 落盘 temp + 输出清单。

用于「修改 → 截图自查」循环的后台自动化：自动打开 24276 文档，滚动到
5.2 公式区 / 附录A 图区 / 附录B 表区，各截一张 PNG 到 %TEMP%，输出清单。
后台 job 跑，主会话/用户可见其执行与产物。
"""
import subprocess
import os
import sys
import time
import shutil
from pathlib import Path

TMP = Path(os.environ.get("TEMP", r"C:\Users\Zegel\AppData\Local\Temp"))
URL = "http://127.0.0.1:5173"

# browser4-cli npm 全局 bin（Windows 无裸命令，需 exe 路径）
_B4EXE = (shutil.which("browser4-cli")
          or r"C:\Users\Zegel\AppData\Roaming\npm\browser4-cli\bin\browser4-cli-win32-x64.exe")


def b4(*args):
    """调用 browser4-cli（返回 stdout）。"""
    r = subprocess.run([_B4EXE, *args], capture_output=True,
                       text=True, timeout=120)
    return (r.stdout or r.stderr)


def ev(js):
    import base64
    b = base64.b64encode(js.encode("utf-8")).decode()
    return b4("eval", "--base64", b, "--json")


def shot(name):
    p = TMP / f"audit_{name}.png"
    b4("screenshot", "-o", str(p))
    return p


def main():
    print(f"[1] open {URL}")
    b4("open", "--headed", "--fresh", URL)
    time.sleep(6)

    # 打开 24276
    print("[2] 打开 24276")
    ev('''() => { const b = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim()==='📚 文件目录'); if (b && !document.querySelector('.toc-drawer')) b.click(); return 'n'; }''')
    time.sleep(1)
    ev('''() => { const i = document.querySelector('.toc-drawer input'); const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(i,'24276'); i.dispatchEvent(new Event('input',{bubbles:true})); return 'q'; }''')
    time.sleep(1)
    ev('''() => { const d = document.querySelector('.toc-drawer'); const h = Array.from(d.querySelectorAll('*')).find(e => e.textContent.trim()==='GB/T 24276-2017' && e.children.length===0); if (h) h.click(); return 'opened'; }''')
    time.sleep(10)

    # 三区截图
    regions = [
        ("formula", '''() => { const pv=document.querySelector('.fulltext'); const f=Array.from(pv.querySelectorAll('img.formula-embed')).find(i=>i.src); if(!f) return 'none'; f.scrollIntoView({block:'center'}); return 'ok'; }'''),
        ("figureA", '''() => { const pv=document.querySelector('.fulltext'); const a=Array.from(pv.querySelectorAll('img.asset-embed')).find(i=>i.src && i.dataset.asset.startsWith('bb212aa1')); if(!a) return 'none'; a.scrollIntoView({block:'center'}); return 'ok'; }'''),
        ("tableB", '''() => { const pv=document.querySelector('.fulltext'); const cls=Array.from(pv.querySelectorAll('.fulltext-clause')); const last=cls[cls.length-1]; if(!last) return 'none'; last.scrollIntoView({block:'start'}); return 'ok'; }'''),
    ]
    paths = []
    for name, js in regions:
        print(f"[3] 滚动到 {name}")
        print("   ->", ev(js))
        time.sleep(1)
        p = shot(name)
        paths.append(p)
        print(f"   裁剪图: {p} ({p.stat().st_size if p.exists() else 0} bytes)")

    print("[done] 截图清单:")
    for p in paths:
        print(f"  {p}")
    print("主会话可 read_image 逐张核对。")


if __name__ == "__main__":
    main()
