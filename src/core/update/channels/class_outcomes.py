"""五类**结论**的组装（§11.0 R6c-4）：把"这一次探测"翻译成"五类各自答成什么样"。

## 为什么需要它（以及为什么**不**写五条事件）
设计稿原话是"每类各自记一条事件"。动手前先量了三条（见 `docs/CHANNEL-R6C-DESIGN.md` §3.2.2）：
1. **五类的第一候选今天几乎总是同一根棒**（11/11 个真库号：`GB/T`/`GBZ`→`official_gb`，`GB `→`ndls`）
   ⇒ 按类问**不会让巡检去问不同渠道**，多的只是记账；
2. **事件会互相压掉**：`update_change_event.change_type` 有 CHECK 约束（只 5 个值），
   而去重键是 `(doc_id, standard_no, change_type)` ⇒ 五类里同为 `no_change` 的会被压成一条、
   类的信息**静默丢失**；要分开就得改 CHECK（= 改 schema，§3.3 明确不做）；
3. 事件量最多 ×5，而**每类各自记结论**这个原意不必靠 ×5 行实现。
⇒ 落法：**那一条** judged 事件的 `latest_info.classes` 里放五类的结论；本模块负责组装它。

## 词汇表（**封闭**，别在别处自己造词）
每类一个 `status`：
- `answered`     —— 这一类的结论拿到了（`conclusion` 里有东西）；
- `not_answered` —— 没拿到，`reason` 说明为什么。

`reason` 取值（前三个来自 `question_router.route_report`，后两个是本模块的判断）：
- `no_capability` —— **没有任何渠道**声明能答这一类（结构性缺口）；
- `off_chain`     —— 有渠道能答，但都不在这一号的链上；
- `all_down`      —— 在链上、能答，但今天全被判死；
- `not_probed`    —— 候选存在，但**这次的探测没轮到它**（第一棒先命中了）——**这是"没问"，
                     不是"问不出来"**，两者在证据里必须分开写；
- `channel_gave_no_field` —— 问了、也命中了，但这根棒对**这一类**该给的东西没给
                     （例如 `official_gb` 对"废止"只有状态串、没有废止日期）。此时
                     `completeness` 会显示该渠道在该类的 `partial` 判定。

⚠ **"有候选"≠"答了"**：本模块只按"**是哪根棒答的**"来判 `answered`，
不把"链上还有其他候选"当成已经查过（那正是"让业主以为查过了"的形态）。
"""
from __future__ import annotations

from typing import Any

from src.core.update import channel_answers as ca

#: 每类的 `status` 词表（封闭）
STATUSES: tuple[str, ...] = ("answered", "not_answered")
#: `reason` 词表（封闭）：前三个来自路由器的空候选原因，后两个是本模块的判断
REASONS: tuple[str, ...] = ("ok", "no_capability", "off_chain", "all_down",
                            "not_probed", "channel_gave_no_field")
#: 结构性"答不出来"的原因（与"这次没问"区分：`not_probed` **不在**这一组）
UNANSWERABLE_REASONS: frozenset[str] = frozenset({"no_capability", "off_chain", "all_down"})


def conclusion_for(cls: str, result: Any) -> dict[str, Any] | None:
    """一根棒的探测结果 → 它对**这一类**的结论；给不出该给的字段 ⇒ `None`。

    `result` 是 `ChannelResult`。**只从它已有的字段取**，不猜、不补。

    ⚠ **"否定的结论"也是结论**（这一条是拿真机演示改出来的，见 `var/tmp/r6c4-demo-out.txt`）：
    我第一版只在"命中"时才算答了，于是"现行"的标准在 `废止` 类上被判成 `not_answered`
    ——可"`现行`"本身就是"没有废止"的**依据**（这一类问的正是"有没有废止日期或依据"）。
    按第一版的口径，几乎每个号都会有 `废止/修订` 两个"没答出来"，"有未答不算 done"那条恒等式
    就会把绝大多数号判成没做完 —— 那是**把语义搞错**，不是数据缺。
    所以：**渠道只要给出了这一类相关的判断就算 `answered`**（正面或否定），
    而"这根棒这类判断可信到什么程度"由 `completeness`（b35 的 supported/partial）如实带出。

    逐类：
    - `发布`   ：要**发布日期** ⇒ `published_date`；没有**就是没有**（`None`）——
      不许拿实施日期顶上（那正是 R6c-3c/3e 修掉的错标；真机上 `mee` 只有实施日期，
      所以它对"发布"确实答不了）；
    - `修订`   ：要"有没有新版/被代替" ⇒ `change_type` 三态都算答了
      （`new_version`/`superseded` 有新版，`no_change` 明确没有）；
    - `废止`   ：要**废止状态与日期** ⇒ 有 `legal_status` 就算答了
      （`withdrawn` 时把 `effective_date` 作为废止日期带上——`ndls` 的约定就是废止号以废止日期为关键日期；
      非废止时`withdrawn_date` 为 `None`，那是"没有废止日期"这个**结论**，不是缺字段）；
    - `现行性` ：要**今天的法律状态** ⇒ `legal_status`；
    - `编号核验`：要"这个号在权威库里存不存在" ⇒ `found`（本模块只在 `found=True` 时被调用，
      所以这里给的是"存在"，外加权威侧回的号 `latest_version` 供比对写法）。
    """
    if cls == "发布":
        d = getattr(result, "published_date", None)
        return {"date": d} if d else None
    if cls == "修订":
        ct = getattr(result, "change_type", None)
        if ct is None:
            return None
        return {"change": ct, "new_version": getattr(result, "latest_version", None)}
    if cls == "废止":
        st = getattr(result, "legal_status", None)
        if not st:
            return None
        return {"state": st,
                "withdrawn_date": getattr(result, "effective_date", None)
                if st == "withdrawn" else None}
    if cls == "现行性":
        st = getattr(result, "legal_status", None)
        return {"state": st} if st else None
    if cls == "编号核验":
        return {"exists": True, "authority_version": getattr(result, "latest_version", None)}
    raise ValueError(f"不是五类之一：{cls!r}（只能是 {list(ca.CLASSES)}）")


