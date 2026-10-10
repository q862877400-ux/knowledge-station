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


def safe_print(*args) -> None:
    """打印，**绝不因控制台编码抛异常**。

    动机（2026-10-10 T401 实测）：本机控制台是 GBK，而适配器/工具的日志里
    常有 `⇒`（U+21D2）、`⚠`、`✓` 这类字符。裸 `print` 会 `UnicodeEncodeError`
    **把整个采集带崩**，表现为"取到 0 条 + 一行 [采集失败]" ——
    **看起来像站点封了，其实是打不出一个箭头**。

    ⇒ 与 `harvest.py::_safe()` 同法：按当前 stdout 编码转义后再打。
    凡日志里可能含非 ASCII 符号的，一律走这里。
    """
    enc = getattr(sys.stdout, "encoding", None) or "ascii"
    parts = []
    for a in args:
        s = str(a)
        try:
            s.encode(enc)
        except (UnicodeEncodeError, LookupError):
            s = s.encode(enc, "replace").decode(enc, "replace")
        parts.append(s)
    print(" ".join(parts))


def human(msg: str, *, stream=None) -> None:
    """给人看的输出（可用中文）。**绝不用于机器可读路径。**

    ⚠ 兜底方向必须对（2026-10-10 spec 005 T107 修）：
    旧写法是 `msg.encode("utf-8","replace").decode("ascii","replace")` ——
    但 `encode("utf-8")` 对**任何**字符串都成功，非 ASCII 会被**原样保留成多字节**，
    接着 `decode("ascii")` 得到一坨 `\\ufffd`，**再交给 GBK 流去写 ⇒ 又抛 UnicodeEncodeError**
    （实测：`human('✅ …')` 在 GBK strict 流上崩在 `\\ufffd`）。
    ⇒ 正确做法是**按目标流的编码**转义，与 `harvest.py::_safe()` 同法。
    """
    out = stream or sys.stderr
    try:
        out.write(msg + "\n")
    except UnicodeEncodeError:
        enc = getattr(out, "encoding", None) or "ascii"
        try:
            out.write(msg.encode(enc, "replace").decode(enc, "replace") + "\n")
        except Exception:                                               # noqa: BLE001
            # 连按流编码转义都失败 ⇒ 退到纯 ASCII，绝不再抛
            out.write(msg.encode("ascii", "replace").decode("ascii") + "\n")


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


# ---------------------------------------------------------------- 标签覆盖口径

#: 判定「这条记录有类型标签」时**按顺序**尝试的键。
#:
#: ⚠⚠ **这个常量就是「标签覆盖率」的唯一出处**（spec 005 T105，2026-10-10 立）。
#: 立它之前，同一个指标有两个实现、两个数字：
#:   - `health.py`           只认 `msg_type_norm`            ⇒ 报 99.2%
#:   - `recon/label-coverage.py` 优先 `msg_type_norm`，**回落到原始脏 `msg_type`** ⇒ 报 100.0%
#: 两者实测差 3,025 条（0.8pt），而**闸门判据④用的正是宽的那个**。
#: ⇒ 现在两边都调 `label_key_of()`；要改口径只改这里一处。
#:
#: **为什么以窄口径（`msg_type_norm`）为准**：`msg_type` 是站方原始值，
#: 混了话题（「省直公积金」）与部门（「办公室」），不是干净的 9 分类；
#: `msg_type_norm` 才是归一化后的标签。用脏值凑覆盖率会**虚高**。
LABEL_KEYS = ("msg_type_norm", "msg_type", "type", "objective_type", "rqstType")


def label_key_of(rec: dict) -> "str | None":
    """返回这条记录**实际带标签的那个键名**，没有则 `None`。

    给需要区分口径的调用方用（例如要分别报「干净标签」与「只有脏标签」）。
    """
    ex = rec.get("extra")
    if not isinstance(ex, dict):
        return None
    for k in LABEL_KEYS:
        if ex.get(k) not in (None, "", [], {}):
            return k
    return None


def has_label(rec: dict, *, strict: bool = False) -> bool:
    """这条记录算不算「有类型标签」。

    `strict=True` 时**只认 `msg_type_norm`**（干净 9 分类）；
    默认（`strict=False`）按 `LABEL_KEYS` 顺序回落 —— 与 `label-coverage.py` 的历史口径一致。
    """
    k = label_key_of(rec)
    if k is None:
        return False
    return (k == "msg_type_norm") if strict else True


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
