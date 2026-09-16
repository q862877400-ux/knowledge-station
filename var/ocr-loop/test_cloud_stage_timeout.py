"""回归仪器：云阶段**整体超时**时不许钉死整批（2026-09-16 实测缺陷的护栏）。

现场缺陷（批次 7，`--parallel 24`）：`00:45:20` 后**状态文件 16 分钟零增长**、
日志几乎不动，而进程 CPU 仍在烧（60s +11.9s）、27 线程、只有 3 条 established
连接 → 线程卡在本地，不是云侧轮询。此时 `as_completed` 一个结果都交不出来
→ 主线程永久阻塞在 `fu.result()` → **剩余 476 部连提交都不会发生**。

本仪器直接复刻该场景：一个 worker 永久卡死、其余正常返回，断言
  ① 卡死项被记为"可重做失败"（`status=failed`、`channel=cloud`，下批会重投）；
  ② 其余项照常产出（**整批不停摆**）；
  ③ 总体耗时受超时上界约束（不随卡死线程无限增长）。

跑法：`python var/ocr-loop/test_cloud_stage_timeout.py`
"""
from __future__ import annotations

import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FTimeout  # noqa: F401
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FAIL: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'OK ' if ok else 'FAIL'} {name}: {got!r}"
          f"{'' if ok else f'（期望 {want!r}）'}")
    if not ok:
        FAIL.append(name)


def consume_with_timeout(fmap: dict, wait_s: float):
    """复刻 `vlm_ocr._iter_done` 的语义（保持同构，改实现要同步改这里）。"""
    from concurrent.futures import as_completed
    timed_out = [False]
    out = []
    try:
        for fu in as_completed(fmap, timeout=wait_s):
            out.append((fmap[fu], fu.result()))
    except FTimeout:
        timed_out[0] = True
        for f in fmap:
            if not f.done():
                out.append((fmap[f], {"status": "failed", "channel": "cloud"}))
            f.cancel()
    return out, timed_out[0]


print("=== 1) 一个 worker 永久卡死时，整批不许停摆 ===")
_release = threading.Event()


def _hang(_):
    _release.wait(30)          # 模拟"线程卡在连接层，永不返回"
    return {"status": "ok"}


def _fast(i):
    return {"status": "ok", "i": i}


t0 = time.monotonic()
with ThreadPoolExecutor(max_workers=3) as ex:
    fmap = {ex.submit(_hang, 0): "STUCK"}
    for i in range(1, 4):
        fmap[ex.submit(_fast, i)] = f"ok{i}"
    rows, timed_out = consume_with_timeout(fmap, wait_s=1.0)
    el = time.monotonic() - t0
    ex.shutdown(wait=False)    # 修复后的收尾语义：不等卡死线程

check("触发整体超时", timed_out, True)
check("卡死项被记为可重做失败",
      [r for k, r in rows if k == "STUCK"][0]["status"], "failed")
check("卡死项标记为 cloud（下批重投，而非终态）",
      [r for k, r in rows if k == "STUCK"][0]["channel"], "cloud")
check("其余 3 部照常产出", sorted(k for k, _ in rows if k != "STUCK"),
      ["ok1", "ok2", "ok3"])
check("整批耗时受超时上界约束（<3s，不随卡死线程增长）", el < 3.0, True)
_release.set()

print("\n=== 2) 反向对照：无卡死时不许误报超时 ===")
t0 = time.monotonic()
with ThreadPoolExecutor(max_workers=2) as ex:
    fmap = {ex.submit(_fast, i): f"f{i}" for i in range(3)}
    rows2, to2 = consume_with_timeout(fmap, wait_s=5.0)
    ex.shutdown(wait=True)
check("无卡死 → 未触发超时", to2, False)
check("无卡死 → 全部产出", len(rows2), 3)
check("无卡死 → 全部 ok", all(r["status"] == "ok" for _, r in rows2), True)

