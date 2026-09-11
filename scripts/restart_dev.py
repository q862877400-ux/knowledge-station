"""重启引擎+vite（原子化：精确杀 → 启动 → 输出端口/token/URL）。"""
import psutil
import subprocess
import time
from pathlib import Path

ROOT = Path("D:/AI/work space/zcode")


def kill_all():
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cl = " ".join(p.info["cmdline"] or [])
            if "src.core.main" in cl:
                p.kill()
            elif "vite" in cl and "node" in cl.lower():
                p.kill()
        except Exception:
            pass
    time.sleep(2)


def main():
    kill_all()
    # 引擎
    engine_log = ROOT / "var" / "engine.log"
    engine_log.unlink(missing_ok=True)
    engine = subprocess.Popen(
        [str(ROOT / ".venv/Scripts/python.exe"), "-m", "src.core.main"],
        cwd=str(ROOT), stdout=open(engine_log, "w", encoding="utf-8"),
        stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(9)
    lines = engine_log.read_text(encoding="utf-8").splitlines()
    port = token = None
    for ln in lines:
        if ln.startswith("KNOWLEDGE_STATION_PORT="):
            port = ln.split("=")[1].strip()
        if ln.startswith("KNOWLEDGE_STATION_TOKEN="):
            token = ln.split("=")[1].strip()
    print(f"ENGINE_PORT={port}")
    if not port:
        print("engine.log 前 20 行:", lines[:20])
        return

    # vite
    vite_log = ROOT / "var" / "vite.log"
    vite_log.unlink(missing_ok=True)
    env = {"VITE_ENGINE_PORT": port, "VITE_ENGINE_TOKEN": token or ""}
    import os
    env.update(os.environ)
    vite = subprocess.Popen(
        ["npm.cmd", "run", "dev:vite"], cwd=str(ROOT),
        stdout=open(vite_log, "w", encoding="utf-8"),
        stderr=subprocess.STDOUT, env=env,
        creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(7)
    vlines = vite_log.read_text(encoding="utf-8").splitlines()
    url = next((l.split("Local:")[-1].strip() for l in vlines if "Local:" in l), "?")
    print(f"VITE_URL={url}")
    # 验证
    import httpx
    h = httpx.get(f"http://127.0.0.1:{port}/api/v1/health", timeout=5)
    print("health:", h.status_code, h.json().get("status"))
    r = httpx.get(f"http://127.0.0.1:{port}/api/v1/egress/audit?limit=1",
                  headers={"Authorization": f"Bearer {token}"}, timeout=5)
    print("egress api:", r.status_code)
    v = httpx.post(f"http://127.0.0.1:{port}/api/v1/vision/locate",
                   headers={"Authorization": f"Bearer {token}"},
                   json={"image_path": "Z:/无.png"}, timeout=5)
    print("vision api:", v.status_code, "(422=端点就绪)")


if __name__ == "__main__":
    main()
