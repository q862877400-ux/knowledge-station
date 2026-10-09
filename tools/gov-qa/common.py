"""公共工具层 —— 可运维化特性（spec 004）的基础设施。

**本模块的三条硬约束**（都来自实测踩坑，不是理论洁癖）：

1. **机器可读输出必须纯 ASCII**（`ascii_kv`）
   2026-10-10 闸门排查了 4 层 bug，其中 **2 层都是「拿中文当程序间接口」**：
   - bash `sed` 匹配中文 ⇒ locale 失配 ⇒ 解析成 `?`
   - Python 打印中文 ⇒ hook 环境 stdout 非 UTF-8 ⇒ `UnicodeEncodeError`
   ⇒ 凡给程序读的输出，一律走 `ascii_kv()`。中文只出现在给人看的输出里。

2. **落盘必须原子**（`atomic_append_jsonl`）
   现有 `harvest.py` 是「跑完才落盘」⇒ 跑 3 小时被 kill 就**整轮全丢**
   （GOAL.md 硬约束 3 就是为绕开它才要求「必须分块」）。
   增量模式改为一律 `O_APPEND` 单行写入，中断只损失当前那条。

3. **并发必须加锁**（`file_lock`）
   本目录**确实有并行 agent**（实测：数据量几分钟内 355,795 → 357,818），
   已因并发产生过 60 行重复 id。**不能假设只有一个 writer。**
"""
from __future__ import annotations

import glob as _glob
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- 纯 ASCII 输出

def ascii_kv(pairs: dict, *, stream=None) -> None:
    """输出 `KEY=VALUE` 形式的**纯 ASCII** 机器可读结果。

    **所有给程序读的输出都必须走这里。** 见模块文档第 1 条。

    规则：
    - key 必须能通过 `[A-Z_][A-Z0-9_]*`
    - value 一律转成字符串；**非 ASCII 字符被替换成 `?`**（而不是抛异常）
    - 每行一个 `KEY=VALUE`，便于 `grep` / `cut` 解析
    """
    out = stream or sys.stdout
    for k, v in pairs.items():
        key = str(k).upper()
        val = str(v)
        # 非 ASCII 一律替换，绝不抛 UnicodeEncodeError
        safe = val.encode("ascii", "replace").decode("ascii")
        try:
            out.write(f"{key}={safe}\n")
        except Exception:                                               # noqa: BLE001
            out.write(f"{key}=<unprintable>\n")


def human(msg: str, *, stream=None) -> None:
    """给人看的输出（可用中文）。**绝不用于机器可读路径。**"""
    out = stream or sys.stderr
    try:
        out.write(msg + "\n")
    except UnicodeEncodeError:
        # 终端编码不支持中文时的兜底，不让它崩
        out.write(msg.encode("utf-8", "replace").decode("ascii", "replace") + "\n")


# ---------------------------------------------------------------- 原子落盘

def atomic_append_jsonl(path, rec: dict) -> None:
    """单行 JSON 追加写入。**边采边落盘**的基础（R3）。

    用 `O_APPEND` 保证「要么整行写进去，要么什么都没写」——
    不存在「半条记录」。多进程并发追加同一文件也是安全的
    （POSIX 保证 `O_APPEND` 写入的原子性，且行小于 PIPE_BUF）。
    """
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)          # 立刻落盘，进程被杀也不丢
    finally:
        os.close(fd)


def iter_records(pattern) -> "list[dict]":
    """流式读 jsonl，**跳过坏行**（不因一行坏掉就整个文件读不了）。

    `pattern` 可以是 glob 字符串或路径列表。
    """
    paths = _glob.glob(str(pattern)) if isinstance(pattern, str) else list(pattern)
    for p in paths:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip() or not line.lstrip().startswith("{"):
                        continue
                    try:
                        yield json.loads(line)
                    except Exception:                                   # noqa: BLE001
                        continue
        except OSError:
            continue


# ---------------------------------------------------------------- 文件锁

class LockBusy(RuntimeError):
    """抢锁失败 —— **不是失败**，是「有人在跑」。调用方应返回退出码 3。"""


@contextmanager
def file_lock(path, *, timeout: float = 0.0):
    """基于 `O_CREAT|O_EXCL` 的跨进程文件锁。

    抢不到时（`timeout` 内）抛 `LockBusy`。**调用方必须把 LockBusy 映射成退出码 3**，
    而不是当成故障（契约见 `specs/004-*/contracts/poll.md`）。

    锁文件里写 pid + 时间戳，便于诊断「谁锁着」。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    fd = None
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            break
        except FileExistsError:
            if time.time() >= deadline:
                holder = ""
                try:
                    holder = path.read_text(encoding="utf-8").strip()
                except OSError:
                    pass
                raise LockBusy(f"锁被占用：{path}（持有者 {holder or '未知'}）")
            time.sleep(0.2)
    try:
        os.write(fd, f"pid={os.getpid()} at={int(time.time())}".encode())
        os.close(fd)
        fd = None
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            path.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------- 其它

def now_iso() -> str:
    """本地时间 ISO 串（秒精度）。"""
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def load_json(path, default=None):
    """读 JSON；**失败返回 default 而不抛**（水位损坏要能安全退化，FR-006）。"""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:                                                   # noqa: BLE001
        return default


def save_json(path, obj) -> None:
    """写 JSON（先写临时文件再 rename，避免写一半损坏）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
