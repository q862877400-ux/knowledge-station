# -*- coding: utf-8 -*-
"""自动串批驱动（2026-09-15 立）：一批跑完 → 取基线 → 无达线类则取下一批。

**为什么需要它**：目标是 35,243 部全量。人工"跑完一批 → 手工换清单 → 再拉起"
在跨小时/跨天运行时必然断（实测：`watchdog_loop` 曾静默不在，批量死了两次无人知）。
本驱动把推进闭环成一条命令：

    循环 {
      等当前批跑完（进程消失且状态无待处理）
      → 取基线（scout --vlm-only --corpus）
      → 有达线类（≥FIX_LINE 部）？→ **停下并报告**（需修复，交 arbiter）
      → 无达线类 → next_batch 取全新一批 → 写 current_batch.json → 拉起
    }

**成功判据不在这里**：本驱动只管推进；"是否修好"由留出集/全量 delta 判定。
**安全阀**：`--max-batches` 上限、`--min-remaining` 候选不足即停、每批落日志。

用法：
  python var/ocr-loop/batch_advance.py --size 500 --max-batches 3
  python var/ocr-loop/batch_advance.py --dry-run      # 只看当前状态与判断
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EV = HERE / "evolve"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import batch_config as BC      # noqa: E402
import next_batch as NB        # noqa: E402

PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
FIX_LINE = 3
#: 拉起批量时用的云等待参数（**唯一所有者**：`_stall_min()` 由它们推导停滞阈值，
#: 与 `start_batch` 的 `--cloud-timeout/--cloud-attempts` 必须一致）。
#:
#: **为什么是 240×1**（2026-09-15 第三次实测校准，前两版都被数据推翻）：
#:   ① 900×3 → 一部卡住最长 45 分钟，把整个 chunk 拖死；
#:   ② 180×2 → 发现大批"云失败"的文档**用更长超时重测 6 秒就成功**，据此以为
#:      是"180 秒不够"→ 调到 ③；
#:   ③ 600×2 → 实测批次 4 **卡死在 40/500 十多分钟不动**：日志显示轮询 600s 超时、
#:      换 key 再等 600s；而同时云探针**三 key 全 5.5s 成功**——服务没坏，
#:      是**某些任务在云侧永不返回**。
#:   结论：这类任务的等待**与超时长短无关**（600 秒照样不回）；②里"重测 6 秒成功"
#:   其实是**晚点重试**的功劳，不是"超时给够"的功劳。故超时应**尽量短**——
#:   只要覆盖健康文档（实测 5–10s，少数 200s 内），卡住的快速失败 →
#:   记 `pending-local` → **下一批带它重跑**（`_carry_over()` 保证真的会重跑，
#:   实测几乎必成）。注意：这条承诺在 2026-09-15 之前**是假的**——见 `_carry_over`。
#:   240 秒 × 1 次 = 单块最长阻塞 4 分钟（对比 600×2 的 20 分钟）。
CLOUD_TIMEOUT_S = 240.0
CLOUD_ATTEMPTS = 1

#: **云并发度 = 24**（2026-09-16 单账号限流探针实测后定案）。
#:
#: ⚠⚠ 本常量我改过三次，**前两次的归因都是错的**。完整留证以免第四次重犯：
#:
#: 【第一次错】`probe_concurrency.py` 报"健康时段 8→24 吞吐 ×1.94、时延不涨"，
#:   我据此提并发 → 真实批次立刻撞 **429 Too Many Requests**（303 次）。
#: 【第二次错】我把 429 归因于"并发太高、已到天花板"，回退到 8。**两次都错**：
#:   429 的真实成因是 **`use_key()` 写全局 settings 后被多线程互相覆盖**
#:   （`run_cloud` 的重试循环里反复 `use_key`），于是**同一账号被并发猛打、
#:   其余账号闲置**——不是服务端不允许更高并发。
#:
#: 【实测依据】专用探针 `probe_key_limits.py`（**全档只用同一个 key**，排除混用）：
#:   · 单账号 loop3：并发 8 → 18.5 部/分；并发 **24 → 77.8 部/分**；
#:     持续 40 部（两波）→ **88.1 部/分**，**全程 0 个 429**
#:   · 单账号 project：并发 8 → 44.8 部/分；并发 **24 → 78.6 部/分**，**0 个 429**
#:   → 单账号在 24 并发下毫无压力。
#:
#: 【为什么该提并发】批 7 实录：12 分钟里**只有 17 部走真云 OCR**（另 109 部是
#:   复用产物、`wall_s=0`）→ 真云速率约 **1.4 部/分钟**；而同 key 探针在 8 并发
#:   就有 18.5–44.8 部/分。差距来自 ① 并发放大 ② 失败文档撞满 240s 超时**占住槽位**
#:   （8 个失败 × 240s ≈ 32 分钟·槽 ÷ 12 分钟 ≈ 2.7 个槽被长期占住）。
#:
#: 【回退判据】若并发 24 下真实批次再现 429：**先查是否有多个 worker 并存**
#:   （`CommandLine -match 'vlm_ocr'` 应只有 2 个进程：启动器 + worker），
#:   再考虑降并发——**不要**像前两次那样直接把 429 归因于并发。
PARALLEL = 24

#: **真正到终点的状态**。`needs-human` 同样是终点（试满上限/识别层能力边界，
#: 已登记待人工），它**不进 `pending_local`**——否则会把推进链永久钉住。
TERMINAL_STATUS = ("ok", "textlayer", "needs-human")
#: **巨型跳过**也是终点（用户指令 2026-09-15，台账 `vlm_oversize_skipped.json`）。
SKIPPED_STATUS = "skipped-oversize"

#: **跨批携带上限**（2026-09-15 立，2026-09-16 由 3 提到 8）。
#:
#: **为什么提**（实测证据，`probe_needs_human.py`）：批 10 有 **37 部**转 `needs-human`，
#: msg 全是"**云侧超时**"、页数 7–79（远低于 200 页硬限）——**没有一部是真正的
#: 云能力边界**，只是撞了 3 次降级窗口就被判终态。
#: 拿其中 6 部当场重测：**5 部成功**（6.0s / 9.8s / 21.6s / 26.1s / 31.9s，
#: 另 1 部仍失败）→ 证明它们**本可救**。
#:
#: 这与"误判 `fatal`"是同一类错误的**第三处**：**临时性失败被当成终态**。
#: 目标是"35,000 部全部识别入库"，这些被判终态的就是**内容缺口**。
#:
#: 取 8 的理由：① 云降级窗口一天多次、单次可达 67 分钟（§10.13），3 次容易连撞；
#: ② 仍保留上限，保证**不会有一部文档无限占用携带额度**（那会把推进链拖住）。
#: 若某部撞满 8 次仍失败，说明它不是临时问题 → 转 `needs-human` 交人工是正确终点。
MAX_CARRY = 8

#: **`needs-human` 复归上限**（2026-09-16 立）。为什么必须有这个机制：
#:
#: `MAX_CARRY` 从 3 提到 8**并没有解决**那 37 部——它们**在改常量之前就已经**
#: 被钉成 `needs-human`，而 `needs-human` 原先被写死为"永不携带的终点"
#: （见 `_carry_over` docstring）。于是提常量只保护**将来**的记录，
#: 已经误判的 37 部**没有任何代码路径会再消费**——静默内容缺口。
#:
#: 更根本的是：**每一次降级窗口都会生产一批新的误判终态**，外部脚本修一次
#: 只补一次，且**修不动**——`vlm_ocr.commit_rec` 是"整体读改写"
#: （`state[key]=rec; save_json(STATE, state)`），worker 活着一写就把外部
#: 修改**整份覆盖**掉（实测：改完 needs-human=0，worker 提交一次即回到 37）。
#: 所以修复**必须在持有 state 的那个进程里做**，即本函数——`_carry_over`
#: 正是"携带/退役"的唯一所有者层。
#:
#: 语义：`needs-human` 里**只有两类是真终态**（本地 VLM 能力边界、源 PDF 不在
#: 盘上）；其余（"撞满 N 次云侧超时"）是**临时性失败被当终态**——本循环里
#: 这已是同一类错误的**第四处**（前四处：误判 `fatal`、`_safe_stage` 全标
#: fatal、`MAX_CARRY=3`）。故给它们一条**复归**路径：
#:   - 只有 `_terminal_human_reason()` 判定为可重试的才复归；
#:   - 复归后**改用 `READMIT_HARD_CAP`**（而非 `MAX_CARRY`）作为携带上限，
#:     否则会与 `MAX_CARRY` 互相打架、在 8 附近来回抖；
#:   - 每批复归**有配额**，避免一口气灌进上千部把全新文档挤出本批。
READMIT_HARD_CAP = 24
#: 每批最多复归多少部（防挤占本批全新文档名额）。
READMIT_QUOTA = 40
#: 携带台账（append-only）：每次把残留带进下一批记一行，便于回看"这部试了几次"。
CARRY_LEDGER = EV / "carry_over.jsonl"

#: driver 心跳文件（单一所有者仲裁）：**driver 活着时 watchdog 退让**，
#: 否则两者会各自拉起一个 vlm_ocr 跑同一批（重复烧云额度）。
#: 实测必要性：批与批之间有几秒"无 vlm_ocr 进程"的窗口，watchdog 恰好巡检
#: 就会按 current_batch 再拉起一个。
OWNER = HERE / "batch_advance.owner"


def _write_owner() -> None:
    import os
    OWNER.write_text(json.dumps(
        {"pid": os.getpid(), "ts": time.strftime("%Y-%m-%d %H:%M:%S")}),
        encoding="utf-8")


#: 心跳刷新间隔（秒）。**必须独立于日志**（2026-09-15 实测缺陷）：
#: 原先只在 `_log()` 里写心跳 → driver 主循环一旦被卡住（实测被慢查询卡了
#: 37 分钟），心跳就变旧 → watchdog 判定"driver 卡死"→ **另拉起一份 vlm_ocr**，
#: 于是 driver 与 watchdog 抢着拉、进程增殖到 5 个（state 无锁、互相覆盖台账）。
#: 改成**守护线程每 30 秒无条件刷新**，与主循环是否阻塞无关。
HEARTBEAT_S = 30.0


def _start_heartbeat() -> None:
    import threading

    def loop() -> None:
        while True:
            try:
                _write_owner()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(HEARTBEAT_S)

    threading.Thread(target=loop, daemon=True).start()


def _clear_owner() -> None:
    try:
        OWNER.unlink()
    except OSError:
        pass


def _log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(HERE / "batch_advance.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    _write_owner()          # 每次日志即心跳，driver 存活对外可见


def _vlm_ocr_procs() -> list:
    """在跑的 `vlm_ocr` 进程（psutil.Process 列表）。**性能关键**。

    **为什么不用 pwsh 子进程**（2026-09-15 实测）：原实现每条日志/每轮巡检都
    起一个 `pwsh -Command Get-CimInstance ...`，实测 **371 ms/次**，而且
    系统高负载（本地 VLM 吃 2–3 核）时更慢甚至挂住——driver 主循环曾因此
    被卡 **37 分钟**，心跳变旧 → watchdog 判定"driver 卡死"→ **另拉一份
    vlm_ocr** → 进程增殖到 5 个（state 无跨进程锁，互相覆盖台账）。

    **psutil 的正确用法**（实测）：`process_iter(["pid","name"])` 只要 **4 ms**；
    但**逐进程读 `cmdline()` 很贵**（早先误写 `process_iter(["pid","name","cmdline"])`
    实测 **2 秒**）。故先按 name 便宜筛选，**只对少数 python 进程**读 cmdline。
    整体 **7 ms**，比 pwsh 快 50 倍，且不依赖外部进程。
    """
    try:
        import psutil
    except ImportError:
        return None                       # 交给调用方走 pwsh 兜底
    out = []
    for pr in psutil.process_iter(["pid", "name"]):
        try:
            if not (pr.info["name"] or "").lower().startswith("python"):
                continue
            if "vlm_ocr.py" in " ".join(pr.cmdline() or []):
                out.append(pr)
        except Exception:  # noqa: BLE001  (NoSuchProcess/AccessDenied/僵尸)
            continue
    return out


def _procs() -> list[int]:
    """在跑的 `vlm_ocr` 进程 pid 列表（判"这批跑完了吗"）。"""
    ps = _vlm_ocr_procs()
    if ps is not None:
        return [p.info["pid"] for p in ps]
    # ---- psutil 不可用时的 pwsh 兜底（慢但能用）----
    cmd = ("Get-CimInstance Win32_Process -Filter "
           "\"Name='python.exe' OR Name='pythonw.exe'\" | "
           "Where-Object { $_.CommandLine -like '*vlm_ocr.py*' } | "
           "Select-Object -ExpandProperty ProcessId")
    try:
        r = subprocess.run(["pwsh", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=40)
        return [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    except Exception:  # noqa: BLE001
        return []


def _proc_cpu(pid: int) -> float:
    """该 pid 累计 CPU 秒数（取不到返回 -1）。用于判"进程是否真的在算"。"""
    try:
        import psutil
        p = psutil.Process(pid)
        ct = p.cpu_times()
        return float(ct.user + ct.system)
    except Exception:  # noqa: BLE001
        return -1.0


def _batch_proc_cpu() -> float:
    """当前批 `vlm_ocr` 全部进程的累计 CPU 秒数之和（-1 表示取不到）。"""
    ps = _vlm_ocr_procs()
    if ps is None:
        return -1.0
    tot = 0.0
    got = False
    for p in ps:
        try:
            ct = p.cpu_times()
            tot += ct.user + ct.system
            got = True
        except Exception:  # noqa: BLE001
            continue
    return tot if got else -1.0


def _gate_exempt_classes() -> set[str]:
    """**达线闸门的显式豁免名单**（2026-09-16 立，`fixed_classes.json` 的
    `"gate_exempt": true` 字段）。

    **解决的结构性矛盾**：闸门对**任何**类都是「命中 ≥ `FIX_LINE`(3) 部 → 停止推进，
    先修复再前进」。但 `fixed_classes.json` 里存在**已被流程判定为"只登记、
    不修判据、仍照常计数上报"**的类（如 `appendix-table-lowconf`：「文本内容本身
    正确…故只登记不修判据」）。→ **这类类涨到 3 部时链条必停，而停下来根本
    没有可做的修复**：闸门的前提（"达线＝有缺陷待修"）对它不成立。

    **为什么这是修闸门的输入、而不是削弱闸门**：闸门的用途是"有缺陷才拦"。
    对一个**已被决策为不可修、且内容本身正确**的类拦截，拦截并不产生任何
    修复动作——是纯空转。实测成本：日志内 2 次停摆共空转 **2.22 小时**，
    且 **2/2 都是判据误报**（`probe_gate_stall_cost.py`）。

    **为什么用"每类显式 opt-in"而不是"凡已登记就豁免"**：
      - 默认**没有任何类被豁免**（名单为空 → 行为与改动前**完全一致**）；
      - 豁免是**逐类、写在台账里、可审计**的决定，必须给出 `gate_exempt_reason`；
      - **真缺陷类仍然照拦**——只有明确登记"不修判据且内容正确"的类才进名单。

    豁免**只影响"是否停链"**：该类**照常出现在基线报告里**（`over_exempt`），
    数字与证据都不隐藏。若判断有误，删掉台账里那个字段即可回滚。
    """
    try:
        d = json.loads((HERE / "fixed_classes.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return set()
    out: set[str] = set()
    for k, v in d.items():
        if isinstance(v, dict) and v.get("gate_exempt"):
            out.add(str(k))
    return out


def _class_in(cls: str, names: set[str]) -> bool:
    """类名匹配（含 `前缀::类名` 形态，如 `table-text::split-value`）。"""
    if cls in names:
        return True
    return cls.split("::")[-1] in names


def scout_and_judge() -> dict:
    """在当前批上跑侦察并给出判断（有达线类就该停下修复）。"""
    cfg = BC.current()
    env = {"KS_CORPUS_LIST": cfg["list"]}
    import os
    e = dict(os.environ)
    e.update(env)
    r = subprocess.run(
        [PY, "-X", "utf8", str(HERE / "scout.py"), "scout",
         "--vlm-only", "--corpus", "--products-only"],
        capture_output=True, text=True, cwd=str(ROOT), env=e, timeout=1800)
    try:
        sc = json.loads((EV / "scout.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"ok": False, "why": "scout.json 读取失败", "raw": r.stdout[-500:]}
    # **策略在闸门这一层施加，`scout.json` 保持原始证据不变**（见
    # `_gate_exempt_classes`）：豁免类不算"达线"，但**单独报出来**不隐藏。
    over_raw = [str(c) for c in (sc.get("over_line") or [])]
    exempt = _gate_exempt_classes()
    over = [c for c in over_raw if not _class_in(c, exempt)]
    over_exempt = [c for c in over_raw if _class_in(c, exempt)]
    # **分母必须一起报**（2026-09-15 修）：`scout` 只对"能定位到 VLM 产物的文档"
    # 统计命中，其余（无产物 / 后端标记 unknown / 文本层）**被跳过**。
    # 只报"评估 496 部 · 命中 0"会被读成"500 部零缺陷"——实测批次 4 有 4 部
    # 不在分母里（2 部待重做、2 部巨型跳过），而当时的报告标题是"质量 100%"。
    # 把 skipped 打进同一行，"命中 0"才带着它的适用范围。
    return {"ok": True, "eval": sc.get("docs_evaluated", 0),
            "skipped": sc.get("skipped_pipeline", 0),
            "hits": sc.get("total_hits", 0), "over": over,
            "over_exempt": over_exempt,
            "kinds": sc.get("source_kinds", {})}


def _list_path(cfg: dict) -> Path | None:
    """把 `cfg["list"]`（如 `evolve/work_batch2.json`）解析成真实文件。

    **为什么不能直接 `EV / cfg["list"]`**（2026-09-15 实测致命）：
    `cfg["list"]` 里**已经带了 `evolve/` 前缀**（由 `batch_config.set` 写入），
    再与 `EV = HERE/"evolve"` 拼接就变成
        `…/var/ocr-loop/evolve/evolve/work_batch2.json`  ← 不存在
    → `total=0` → `_wait_batch` 判 `no-total` → **driver 每一批都立刻"交人工"停下**，
    整条自动推进链断掉（本次 35,243 部目标正是靠这条链）。且它**不报错**：
    异常被 `except` 吞掉、退化成 0/0，日志只说"无进度信息"，看上去像"还没跑完"。
    实测现场：日志从 05:32 起只剩"仍在跑，等待…"，本地 VLM 一结束就会停。

    修法：按"相对 ocr-loop 根"解析（`HERE / cfg["list"]`），并兼容旧的
    相对仓库根写法（`ROOT / "var/ocr-loop" / cfg["list"]`）。两者都不存在则
    返回 None —— **绝不静默退回 0/0**，让上游把路径本身报出来。
    """
    raw = str(cfg.get("list") or "")
    if not raw:
        return None
    p = Path(raw)
    for cand in ([p] if p.is_absolute() else
                 [HERE / raw, ROOT / "var" / "ocr-loop" / raw, EV / p.name]):
        if cand.exists():
            return cand
    return None


def _batch_progress(cfg: dict) -> tuple[int, int, int, int, int, int]:
    """当前批的 (已完成, 已失败终点, 总数, 待重做, 巨型跳过, 待人工)。

    **为什么不能只看进程消失**（2026-09-15 实测）：批次因未捕获异常崩溃时进程
    也会消失，driver 会误判"跑完了"→ 对**不完整的数据**取基线并推进，评测口径
    直接失真（实测批次 2 只跑 116/500 就被判"已结束"）。

    **为什么 failed 要单独算**（2026-09-15 实测）：`failed` 是**已到达终点**的记录
    （state 已落盘、`--status` 记为"失败 N 部"），不是"还没跑"。若只数
    `ok|textlayer`，一个反复失败的文档会让 `done < total` 永久成立 → driver 重启
    5 次后停在"待人工"。实测现场：`GB/T 16751.1-2023`（241 页，超云硬限 200 页
    → 走本地 VLM）。
    分开计数后：**能确认到位 → 允许推进**，但把失败数报出来（不静默丢缺口）。

    **`待人工` 为什么必须单独一桶**（2026-09-15 修）：`pending_local` 是"未到终点"，
    把它算进终点会让批次带着缺口收批（原缺陷）；把它算进"未完成"又会让一部
    云侧永久卡死的文档把整条推进链钉住。故引入 `needs-human` 作为**显式终点**：
    它由 `_carry_over` 在试满 `MAX_CARRY` 次后写入，**永远带着数字出现在日志里**。
    """
    lp = _list_path(cfg)
    if lp is None:
        return 0, 0, -1          # -1 = 清单路径都没找到（上游据此报错，不当成 0 部）
    try:
        obj = json.loads(lp.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return 0, 0, -1
    total = int(obj.get("n") or len(obj.get("paths") or []))
    try:
        st = json.loads((HERE / "vlm_ocr_state.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        st = {}
    done = failed = pending_local = skipped = human = 0
    for p in obj.get("paths") or []:
        s = (st.get(Path(p).stem) or {}).get("status")
        if s in ("ok", "textlayer"):
            done += 1
        elif s == "failed":
            failed += 1
        elif s == SKIPPED_STATUS:
            # **巨型文档跳过**（用户指令 2026-09-15）：页数 >200 → 云必拒 +
            # 本地极慢（单部 1–2 小时、GPU 独占串行）→ 拖死循环速度。
            # 跳过=已到终点（否则批次永不完成、driver 永远等）。台账在
            # `vlm_oversize_skipped.json`，需要时可按清单补跑。
            skipped += 1
        elif s == "needs-human":
            # 试满 `MAX_CARRY` 次仍未成功 / 识别层能力边界：**显式终点**，
            # 不再无休止重试，但每次收批都随数字报出来（不静默丢）。
            human += 1
        elif s == "pending-local":
            # 云没解析成、**还没到终点**——既不能算完成（会留下缺口），
            # 也不能拦死推进（会钉住整条链）。由 `_carry_over` 带进**下一批**
            # 清单重跑；试满上限转 `needs-human`。
            pending_local += 1
    return done, failed, total, pending_local, skipped, human


#: 刚拉起一批后的**启动宽限期**（秒）：宽限内即使进度还是 0/500 也不判"未跑完"。
#: **为什么必须有**（2026-09-15 实测）：`_batch_progress` 只统计**已到达终点**的文档，
#: 而首批文档从提交到落 state 需要十几秒~几分钟（云 VLM 单部 6~140 页）。driver
#: 拉起后立刻查 → 0+0/500 → 判"未跑完"→ 重拉 → 又立刻查 → 再重拉……
#: 实测：批次 3 刚健康开跑（日志已到 `[8/500] … 云VLM…`）就被重拉，日志写着
#: "重新拉起续跑（第 1 次）"——**两个进程并发跑同一批**、重复提交云端任务
#: （用户额度 5000 文件/日）。宽限期把"还没跑出第一部"与"跑挂了"分开：
#: 判据是**时间**，因为**进度天然滞后**，用进度判"启动失败"必然误判。
START_GRACE_S = 150

#: **停滞判定阈值**（分钟）：进程活着但 `(完成+失败)` 与日志 mtime 都 N 分钟不动
#: → 视为卡死，杀掉该批进程并重拉（state 保证断点续跑）。
#: **为什么需要**（2026-09-15 实测）：进程"活着"不等于"在干活"。实测批次 3
#: 曾卡在 8/500、日志 3 分钟无更新、CPU 30 秒只涨 0.7 秒——而 `_procs()`
#: 只要看到进程就 `while` 死等**永不超时**。若无人盯着，这会白等到天荒地老
#: （本目标跨天运行，必须自愈）。
#:
#: **为什么下限是 30 分钟而不是 12**（2026-09-15 实测修正）：每次重启都**丢弃
#: in-flight 的那个 chunk**（`as_completed` 的结果只在本进程内，未提交的 8 部要
#: 重做），实测批次 3 因 12 分钟阈值被重启两次、两次都白丢一整块。
#: 而一个 chunk 的**合法**最长耗时并不小：云 180s×2 次 + 本地 VLM 兜底
#: （实测有 ~200 秒固定启动开销，2 页文档也要 211.8s）。取 30 分钟可容下
#: "云超时→换 key→再超时→进本地队列"这条完整链路，同时仍能捕获真卡死。
#: 用 `_stall_min()` 与云端预算取较大值。
STALL_MIN = 30


def _stall_min() -> float:
    """实际停滞阈值 = max(STALL_MIN, 云端等待预算 + 缓冲区)。

    云端等待预算从 **`current_batch` 实际使用的启动参数**推导（单一口径：
    与 `start_batch` 里传的 `--cloud-timeout/--cloud-attempts` 一致）。
    这里硬编码与 start_batch 同源的两个常量，避免"改了启动参数忘了改阈值"。
    """
    budget_min = (CLOUD_TIMEOUT_S * CLOUD_ATTEMPTS + 300) / 60.0
    return max(float(STALL_MIN), budget_min)


def _wait_batch(cfg: dict, *, max_restarts: int = 5) -> tuple[bool, str]:
    """等当前批真正跑完（进程消失 **且** 进度达标），必要时重新拉起。

    返回 `(是否完成, 原因)`。崩溃的批次会被重新拉起（state 保证断点续跑），
    超过 `max_restarts` 则放弃并交由人工——**绝不带着不完整数据推进**。
    "收批达标" = 本批每部文档都**到过一次终点**（`已完成 + 失败 + 待人工 + 巨型跳过
    + 待重做 >= 总数`，见 `_batch_progress`）：`待重做`（`pending-local`）不再拦死
    推进，但它**必须**由 `_carry_over()` 带进下一批清单重跑——收批日志里的
    "残留 N 部"就是这个数字，不是"N 部已完成"。
    """
    restarts = 0
    grace_until = 0.0          # 刚拉起后的免判窗口（见 START_GRACE_S）
    sig: tuple | None = None   # 上次观察到的 (done, failed, 日志mtime)
    sig_at = 0.0               # 该观察的时刻（用于停滞计时）

    def _sleep_until_dead(total_s: float, *, step: float = 20.0) -> None:
        """睡 `total_s`，但**批进程一消失就立刻返回**（2026-09-16 新增）。

        **为什么需要**（实测观察）：原实现用固定 `time.sleep(300)`。
        worker 若在这 5 分钟里死掉，driver 要等**睡满**才回到 `while _procs()`
        重新判活 → 最坏空窗 **5 分钟**；而这类死法在整轮里反复发生
        （本会话我自己的重启、以及 429 风暴里的多次崩溃）。
        空窗期间**没有任何文档在被处理**，纯产能损失。

        只轮询进程存在性（`_procs()` 是 pid+name 过滤，实测量级毫秒），
        不引入额外开销；不改变任何判据——stall 阈值、宽限期、重拉次数都不变。
        """
        end = time.time() + total_s
        while time.time() < end:
            time.sleep(min(step, max(0.5, end - time.time())))
            if not _procs():
                return

    while True:
        while _procs():
            if grace_until and time.time() < grace_until:
                left = int(grace_until - time.time())
                _log(f"批次 #{cfg['batch']} 启动宽限中（剩 {left}s，不因 0 进度重拉）")
                _sleep_until_dead(min(60, max(10, left)))
                continue
            # ---- 停滞检测：进程活着≠在干活 ----
            cur = _liveness_sig(cfg)
            prog = (f"完成 {cur[0]} · 失败 {cur[1]} · 待重做 {cur[2]} · "
                    f"巨型跳过 {cur[4]} · 待人工 {cur[5]} / 共 {cur[3]}")
            if cur != sig:
                sig, sig_at = cur, time.time()
                _log(f"批次 #{cfg['batch']} 仍在跑（{prog}）…")
                _sleep_until_dead(300)
                continue
            stalled_min = (time.time() - sig_at) / 60.0
            limit = _stall_min()
            if stalled_min < limit:
                _log(f"批次 #{cfg['batch']} 仍在跑（{prog}，"
                     f"已停滞 {stalled_min:.0f}/{limit:.0f} 分钟）…")
                _sleep_until_dead(300)
                continue
            # 停滞超阈值 → 杀掉该批进程，交给下方"重新拉起"分支（state 断点续跑）
            _log(f"❗批次 #{cfg['batch']} 停滞 {stalled_min:.0f} 分钟"
                 f"（{prog}，"
                 f"日志 mtime 未变）→ 判定卡死，杀掉该批进程后重拉")
            _kill_batch_procs()
            grace_until = 0.0
            break
        done, failed, total, pending_local, skipped, human = _batch_progress(cfg)
        if total < 0:
            _log(f"❗批次 #{cfg['batch']} 清单路径解析失败：cfg['list']="
                 f"{cfg.get('list')!r}（已试 {HERE / str(cfg.get('list'))} 等）"
                 f"→ 停，交人工（既不当成「跑完」也不当成「没跑」）")
            return False, "list-not-found"
        # **收批判据 = 本批每部文档都"到过一次终点"**（2026-09-15 修）。
        #
        # 原判据是 `done+failed+skipped >= total and not pending_local`：它把
        # `failed` 当终点、又在**宣布完成之后**才把 failed 重分类成 pending-local，
        # 于是决策与落盘互相矛盾（详见本块下方的缺陷记录），且 `pending_local`
        # 一出现就永不收批 → 一部云侧永久卡死的文档把整条推进链钉死。
        #
        # 现判据把 `pending_local` 也算作"到过终点"（它**确实**已落盘、已尝试过），
        # 缺口不靠"拦住批次"来兜，而靠 `_carry_over()` 把残留**带进下一批清单**
        # 重跑——批次能推进，残留不丢，数字照报。
        if total and done + failed + human + skipped + pending_local >= total:
            # **先重分类、再收批**（2026-09-15 修，原顺序是反的）。
            #
            # 缺陷证据（实测批次 4，2026-09-15 20:19）：判据读的是**重分类之前**
            # 的 state（2 部仍记 `failed`）→ 判"到齐"→ 紧接着 `_requeue_cloud_failures`
            # 把这 2 部改成 `pending-local`（语义"未到终点"）→ 批次已被宣布
            # "已完成 496/500"、driver 立刻换批。而这 2 部**只存在于批次 4 的清单里**，
            # `vlm_ocr` 只会被以**当前批清单**拉起 → 它们再也不会被重做：
            # 自 19:46 / 20:13 起无人再碰（`GB／T 34001-2016`、`GB／T 46085-2025`），
            # 而当时的会话把这件事报告成"下一轮自动重试"。
            #
            # 现在：重分类先落盘 → 重新读一遍 → 残留（failed + pending_local）
            # 随数字如实报出，并由 `_carry_over()` 保证进入下一批清单。
            moved = _requeue_cloud_failures(cfg)
            done, failed, total, pending_local, skipped, human = _batch_progress(cfg)
            residue = failed + pending_local
            _log(
                f"批次 #{cfg['batch']} 收批：**完成 {done} · 残留 {residue} 部"
                f"（带进下一批重跑）** · 巨型跳过 {skipped} 部 · 待人工 {human} 部"
                f" / 共 {total}"
                + (f"（本次重分类 {moved} 部：云侧超时≠做不了）" if moved else "")
                + ("（巨型台账 vlm_oversize_skipped.json）" if skipped else ""))
            return True, "complete"
        if not total:
            _log(f"批次 #{cfg['batch']} 无进度信息（{done}/{total}）→ 交人工")
            return False, "no-total"
        restarts += 1
        if restarts > max_restarts:
            _log(f"❗批次 #{cfg['batch']} 反复中断（{done}+{failed}+{pending_local}待本地"
                 f"/{total}，已重启 {max_restarts} 次）→ 停在此处待人工")
            return False, "restart-limit"
        _log(f"批次 #{cfg['batch']} 未跑完（完成 {done} · 失败 {failed} · 待重做 "
             f"{pending_local} · 巨型跳过 {skipped} · 待人工 {human} / 共 {total}）"
             f"→ 重新拉起续跑（第 {restarts} 次）")
        if not start_batch(cfg):
            _log("❗重新拉起失败 → 停在此处待人工")
            return False, "start-failed"
        grace_until = time.time() + START_GRACE_S
        time.sleep(20)


def _carry_attempts() -> dict[str, int]:
    """携带台账里各文档**已被带过几次**（append-only 台账按 std_no 计数）。"""
    c: dict[str, int] = {}
    if not CARRY_LEDGER.exists():
        return c
    for line in CARRY_LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            k = json.loads(line).get("key")
        except Exception:  # noqa: BLE001
            continue
        if k:
            c[k] = c.get(k, 0) + 1
    return c


def _terminal_human_reason(rec: dict) -> str:
    """`needs-human` 记录**是否真终态**：真终态返回原因串，可重试返回 ""。

    **判据只用记录自身的客观事实，不去解析 `msg` 文本**——`msg` 是给人看的、
    会被层层前缀拼接（实测样例："（转待人工）已携带重跑 3 次仍未成功：
    （批次收尾重分类）云侧超时，待下轮重做：第 1/1 次云解析失败（key=…"），
    拿它做判定等于把展示层当契约（本循环已因"用手写探针读展示文本"
    吃过亏，见 HANDOFF §10.20）。

    真终态只有两类：
      - 本地 VLM 失败 → 识别层能力边界，重试无意义；
      - 源 PDF 不在盘上（或无 `pdf` 字段的旧回填记录）→ 无从重做。
    """
    if rec.get("channel") in ("local-vlm", "local"):
        return "本地 VLM 失败＝识别层能力边界（不无限重试）"
    if not rec.get("pdf"):
        return "记录无源 PDF 路径（旧回填记录），无从重做"
    if not Path(str(rec["pdf"])).exists():
        return "源 PDF 已不在盘上"
    return ""


def _carry_over(paths: list[str], *, dry_run: bool = False) -> tuple[list[str], dict]:
    """把 state 里**未到终点**的文档并进本批清单——残留进下一批重跑的唯一保证。

    **为什么必须有**（2026-09-15 实测缺陷，本函数就是它的所有者层修复）：
    `pending_local` / `failed` 这类"未到终点"记录**只存在于它所属批次的清单里**，
    而 driver 收批后立刻 `next_batch` 换一批**全新、零重叠**的文档，`vlm_ocr`
    也只会被以**当前批清单**拉起 → 上一批的残留**没有任何代码路径会再消费它**。
    原实现把这件事靠注释假设成"下一轮必然重做"，实测反例：
    `GB／T 34001-2016`（152 页）、`GB／T 46085-2025`（27 页）自 2026-09-15
    19:46 / 20:13 被重分类为 `pending-local` 后，批次 5 全程在跑、这两部无人再碰——
    **一次静默的内容缺口 + 一句"下一轮自动重试"的假承诺**。

    语义：
      - 残留 = state 里 status 为 `pending-local` 或 `failed` 的记录（白名单，
        空状态/未知状态不动）；`ok|textlayer|skipped-oversize` 是终点，永不携带；
      - **`needs-human` 里可重试的会先复归**（`READMIT_HARD_CAP` 注释）：只有
        `_terminal_human_reason()` 认定的真终态（本地 VLM 能力边界、源 PDF 不在
        盘上）才永不携带；"撞满 N 次云侧超时"是临时性失败，复归后按
        `READMIT_HARD_CAP` 计上限，每批受 `READMIT_QUOTA` 约束；
      - **本地 VLM 的 failed** 是识别层能力边界（不该无限重试）→ 直接 `needs-human`；
      - 其余（云侧超时类 `pending-local` / 云端 `failed`）→ 带进本批清单重跑，
        每次携带记一行台账；**试满上限**转 `needs-human`（显式终点 +
        日志数字，永不静默丢）；
      - 源 PDF 不在盘上的（记录不带 `pdf` 字段的旧回填记录）→ `needs-human`，
        因为**没有源文件就无从重做**，静默忽略才是真丢账。

    **调用时机**：只在上一批**已确认收批**、且没有 `vlm_ocr` 在跑时调用——
    state 是整体读改写、无跨进程锁（见 `vlm_ocr._guard_single_instance` 注释）。

    `dry_run=True`：只算不写（用于人工核对"现在到底有多少残留"）。
    """
    st = {}
    sp = HERE / "vlm_ocr_state.json"
    try:
        st = json.loads(sp.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return paths, {"carried": [], "retired": [], "reason": "state 读取失败"}
    attempts = _carry_attempts()
    seen = {Path(p).stem for p in paths}
    carried: list[str] = []
    retired: list[str] = []
    readmitted: list[str] = []
    changed = False
    for key, rec in sorted(st.items()):
        if not isinstance(rec, dict):
            continue
        s = rec.get("status")
        # **`needs-human` 复归**（见 READMIT_HARD_CAP 注释）：先于状态白名单判定，
        # 因为复归后它就变成一条普通残留、走下面完全相同的携带逻辑（含台账、
        # 含"本批清单里已有则不重复带"）。
        if s == "needs-human":
            if _terminal_human_reason(rec):
                continue                     # 真终态：保持"永不携带"
            if attempts.get(key, 0) >= READMIT_HARD_CAP:
                continue                     # 复归后又撞满硬上限 → 钉死
            if len(readmitted) >= READMIT_QUOTA:
                continue                     # 本批配额已满，留到下批
            rec["status"] = "pending-local"
            rec["readmitted"] = True         # 复归过的用更宽的上限（见下 cap）
            rec["msg"] = ("（复归重试）降级窗口已过，重新排队："
                          + str(rec.get("msg"))[:80])
            readmitted.append(key)
            changed = True
            s = "pending-local"
        # **只有这两种状态算"未到终点"**：显式白名单，不用"非终点皆是残留"的
        # 反写法——否则一个空状态/未来新增状态的记录会被反复携带重跑。
        if s not in ("pending-local", "failed"):
            continue
        # **两种 channel 都要认**（2026-09-16 审计子代理发现）：`vlm_ocr.py:410/415/417`
        # 返回 `local-vlm`，而 `--channel local` 的失败路径返回 `"local"`（`vlm_ocr.py:877`）。
        # 只认前者会让后者被当成"可重试的云残留"反复携带，而不是按能力边界转 `needs-human`。
        if s == "failed" and rec.get("channel") in ("local-vlm", "local"):
            why = "本地 VLM 失败＝识别层能力边界（不无限重试）"
        elif not rec.get("pdf"):
            why = "记录无源 PDF 路径（旧回填记录），无从重做"
        elif not Path(str(rec["pdf"])).exists():
            why = "源 PDF 已不在盘上"
        elif attempts.get(key, 0) >= (READMIT_HARD_CAP if rec.get("readmitted")
                                      else MAX_CARRY):
            # 复归过的记录用更宽的上限，否则会与 MAX_CARRY 来回抖（见 READMIT_HARD_CAP）。
            why = f"已携带重跑 {attempts.get(key, 0)} 次仍未成功"
        else:
            why = ""
        if why:
            rec["status"] = "needs-human"
            rec["human_reason"] = why        # 结构化留痕，避免日后解析 msg
            rec["msg"] = f"（转待人工）{why}：{str(rec.get('msg'))[:80]}"
            retired.append(key)
            changed = True
            continue
        stem = Path(str(rec["pdf"])).stem
        if stem in seen:
            continue                     # 本批清单里已有（它就在本批），不重复带
        paths.append(str(rec["pdf"]))
        seen.add(stem)
        carried.append(key)
        attempts[key] = attempts.get(key, 0) + 1
        if not dry_run:
            with CARRY_LEDGER.open("a", encoding="utf-8") as f:
                f.write(json.dumps(
                    {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "key": key,
                     "attempt": attempts[key], "status": s}, ensure_ascii=False) + "\n")
    if changed and not dry_run:
        sp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    return paths, {"carried": carried, "retired": retired,
                   "readmitted": readmitted}


def _requeue_cloud_failures(cfg: dict) -> int:
    """把当前批里**云通道的终态 failed** 转成 `pending-local`（下次启动重做）。

    **为什么不能把它们当"已完成"**：实测这些 `failed` 绝大多数是云侧拥塞时的
    超时，用更长超时重测 6 秒即成功（见 `CLOUD_TIMEOUT_S` 注释）。留成终态
    等于**内容缺口 + 假完成**（`done+failed>=total` 会判本批完成）。
    只动 `channel == "cloud"` 的失败：本地 VLM 的失败是真正到过终点的
    （识别层能力边界），不该无限重试。
    """
    lp = _list_path(cfg)
    if lp is None:
        return 0
    try:
        obj = json.loads(lp.read_text(encoding="utf-8"))
        st = json.loads((HERE / "vlm_ocr_state.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return 0
    n = 0
    for p in obj.get("paths") or []:
        k = Path(p).stem
        v = st.get(k) or {}
        if v.get("status") == "failed" and v.get("channel") == "cloud":
            v["status"] = "pending-local"
            v["msg"] = ("（批次收尾重分类）云侧超时，待下轮重做："
                        + str(v.get("msg"))[:90])
            st[k] = v
            n += 1
    if n:
        (HERE / "vlm_ocr_state.json").write_text(
            json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    return n


def _proc_cpu(pid: int) -> float:
    """该进程累计 CPU 秒数（取不到返回 -1）。用于判"进程是否真的在算"。"""
    try:
        r = subprocess.run(
            ["pwsh", "-NoProfile", "-Command",
             f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
             f"if ($p) {{ [math]::Round($p.CPU, 1) }}"],
            capture_output=True, text=True, timeout=30)
        s = (r.stdout or "").strip()
        return float(s) if s else -1.0
    except Exception:  # noqa: BLE001
        return -1.0


def _batch_proc_cpu() -> float:
    """当前批 `vlm_ocr` 全部进程的累计 CPU 秒数之和（-1 表示取不到）。"""
    tot = 0.0
    got = False
    for pid in _procs():
        c = _proc_cpu(pid)
        if c >= 0:
            tot += c
            got = True
    return tot if got else -1.0


def _liveness_sig(cfg: dict) -> tuple:
    """存活签名 `(已完成, 已失败, 待本地, 总数, 日志mtime, CPU秒)`——**变了才叫在干活**。

    只用"进程是否存在"判活会把卡死当健康（实测批次 3 卡在 8/500 三分钟、
    CPU 30 秒只涨 0.7 秒）。签名纳入三个证据：
      - **进度**：state 里的 (完成, 失败, 待本地, 待人工, 巨型跳过)；
      - **日志 mtime**：云 VLM 每部都留 `[n/N] …` 行，mtime 变即"还在推进"；
      - **进程累计 CPU**（2026-09-15 补）：**本地 VLM 是长时间单篇推理**
        （408 页实测需 68–90 分钟），其间**既不写日志也不写 state，只有 CPU 在涨**。
        没有这一项，任何固定停滞阈值都会短于巨型文档的处理时长 → 误杀 →
        重提同一部 → 又等同样久 → **无限循环**（实测：408 页文档跑到第 10 分钟时
        driver 已在报"停滞 10/30 分钟"）。
    """
    done, failed, total, pending_local, skipped, human = _batch_progress(cfg)
    try:
        mt = (HERE / cfg["log"]).stat().st_mtime
    except OSError:
        mt = 0.0
    return (done, failed, pending_local, total, skipped, human,
            round(mt, 3), round(_batch_proc_cpu(), 1))


def _kill_batch_procs() -> None:
    """杀掉在跑的 `vlm_ocr` 进程（停滞自愈用；state 保证断点续跑）。

    只杀 `vlm_ocr.py`，**不碰 driver 自己**。杀掉是安全的：已完成文档都在
    `vlm_ocr_state.json` 里，重拉后 `targets` 会跳过它们（实测跳过计数正常）。
    """
    for pid in _procs():
        try:
            subprocess.run(["pwsh", "-NoProfile", "-Command",
                            f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
                           capture_output=True, text=True, timeout=30)
            _log(f"已停卡死的 vlm_ocr pid={pid}")
        except Exception as ex:  # noqa: BLE001
            _log(f"停 pid={pid} 失败：{type(ex).__name__}: {ex}")


def _preflight(lp: Path) -> tuple[int, int]:
    """启动前确认清单**真的能解析出目标**（返回 (可解析目标数, 清单条数)）。

    **为什么必须有**（2026-09-15 实测致命，同一个 bug 的第二次现身）：
    `Start-Process -ArgumentList` 传的是**数组**，PowerShell 会用空格重新拼接且
    **不加引号** → 含空格的路径被拆成多个参数 → `--corpus-list` 的值不完整 →
    `vlm_ocr.py` 的 `targets_from_corpus_list` 对每条路径 `p.exists()` 全 False
    → **目标 0 部，退出码 0**。于是它"成功启动了、成功结束了、什么也没做"，
    driver 只看到进度 0/500，20 秒后重拉一次——实测 42 秒内连拉 3 次，
    若不拦住会**多个进程并发跑同一批、重复烧云额度**（用户额度 5000 文件/日）。

    本预检直接复用 `vlm_ocr.targets_from_corpus_list`（**单一所有者**：判"哪些路径
    算目标"的口径与真正跑批的那份代码完全一致），启动前先算一遍：
    能解析出目标才允许拉起；否则**拒绝启动并报出两个数字**，
    让"清单空"和"参数传递坏了"可区分（前者是选批问题，后者是启动问题）。
    """
    try:
        sys.path.insert(0, str(HERE))
        import vlm_ocr as V
        tg = V.targets_from_corpus_list(lp, None)
        obj = json.loads(lp.read_text(encoding="utf-8"))
        return len(tg), len(obj.get("paths") or [])
    except Exception as ex:  # noqa: BLE001
        _log(f"❗预检异常：{type(ex).__name__}: {ex}")
        return -1, -1


def start_batch(cfg: dict) -> bool:
    """按当前配置拉起批量（与 watchdog 同参数）。

    `--corpus-list` 传**绝对路径**（由 `_list_path` 解析）：早先用
    `"var/ocr-loop/" + cfg["list"]` 拼相对路径，**依赖 cwd 恰好是仓库根**——
    cwd 一变就指向不存在的文件，且 `vlm_ocr.py` 会以"0 部待处理"悄悄结束
    （不报错），driver 只会看到"跑完了但一部没动"。绝对路径消除该依赖。
    """
    lp = _list_path(cfg)
    if lp is None:
        _log(f"❗拉起前清单路径解析失败：{cfg.get('list')!r}")
        return False
    got, want = _preflight(lp)
    if got != want or got <= 0:
        _log(f"❗拉起前预检不通过：清单 {want} 条，可解析目标 {got} 条"
             f"（{lp.name}）→ 拒绝启动。判据：两者必须相等且 >0。"
             f"常见原因＝启动参数被空格拆开（路径含空格需加引号）")
        return False
    corpus = str(lp)
    log = str(HERE / cfg["log"])
    err = str(HERE / cfg["err"])
    import os
    e = dict(os.environ)
    e.update({"KS_VLM_ONLY": "1", "KW_DAILY_CLOUD_FILES": "5000"})
    # **PID 走临时文件，不走管道**（2026-09-15 实测致命）：
    # 原先用 `… -PassThru | Select-Object -ExpandProperty Id` 把 pid 打到 **stdout**，
    # 再由 `subprocess.run(capture_output=True)` 读。但 `Start-Process` 启动的
    # 子进程**继承了那个 stdout 写端**（子进程的 stdout 被重定向到日志文件，
    # 但**继承的句柄**仍在），于是管道**不关闭** → `subprocess.run` 一直等到
    # `communicate()` 超时 → **driver 抛 TimeoutExpired 整进程崩掉**
    # （实测 driver 在批次 4 推进到 272/500 时死于此，推进链断）。
    # 改用 `Out-File` 写 pid 到临时文件、再用 5 秒超时读回：**不依赖管道**，
    # 且即使读回超时也能从文件拿到 pid（进程其实已启动）。
    #
    # **第二次修正（同一次实测）**：只把 pid 改走文件还不够——`subprocess.run`
    # 的 `capture_output=True` 仍会建管道，而 `Start-Process` 启动的子进程
    # **继承了那个管道的写端** → `communicate()` 照样等到子进程结束（实测仍 **62.9 秒**）。
    # 故本次**完全不捕获管道**（`stdout=DEVNULL, stderr=DEVNULL`），
    # 包装器自己的输出也用 `*> file` 落文件 → 父进程无管道可等，立刻返回。
    pidfile = HERE / ".last_vlm_pid"
    wrapout = HERE / ".last_vlm_launch.txt"
    for f in (pidfile, wrapout):
        try:
            f.unlink()
        except OSError:
            pass
    cmd = ["pwsh", "-NoProfile", "-Command",
           f"$p = Start-Process -FilePath '{PY}' "
           f"-ArgumentList '-X','utf8','\"var/ocr-loop/vlm_ocr.py\"',"
           f"'--corpus-list','\"{corpus}\"','--docs','9999','--channel','auto',"
           f"'--cloud-timeout','{CLOUD_TIMEOUT_S:.0f}',"
           f"'--cloud-attempts','{CLOUD_ATTEMPTS}','--parallel','{PARALLEL}' "
           f"-RedirectStandardOutput '{log}' -RedirectStandardError '{err}' "
           f"-PassThru -WindowStyle Hidden -WorkingDirectory '{ROOT}'; "
           f"$p.Id | Out-File -Encoding ascii '{pidfile}'"]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       stdin=subprocess.DEVNULL, timeout=90, env=e)
    except subprocess.TimeoutExpired:
        # 启动本身可能已成功，只是包装器没退出 → 仍尝试从 pid 文件取
        _log("（拉起包装器未按时退出，改从 pid 文件取）")
    pid = ""
    for _ in range(10):
        try:
            pid = pidfile.read_text(encoding="utf-8").strip()
        except OSError:
            pid = ""
        if pid:
            break
        time.sleep(0.5)
    _log(f"已拉起批次 #{cfg['batch']}（{cfg['list']}）pid={pid or '?'}")
    return bool(pid)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=500)
    ap.add_argument("--max-batches", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    _write_owner()
    _start_heartbeat()      # 独立线程刷心跳（见 HEARTBEAT_S 注释）
    try:
        _run(a)
    finally:
        # 正常/异常退出都要撤心跳，否则 watchdog 会一直退让、没人拉起批量
        _clear_owner()


def _run(a) -> None:
    for n in range(a.max_batches):
        cfg = BC.current()
        # 1) 等当前批**真正**跑完（进程消失不够——崩溃也会消失）
        done_ok, why = _wait_batch(cfg)
        if not done_ok:
            _log(f"❗批次 #{cfg['batch']} 无法确认完成（{why}）→ 停，不推进")
            return
        # 2) 取基线并判断
        j = scout_and_judge()
        if not j.get("ok"):
            _log(f"❗侦察失败：{j.get('why')} —— 停在此处待人工")
            return
        _log(f"基线：评估 {j['eval']} 部（**未进分母 {j.get('skipped', 0)} 部**："
             f"无 VLM 产物/后端标记 unknown，命中数只覆盖已评估部分）· "
             f"命中 {j['hits']} · 来源 {j['kinds']}")
        if j.get("over_exempt"):
            _log(f"ℹ 已豁免达线 {j['over_exempt']}（台账标 `gate_exempt`："
                 f"该类为「只登记不修判据、内容本身正确」→ 拦截它不产生任何修复动作，"
                 f"故不停链；**命中数字仍照常计入基线**，未被隐藏）")
        if j["over"]:
            _log(f"⚠ **达线类 {j['over']}** —— 按流程应先修复"
                 f"（arbiter plan），故停止推进")
            return
        _log("无达线类 → 继续下一批")

        if a.dry_run:
            _log("（dry-run，不取新批）")
            return

        # 3) 取全新一批并拉起
        rem = len(NB.candidates())
        if rem < a.size:
            _log(f"候选不足（剩 {rem} < {a.size}）→ 停止；语料已基本跑完")
            return
        name = f"work_batch{cfg['batch'] + 1}.json"
        cand = NB.candidates()
        work = NB.pick(cand, a.size)
        # **残留带进本批**（`_carry_over` 是"未到终点"记录的唯一消费者）：
        # 全新语料保证不过拟合，但**不能因此丢掉上一批没做完的文档**——
        # 它们不再出现在任何新清单里，就会被静默遗忘（实测缺陷，见 `_carry_over`）。
        paths, carry = _carry_over([str(p) for p in work])
        obj = {"built_at": time.strftime("%Y-%m-%d %H:%M:%S"), "seed": NB.SEED,
               "n": len(paths), "size_requested": a.size,
               "carried_over": len(carry["carried"]),
               "rule": ("next_batch 自动取（排除库内已用/已跑批次/留出集/撞键）"
                        "＋上一批未到终点的残留（carried_over）"),
               "paths": paths}
        (EV / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        newcfg = BC.set_current(f"evolve/{name}", cfg["batch"] + 1,
                               f"vlm_batch{cfg['batch'] + 1}.log",
                               f"vlm_batch{cfg['batch'] + 1}.err")
        _log(f"新批次 #{newcfg['batch']}：{len(work)} 部全新 + "
             f"**{len(carry['carried'])} 部上批残留重跑 = {len(paths)} 部**"
             f" → {name}（剩余候选 {rem}）")
        if carry["carried"]:
            _log(f"  残留清单（下批必跑）：{carry['carried'][:12]}"
                 + ("…" if len(carry["carried"]) > 12 else ""))
        if carry["readmitted"]:
            _log(f"  ♻ 复归重试 {len(carry['readmitted'])} 部（此前被误判终态的"
                 f"临时性失败，降级窗口后重新排队；本批配额 {READMIT_QUOTA} / "
                 f"硬上限 {READMIT_HARD_CAP}）：{carry['readmitted'][:8]}"
                 + ("…" if len(carry["readmitted"]) > 8 else ""))
        if carry["retired"]:
            _log(f"  ⚠ 转待人工 {len(carry['retired'])} 部（试满 "
                 f"{MAX_CARRY} 次 / 复归后 {READMIT_HARD_CAP} 次 / 能力边界）："
                 f"{carry['retired'][:12]}"
                 + ("…" if len(carry["retired"]) > 12 else ""))
        if not start_batch(newcfg):
            _log("❗拉起失败，停在此处待人工")
            return


if __name__ == "__main__":
    main()
