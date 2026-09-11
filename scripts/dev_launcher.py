"""一键启动器（Phase 8）：拉起引擎 → 读 session 文件 → 拉起 vite → 打开浏览器。

用法: .venv/Scripts/python scripts/dev_launcher.py
停止: 关闭弹出的两个窗口，或 Ctrl+C 后由 launcher 清理子进程。
"""
import json
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESSION = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) /     "KnowledgeStation" / "engine.session.json"


def wait_session(timeout: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if SESSION.exists():
            try:
                return json.loads(SESSION.read_text(encoding="utf-8"))
            except Exception:
                pass
        time.sleep(0.5)
    raise TimeoutError("引擎未在 60s 内就绪")


def main() -> int:
    if SESSION.exists():
        SESSION.unlink()  # 旧会话文件作废
    python = str(ROOT / ".venv" / "Scripts" / "python.exe")
    engine = subprocess.Popen(
        [python, "-m", "src.core.main"], cwd=str(ROOT),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        info = wait_session()
        print(f"引擎就绪: port={info['port']} pid={info['pid']}")
        env = dict(os.environ)
        env["VITE_ENGINE_PORT"] = str(info["port"])
        env["VITE_ENGINE_TOKEN"] = info["token"]
        vite = subprocess.Popen(
            ["npm", "run", "dev:vite"], cwd=str(ROOT), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("前端启动中: http://localhost:5173/ （首次编译约 5~10s）")
        time.sleep(6)
        webbrowser.open("http://localhost:5173/")
        print("按 Ctrl+C 停止（引擎与前端会一并结束）")
        try:
            while True:
                time.sleep(2)
        except KeyboardInterrupt:
            pass
        finally:
            vite.terminate()
    finally:
        engine.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
