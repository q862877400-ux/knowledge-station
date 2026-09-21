"""归位计划：把「现有每一篇按当前显示的分类该落到哪个目录」算出来（KB-FOLDER-PLAN §五第 1 步）。

方案真源：``docs/KB-FOLDER-PLAN.md``。本模块是**纯函数 + 一个批量落库入口**，
不带界面、不带 HTTP 接口（第 2/3 步的事）。

════ 两条纪律 ════

1. **分类口径只有一份**：一律走 ``src.core.knowledge.doc_catalog.classify_document``
   （页面「文件目录」面板读时推导用的就是它，``server.py`` 的 ``/documents/categories``）。
   本模块**不另写一份判断** —— 两份判断迟早会漂移，而"预览说会落到 A、真跑落到 B"
   是最坏的一种错。
2. **无分类 = classify_document 的两个兜底桶**（这两桶进「待分类」，**不建目录**）：

   * ``level2 == '其他标准'`` —— 标准号**是**标准（``_is_standard_no`` 命中），
     但 CCS 标签与本地映射表 ``LOCAL_CCS`` 都没有它 ⇒ 拿不到任何分类信息。
   * ``level2 == '未定级'`` —— 法规树里 ``legal_hierarchy`` 映射不到，标题关键词也没命中。

   除此之外还有第三类"空/异常值"（值为空串、名字或路径超上限等），一律进 ``anomalies``，
   **不静默塞进某个目录**。

════ 目录树 ════

四级路径 = ``(top_name, level2, level3, level4)``，即页面上那棵树（方案 §一定案
"按当前显示的分类"）。每一级前缀都是一个目录，所以 L1/L2/L3 都靠"它下面的篇数
（含更深层）"才有意义 —— 计数因此分 ``docs_direct``（直接放在这一级）与
``docs_deep``（这一级及其所有下级，去重）。

⚠ 上面那条是**分类口径**的路径；**真树**还少一级（标准树被跳过的那层）—— 两者的映射
是 ``tree_path_of``，唯一所有者（见该函数与 ``SKIPPED_PLAN_TOP`` 的注释）。落库脚本
（``apply-folder-filing.py``）与接口的建议匹配（``folder_store.suggest_folder_for_doc``）
都从这一处取，不许各写一份。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from src.core.knowledge import folder_store
from src.core.knowledge.doc_catalog import STD_LEVEL1_NAME, classify_document

#: 「无分类」的两个兜底桶 → 进「待分类」，不建目录
NO_CLASS_LEVEL2: str = "其他标准"
UNDEFINED_LEVEL2: str = "未定级"

#: ─────────── 分类口径 ↔ **真树** 的唯一所有者（2026-09-21 复核打回后收成一处）───────────
#
# 为什么需要这层映射：分类口径（``classify_document``）算出来的是**文档分类体系**的路径，
# 真树（``scripts/apply-folder-filing.py`` 落库的那棵，也是 ``/api/v1/kb/folders`` 读的
# 那一棵）**故意跳过了标准树的第一层**——业主 2026-09-21 定：「国家标准·行业标准·团体标准」
# 挂在真顶层「标准」下面就是**重复的一层**，所以它的下级（``A 综合``…）直接挂「标准」。
# ⇒ 拿分类口径的 L1 名字去真树里匹配**永远不中**（复核实测：6036 篇已归位文件精确命中 0，
#   把第一段换成真顶层「标准」后 6036/6036）。这条规则以前散在脚本里（``PLAN_STD_LEVEL1`` /
#   ``STANDARD_TOP``），接口侧完全不知道 ⇒ 本模块把它收成**唯一所有者**：
#   · 顶层叫什么 —— ``folder_store.PREBUILT_TOP_NAMES``（**唯一所有者**；但要注意
#     **目前只有落库脚本消费它**，`routes_kb_folders.py` 是不限制顶层名字的 ——
#     原写"脚本与接口都从那儿取"是**旧错话**，复核 2026-09-21 打回，此处保留更正）；
#   · 跳过哪一段 —— ``SKIPPED_PLAN_TOP``（= ``doc_catalog.STD_LEVEL1_NAME``，那段的名字
#     归分类口径所有，这里只说"真树跳过它"）；
#   · 怎么映射 —— ``tree_path_of``（**唯一实现**：脚本的跳层逻辑与接口的建议匹配都得与它一致）。
# ⚠ 改这里 = 改真树的形状；``tests/test_apply_folder_filing.py`` 有一条断言钉住
#   「标准树不许出现被跳过的那一层」。
STANDARD_TOP_NAME: str = folder_store.STANDARD_TOP_NAME
SKIPPED_PLAN_TOP: str = STD_LEVEL1_NAME

#: 路径的**显示**分隔符。目录名里可以带 `/`（CCS 区间名 `P15/19` 自带的），
#: 所以显示路径不能用 `/` 连 —— 那会看不出这条路径有几级。
PATH_SEP = " › "


def tags_of(doc: Any) -> list[str]:
    """``domain_tags`` 统一成 list（库里是 JSON 字符串；已是 list 就用它）。"""
    raw = doc.get("domain_tags") if hasattr(doc, "get") else None
    if isinstance(raw, list):
        return [str(t) for t in raw if isinstance(t, str)]
    try:
        parsed = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return [str(t) for t in parsed if isinstance(t, str)] if isinstance(parsed, list) else []


def path_of(cls: dict) -> tuple[str, str, str, str]:
    """分类结果 → 四级目录路径（L1..L4，**分类口径**；真树路径要再过 ``tree_path_of``）。"""
    return (str(cls.get("top_name") or ""), str(cls.get("level2") or ""),
            str(cls.get("level3") or ""), str(cls.get("level4") or ""))


def tree_path_of(path: Iterable[str]) -> tuple[str, ...]:
    """**分类口径路径 → 真树路径**（唯一所有者，理由见上面的常量区注释）。

    规则只有一条：第一段若是 ``SKIPPED_PLAN_TOP``（标准树那段被跳过的重复层），
    就换成真顶层名 ``STANDARD_TOP_NAME``（段数因此少一级）；其余原样。

    真树路径一定不会出现被跳过的那一段 —— 这正是 ``suggest_folder_for_doc``
    拿"分类算出来的路径"去真树里找时必须先走这一步的原因。
    """
    segs = tuple(str(s) for s in path)
    if not segs:
        return ()
    head = STANDARD_TOP_NAME if segs[0] == SKIPPED_PLAN_TOP else segs[0]
    return (head, *segs[1:])


def show_path(path: Iterable[str]) -> str:
    return PATH_SEP.join(path)


def _register(cls: dict, doc: dict[str, Any], nodes: dict[str, dict[str, Any]],
              assignments: list[dict[str, Any]], anomalies: list[dict[str, Any]]) -> bool:
    """给一篇**已分类好**的文档登记目录节点与归属。返回 False = 因异常没归位。"""
    doc_id = str(doc["doc_id"])
    path = path_of(cls)
    empty = [k for k, v in zip(("L1", "L2", "L3", "L4"), path) if not v.strip()]
    if empty:
        anomalies.append({"kind": "empty_level", "doc_id": doc_id,
                          "detail": f"{'/'.join(empty)} 为空；path={path!r}"})
        return False
    if len(path) > folder_store.MAX_DEPTH:
        anomalies.append({"kind": "depth_over_limit", "doc_id": doc_id,
                          "detail": f"路径 {len(path)} 级 > 上限 {folder_store.MAX_DEPTH}"})
        return False
    if len(show_path(path)) > folder_store.MAX_PATH_LEN:
        anomalies.append({"kind": "path_too_long", "doc_id": doc_id,
                          "detail": f"路径长 {len(show_path(path))} > 上限"
                                    f" {folder_store.MAX_PATH_LEN}：{show_path(path)}"})
        return False
    for seg in path:
        if len(seg) > folder_store.MAX_NAME_LEN:
            anomalies.append({
                "kind": "name_too_long", "doc_id": doc_id,
                "detail": f"「{seg}」长 {len(seg)} > 上限 {folder_store.MAX_NAME_LEN}"})
            return False

    # 逐级登记目录节点（父先子后：depth 递增 ⇒ 上级一定先建好）
    parent_key: str | None = None
    for depth in range(1, len(path) + 1):
        key = show_path(path[:depth])
        if key not in nodes:
            nodes[key] = {"key": key, "name": path[depth - 1], "parent_key": parent_key,
                          "depth": depth, "path": list(path[:depth]),
                          "docs_direct": 0, "docs_deep": 0}
        nodes[key]["docs_deep"] += 1
        parent_key = key
    assert parent_key is not None
    nodes[parent_key]["docs_direct"] += 1
    assignments.append({"doc_id": doc_id, "key": parent_key, "path": list(path)})
    return True


def plan_filing(docs: list[dict[str, Any]]) -> dict:
    """算归位计划（**纯函数**：不碰库、不落盘）。

    ``docs``: 每篇一个 dict，至少要有 ``doc_id`` / ``standard_no`` / ``standard_name``；
    ``domain_tags`` 可以是 JSON 字符串或 list；``legal_hierarchy``/``doc_type`` 可选。
    带 ``catalog_hidden`` 的行进 ``hidden_docs``、**不参与归位**
    （与 ``/documents/categories`` 的 ``WHERE catalog_hidden = 0`` 同口径）。
    """
    nodes: dict[str, dict[str, Any]] = {}
    assignments: list[dict[str, Any]] = []
    no_class: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    hidden: list[str] = []
    seen_docs: set[str] = set()

    for doc in docs:
        doc_id = str(doc.get("doc_id") or "")
        if not doc_id:
            anomalies.append({"kind": "missing_doc_id", "detail": repr(doc)[:200]})
            continue
        if doc_id in seen_docs:
            anomalies.append({"kind": "duplicate_doc_id", "detail": doc_id, "doc_id": doc_id})
            continue
        seen_docs.add(doc_id)
        if int(doc.get("catalog_hidden") or 0) == 1:
            hidden.append(doc_id)
            continue

        d = dict(doc)
        d["domain_tags"] = tags_of(d)
        try:
            cls = classify_document(d)
        except Exception as e:                   # 分类函数自己炸了也要如实记下
            anomalies.append({"kind": "classify_error",
                              "detail": f"{type(e).__name__}: {e}", "doc_id": doc_id})
            continue

        bucket = str(cls.get("level2") or "")
        if bucket in (NO_CLASS_LEVEL2, UNDEFINED_LEVEL2):
            no_class.append({
                "doc_id": doc_id,
                "standard_no": doc.get("standard_no"),
                "standard_name": doc.get("standard_name"),
                "bucket": bucket,
                "reason": ("标准号是标准，但库里没有它的分类信息（CCS 标签与本地映射表都没有）"
                           if bucket == NO_CLASS_LEVEL2 else
                           "法规：效力层级映射不到，标题关键词也没命中"),
            })
            continue
        _register(cls, doc, nodes, assignments, anomalies)

    ordered = sorted(nodes.values(), key=lambda n: (list(n["path"]), n["key"]))
    return {
        "total_docs": len(docs),
        "planned_docs": len(assignments),
        "hidden_docs": hidden,
        "no_class": no_class,
        "anomalies": anomalies,
        "nodes": ordered,
        "assignments": assignments,
    }


def tree_lines(plan: dict, max_nodes: int = 4000) -> list[str]:
    """目录树的**给人看**的行（按层级缩进，括号里是"含更深层"篇数）。"""
    lines: list[str] = []
    for n in plan["nodes"]:
        if len(lines) >= max_nodes:
            lines.append(f"…（更多目录省略，全量 {len(plan['nodes'])} 个，见 JSON）")
            break
        indent = "  " * (n["depth"] - 1)
        lines.append(f"{indent}- {n['name']}（{n['docs_deep']} 篇；本级直接 "
                     f"{n['docs_direct']} 篇）")
    if not lines:
        lines.append("（没有要建的目录）")
    return lines


def summarize_plan(plan: dict) -> dict:
    """清单要的关键数字（层级计数 + 无分类成因归类 + 异常归类）。"""
    by_depth: dict[int, int] = {}
    by_top: dict[str, dict[str, int]] = {}
    for n in plan["nodes"]:
        by_depth[n["depth"]] = by_depth.get(n["depth"], 0) + 1
        if n["depth"] == 1:
            by_top[n["name"]] = {"folders": 0, "docs_deep": n["docs_deep"]}
        elif n["depth"] == 2:
            top = n["path"][0]
            by_top.setdefault(top, {"folders": 0, "docs_deep": 0})["folders"] += 1
    no_class_by_bucket: dict[str, int] = {}
    for item in plan["no_class"]:
        no_class_by_bucket[item["bucket"]] = no_class_by_bucket.get(item["bucket"], 0) + 1
    anomalies_by_kind: dict[str, int] = {}
    for a in plan["anomalies"]:
        anomalies_by_kind[a["kind"]] = anomalies_by_kind.get(a["kind"], 0) + 1
    return {
        "total_docs": plan["total_docs"],
        "planned_docs": plan["planned_docs"],
        "hidden_docs": len(plan["hidden_docs"]),
        "no_class_total": len(plan["no_class"]),
        "no_class_by_bucket": no_class_by_bucket,
        "anomaly_total": len(plan["anomalies"]),
        "anomalies_by_kind": anomalies_by_kind,
        "folders_by_depth": {str(k): v for k, v in sorted(by_depth.items())},
        "folders_total": len(plan["nodes"]),
        "by_top": by_top,
    }


def apply_plan(db_path: Path | None, plan: dict,
               placed_by: str = "filing-preview") -> dict:
    """把计划落进**指定的库**（``db_path``）—— 单事务，全成或全败。

    已归位的文件写 ``stage='filed'`` 并记"谁在什么时候放进了哪个目录"；无分类的写
    ``stage='queued'``（= 进「待分类」排队，等着被识别或人工处理）。
    """
    nodes = [{"key": n["key"], "name": n["name"], "parent_key": n["parent_key"]}
             for n in plan["nodes"]]
    memberships = [{"folder_key": a["key"], "item_kind": "file", "item_id": a["doc_id"]}
                   for a in plan["assignments"]]
    states: list[dict[str, Any]] = [
        {"doc_id": a["doc_id"], "stage": "filed", "placed_folder_key": a["key"],
         "placed_by": placed_by} for a in plan["assignments"]]
    states += [{"doc_id": item["doc_id"], "stage": "queued", "placed_by": placed_by}
               for item in plan["no_class"]]
    return folder_store.build_folder_tree(nodes, memberships, states, db_path=db_path)


def build_report(plan: dict, *, generated_at: str, real_db: dict, copy_db: str,
                 copy_removed: bool, timing: dict, apply_result: dict,
                 verify: dict) -> dict:
    """把计划、实测耗时、落库结果、自证拼成**机器可读报告**（清单文本由它渲染）。"""
    return {
        "generated_at": generated_at,
        "real_db": real_db,
        "copy_db": copy_db,
        "copy_removed": copy_removed,
        "timing": timing,
        "apply_result": apply_result,
        "verify": verify,
        "summary": summarize_plan(plan),
        "tree_lines": tree_lines(plan),
        "no_class": plan["no_class"],
        "anomalies": plan["anomalies"],
        "nodes": plan["nodes"],
    }


def render_text(report: dict) -> str:
    """把报告渲染成**给人看**的清单（业主过目用的那一份）。"""
    s = report["summary"]
    L: list[str] = []
    add = L.append
    add("# 知识库多级目录 · 归位预览清单")
    add("")
    add(f"生成时间：{report['generated_at']}")
    add(f"真库：{report['real_db']['path']}")
    add(f"- 大小 {report['real_db']['size']:,} 字节")
    add(f"- 跑之前 mtime={report['real_db']['mtime_before']}，"
        f"跑之后 mtime={report['real_db']['mtime_after']}")
    add(f"- **真库未被改动**：{report['real_db']['untouched']}"
        f"（大小与修改时间前后一致才算 True）")
    add(f"副本：{report['copy_db']}")
    add(f"- 用完已删：{report['copy_removed']}")
    add("")
    add("## 一、关键数字")
    add("")
    add(f"- 库里总共 **{s['total_docs']}** 篇；本次归位 **{s['planned_docs']}** 篇")
    add(f"- **没有分类的 {s['no_class_total']} 篇**（进「待分类」，不建目录）")
    for bucket, n in sorted(s["no_class_by_bucket"].items(), key=lambda kv: -kv[1]):
        add(f"    - 兜底桶「{bucket}」：{n} 篇")
    add(f"- 要建的目录：**{s['folders_total']}** 个"
        f"（按层级 {s['folders_by_depth']}）")
    add(f"- 异常：**{s['anomaly_total']}** 条"
        + (f"（{s['anomalies_by_kind']}）" if s["anomaly_total"] else ""))
    add(f"- 不参与归位（页面上本来就隐藏 catalog_hidden=1）：{s['hidden_docs']} 篇")
    add(f"- 落库核对：{report['verify']}")
    add("")
    add("## 二、一级目录各多少篇")
    add("")
    add("| 一级目录 | 下级目录数 | 篇数（含更深层） |")
    add("|---|---|---|")
    for name, v in sorted(s["by_top"].items(), key=lambda kv: -kv[1]["docs_deep"]):
        add(f"| {name} | {v['folders']} | {v['docs_deep']} |")
    add("")
    add("## 三、目录树（按层级；括号内为含更深层篇数）")
    add("")
    L.extend(report["tree_lines"])
    add("")
    add("## 四、现在没有分类的那些（逐篇）")
    add("")
    add("| # | 标准号 | 名称 | 兜底桶 |")
    add("|---|---|---|---|")
    for i, item in enumerate(report["no_class"], 1):
        add(f"| {i} | {item['standard_no']} | {item['standard_name']} | {item['bucket']} |")
    add("")
    add("## 五、异常")
    add("")
    if not report["anomalies"]:
        add("（无）")
    else:
        for a in report["anomalies"][:200]:
            add(f"- [{a['kind']}] {a.get('doc_id', '')} {a['detail']}")
        if len(report["anomalies"]) > 200:
            add(f"- …还有 {len(report['anomalies']) - 200} 条，完整清单见 JSON")
    add("")
    add("## 六、耗时")
    add("")
    for k, v in report["timing"].items():
        if k == "est_real_seconds":
            continue
        add(f"- {k}: {v} 秒")
    add(f"- **估算真库上跑一次约 {report['timing']['est_real_seconds']} 秒**"
        "（= 读 + 分类 + 落库；不含首次建表与备份真库的时间）")
    return "\n".join(L) + "\n"
