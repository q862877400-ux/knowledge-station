"""stage19：常州明细页结构 + 南通互动页真实接口 + 南京 SPA 接口定位。"""
import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0"})

    # ---------- 常州 明细页 ----------
    w("## 常州明细页 sgj.changzhou.gov.cn ...show&id=365")
    for u in ("https://sgj.changzhou.gov.cn/index.php?m=letter&c=index&a=show&id=365",
              "https://czj.changzhou.gov.cn/index.php?m=letter&c=index&a=show&id=84122"):
        try:
            rr = c.get(u, timeout=30)
            w(f"  {u}\n    -> {rr.status_code} len={len(rr.text)}")
            # 去标签后看正文
            txt = re.sub(r"<script[\s\S]*?</script>", " ", rr.text)
            txt = re.sub(r"<style[\s\S]*?</style>", " ", txt)
            txt = re.sub(r"<[^>]+>", " ", txt)
            txt = re.sub(r"\s+", " ", txt).strip()
            w("    text=" + txt[:600])
        except Exception as e:  # noqa: BLE001
            w(f"  {u} -> {type(e).__name__} {str(e)[:70]}")

    # ---------- 南通 互动页真实接口 ----------
    w("\n## 南通 页面内接口")
    for u in ("https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html",
              "https://www.nantong.gov.cn/ntsrmzf/bumxx/bumxx.html"):
        try:
            rr = c.get(u, timeout=30)
            w(f"  {u} -> {rr.status_code} len={len(rr.text)}")
            for m in re.finditer(r"(truecms/[A-Za-z0-9_/\.]+|/[A-Za-z0-9_]+Controller/[A-Za-z0-9_]+\.do)", rr.text):
                w("     " + m.group(0))
        except Exception as e:  # noqa: BLE001
            w(f"  {u} -> {type(e).__name__} {str(e)[:70]}")

    # ---------- 南京 SPA 接口 ----------
    w("\n## 南京 SPA 接口定位")
    for u in ("https://szxx.nanjing.gov.cn:32767/zhengfuxinxiang/huifuxuandeng?orgid=320113&type=sszxx",):
        try:
            rr = c.get(u, timeout=30)
            w(f"  {u} -> {rr.status_code} len={len(rr.text)}")
            # 找 js 资源
            js = re.findall(r'(?:src|href)="([^"]+\.js)"', rr.text)
            w("  js=" + str(js[:20]))
            for j in js[:8]:
                ju = j if j.startswith("http") else "https://szxx.nanjing.gov.cn:32767" + (j if j.startswith("/") else "/" + j)
                try:
                    jr = c.get(ju, timeout=30)
                    for m in re.finditer(r'(https?://[^"\']+|/[a-zA-Z0-9_/]+)(?=["\'])', jr.text):
                        pass
                    # 找 axios baseURL / api 前缀
                    for m in re.finditer(r'(baseURL|/api/[a-zA-Z0-9_/]+|/[a-zA-Z0-9_]+/[a-zA-Z0-9_]+/[a-zA-Z0-9_]+)', jr.text):
                        w(f"     [{ju.split('/')[-1]}] {m.group(0)[:90]}")
                except Exception as e:  # noqa: BLE001
                    w(f"     js {ju} -> {type(e).__name__}")
        except Exception as e:  # noqa: BLE001
            w(f"  {u} -> {type(e).__name__} {str(e)[:70]}")


if __name__ == "__main__":
    main()