def _verdict(channel_id: str, cls: str,
             table: dict[str, dict[str, Any]] | None) -> str | None:
    """该渠道在该类上的能力判定（来自 b35 的逐条审计）；没有审计记录 ⇒ `None`。

    ⚠ 目前**只用于记录**（写进 `completeness`），**不参与排序**——因为模拟发现
    "按 verdict 排序"会把 `发布` 类改坏（`official_gb` 判 supported 但产出的是实施日期）。
    """
    entry = (table if table is not None else ca.load_answers()).get(channel_id) or {}
    detail = entry.get("answers_detail") or {}
    v = (detail.get(cls) or {}).get("verdict")
    return str(v) if v else None


def build_classes(report: dict[str, dict[str, Any]], *,
                  channel_id: str,
                  result: Any,
                  table: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """`route_report` + "谁答的" + 那根棒的结果 → 五类结论汇总。

    Returns:
        `{"classes": {类: {...}}, "unanswered": [...], "unanswerable": [...]}`
        —— `unanswered` 是**没答出来**的类（含 `not_probed` 与结构性缺口）；
        `unanswerable` 只含**结构性**那些（`no_capability`/`off_chain`/`all_down`）。
        调用方用 `unanswerable` 做"不算 done"的判据（设计稿 §3.2.2 第 2 条），
        但**两个列表都要如实出现在证据里**：`not_probed` 与"答不出来"不是一回事。
    """
    out: dict[str, dict[str, Any]] = {}
    for cls, item in report.items():
        cands = list(item.get("channels") or [])
        verdict = _verdict(channel_id, cls, table)
        if channel_id in cands:
            concl = conclusion_for(cls, result)
            if concl is None:
                out[cls] = {"status": "not_answered", "reason": "channel_gave_no_field",
                            "channel": channel_id, "completeness": verdict}
            else:
                out[cls] = {"status": "answered", "reason": "ok", "channel": channel_id,
                            "completeness": verdict, "conclusion": concl}
        elif cands:
            # 候选在，但这次没轮到它（第一棒先命中了）——**不是**"问不出来"
            out[cls] = {"status": "not_answered", "reason": "not_probed",
                        "candidates": cands}
        else:
            out[cls] = {"status": "not_answered", "reason": str(item.get("reason"))}
    unanswered = [c for c, v in out.items() if v["status"] != "answered"]
    unanswerable = [c for c in unanswered if out[c]["reason"] in UNANSWERABLE_REASONS]
    return {"classes": out, "unanswered": unanswered, "unanswerable": unanswerable}


def build_classes_for_miss(report: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """**整条链都没命中**时的五类记录（没有"谁答的"这回事）。

    用途：`not_found`（灰）也要能回答"这五类各自为什么没答出来"——
    是**结构性**（没有任何渠道能答 / 都不在链上 / 都在链上但今天全挂），
    还是**候选在、只是这次都没命中**（记 `not_probed`：链上有棒能答，但这一轮问空了）。
    ⚠ 与 `build_classes` 的区别只有一个：这里**没有** `channel`/`conclusion`/`completeness`。
    """
    out: dict[str, dict[str, Any]] = {}
    for cls, item in report.items():
        cands = list(item.get("channels") or [])
        if cands:
            out[cls] = {"status": "not_answered", "reason": "not_probed",
                        "candidates": cands}
        else:
            out[cls] = {"status": "not_answered", "reason": str(item.get("reason"))}
    unanswered = list(out)
    unanswerable = [c for c in unanswered if out[c]["reason"] in UNANSWERABLE_REASONS]
    return {"classes": out, "unanswered": unanswered, "unanswerable": unanswerable}
