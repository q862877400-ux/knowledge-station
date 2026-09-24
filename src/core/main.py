"""入口：python -m src.core.main"""
import os
import threading

from src.core.api.server import run


def _normalize_no_proxy() -> None:
    """启动时把 ``NO_PROXY`` 里的 ``[::1]`` 折成 ``::1``（2026-09-24 加）。

    **为什么必须在这里做（本仓已经被这个坑咬了 5 次）**：
    本机环境 ``NO_PROXY=localhost,127.0.0.1,::1,[::1]``，而 httpx 解析 ``NO_PROXY``
    时遇到方括号 IPv6 字面量会抛 ``InvalidURL: Invalid port: ':1]'``——
    **是在构造客户端那一刻抛**，不是发请求时。各模块此前各自绕过（``ccs_fetcher``、
    ``ccs_backfill``、``channels/base.py``、``pipeline.py`` 的注释都记着这件事），
    但**取证调大模型那条路（``ks_answer`` / ``deepseek_client`` 的 OpenAI 客户端）没绕**。

    实测后果（2026-09-24）：``ks_answer`` 每一次取证都返回
    ``"DeepSeek 取证调用失败: Invalid port: ':1]'"`` ⇒ **推导区与结论区全空**，
    只剩证据区；界面看起来正常，实际不产出答案。

    **为什么在这里一次性修**（而不是给第 6 个模块再加一遍绕过）：
    方括号 IPv6 在 ``NO_PROXY`` 里本来就是**不规范写法**，折成 ``::1`` 语义完全相同
    （都表示本机 IPv6 回环）。放在入口做 ⇒ 进程内**所有** HTTP 栈一次受益，
    以后新写的模块也不会再踩。

    ⚠ 若将来确实需要用方括号写法表达别的意思，请改这里而不是绕过——本仓已有 5 处
    注释证明"逐模块绕过"这条路走不通（总会漏下一个调用点）。
    """
    raw = os.environ.get("NO_PROXY") or os.environ.get("no_proxy")
    if not raw or "[::1]" not in raw:
        return
    fixed = raw.replace("[::1]", "::1")
    os.environ["NO_PROXY"] = fixed
    os.environ["no_proxy"] = fixed


def _warmup_figure_ocr() -> None:
    """后台预热流程图重绘的 RapidOCR 模型（2026-08-29）。

    实测冷启动首图请求阻塞 ~60s（模型检索+加载在请求线程内），预热后
    首图 ~4s。失败静默——预热失败只影响首次响应速度，不影响正确性。
    """
    def _load():
        try:
            from src.core.figure_redraw import get_ocr
            get_ocr()
        except Exception:
            pass
    threading.Thread(target=_load, name="figure-ocr-warmup", daemon=True).start()


if __name__ == "__main__":
    _normalize_no_proxy()
    _warmup_figure_ocr()
    run()