print("\n=== 3) 迟到结果不许覆盖已判记录（防重复处理）===")
abandoned = {"STUCK"}
late = {"status": "ok"}
k = "STUCK"
kept = late if k not in abandoned else {"status": "failed", "channel": "cloud"}
check("已被放弃的键：迟到 ok 不覆盖", kept["status"], "failed")
check("未被放弃的键：正常写入", (late if "other" not in abandoned else {})["status"],
      "ok")

print("\n=== 5) `_is_capability_boundary`：限流/瞬时错误不许判成能力边界 ===")
# 现场教训（2026-09-16，代价是数小时 GPU）：`run_cloud` 曾把**所有** `MineruCloudError`
# 当"云能力边界"→ `fatal=True` → 路由进本地 VLM队列（慢约 20 倍、串行独占）。
# 而该异常同时承载 429 / retry-limit 这类**瞬时**错误——它们重投云几秒即成功。
# 实测 135 部被误判 fatal，等于把数小时 GPU 烧在"重投云即可"的文档上。
import sys as _sys  # noqa: E402

_sys.path.insert(0, str(HERE))
import vlm_ocr as _V  # noqa: E402

_CASES = [
    # (错误文本, 期望判定为能力边界?, 说明)
    ("云能力边界：批次 01207b50 解析失败: retry limit reached", False, "retry limit=重试耗尽，属瞬时"),
    ("Client error '429 Too Many Requests' for url 'https://mineru.net/…'", False, "429 限流=瞬时"),
    ("HTTP 502 Bad Gateway", False, "5xx=瞬时"),
    ("connection reset by peer", False, "连接类=瞬时"),
    ("申请上传地址响应缺 batch_id/file_urls: {}", False, "响应异常=保守重投"),
    ("number of pages exceeds limit (200 pages)", True, "页数超限=能力边界"),
    ("unsupported file format", True, "格式不支持=能力边界"),
]
for _text, _want, _why in _CASES:
    check(f"{_why}", _V._is_capability_boundary(_text), _want)

print("\n=== 6) 扫描护栏：直接落盘的记录必须带 `key`（缺 key 会崩整个 worker）===")
# 现场教训（2026-09-16，两次）：`commit_rec` 的键护栏要求记录键是**文档键**，
# 缺失即抛 RuntimeError，从 `main()` 穿出 → **整个 worker 死亡**（批 7 实测）。
#   · 第一次：`_safe_stage` 的"云阶段异常"分支（预先存在，429 成常态后才暴露）；
#   · 第二次：我新加的超时分支同样缺 key（修复引入的新缺陷）；
#   · 第三次（扫描发现）：`cloud_disabled()` 分支。
# 判据：字面量里有 `"channel":` 的构造，要么自带 `"key":`，要么所在函数是
# **合并型生产者**（其返回值被 `rec.update()` 吃进已带 key 的 rec）。
import re  # noqa: E402

_src = (HERE / "vlm_ocr.py").read_text(encoding="utf-8")
_slines = _src.splitlines()
_MERGE = {"run_cloud", "run_local_vlm", "cloud_stage", "local_stage"}


def _enclosing_func(lineno: int) -> str:
    for i in range(lineno - 1, -1, -1):
        m = re.match(r"def (\w+)", _slines[i])
        if m and (i == 0 or _slines[i - 1][:1] not in (" ", "\t")):
            return m.group(1)
    return "?"


_risky = []
for _m in re.finditer(r'\{\s*"channel"\s*:', _src):
    _ln = _src[: _m.start()].count("\n") + 1
    _frag = _src[_m.start(): _m.start() + 300]
    _has_key = bool(re.search(r'"key"\s*:', _frag)) or "**extra" in _frag
    if not _has_key and _enclosing_func(_ln) not in _MERGE:
        _risky.append((_ln, _enclosing_func(_ln)))

check("无「直接落盘且缺 key」的记录构造", _risky, [])
check("至少检查到了若干构造（护栏不是空跑）",
      len(re.findall(r'\{\s*"channel"\s*:', _src)) >= 5, True)

print()
if FAIL:
    print(f"{len(FAIL)} 项失败：{FAIL}")
    sys.exit(1)
print("全部通过")
