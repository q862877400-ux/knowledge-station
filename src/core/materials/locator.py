# -*- coding: utf-8 -*-
"""**引用锚点稳定性**（方案 §12 未决第 5 条 = Phase B 必解）。

## 问题（为什么需要这个模块）
`material.content_hash` 是**源文件字节**的哈希；而 `material_chunk` 的
`char_start` / `char_end` / `page` 是**解析结果**的坐标。两者之间隔着**解析器**：
换 PyMuPDF 版本、换 MinerU backend、开 `deep_fallback` 走云解析，甚至同一版本换机器，
都可能让同一份 PDF 解析出**不一样的文本**——于是所有已存区间悄悄指向别处，
而引用、报告、界面看起来一切正常。**这是"看起来很正常的错引用"，比报错危险得多。**

## 三道判据（代价从低到高，**不要跳级下结论**）
1. `locator_health(material)` —— 便宜判据，比**两样**东西：
   - **解析器指纹**：入库时记的 vs 现在这台机器的（判"**解析器**有没有变"）；
   - **源文件字节哈希**：`material.content_hash`（入库时的源文件 sha256）vs 现在磁盘上的
     （判"**输入**有没有变"）。一次**流式** sha256（`material_ingest.file_hash`），
     不像重解析那样起子进程。
   取值 `ok` / `stale` / `unknown`（入库时没记 = 2026-09-17 之前的材料）/ `no_locators`。
   ⚠ **只比指纹是不够的**（独立复核 b9 的 MEDIUM-1，2026-09-18 修）：`current_fingerprint_for`
   只看**后缀**，所以"用户把更新版 PDF 放回项目目录再扫一次"（正常操作）或"源文件被删"
   都会让指纹**一字不变**——只比指纹会报 `ok`，而那正是本模块要防的**静默失效**。
   ⚠ 因此它比"只比字符串"贵一点（每个材料一次源文件读取）；换来的是
   "**输入变了不会被说成 ok**"。真嫌贵，正确的优化是**缓存源文件的 size/mtime**（登记为待办），
   **不是**把这条判据删掉。
2. `reverify_material_locators(material_id)` —— **重解析比对**：用当前的解析器重新解析
   **留存的源文件**，算派生全文哈希，与入库时记的 `derived_text_hash` 比：
   `match` / `mismatch`（**已存区间失效了，必须修数据**）/ `unavailable`
   （没有源文件——网页材料就是这样）。**贵**（PDF 是子进程 + 秒级到分钟级），
   所以它是**显式动作**，不是每次回答都跑。
3. 人（业主）看到 `mismatch`/`stale` 之后决定怎么办：重解析并重建区间，或把这份材料弃用。

## 诚实边界（这一层的结论怎么说才不算骗人）
- 指纹**相同**只说明"影响解析的那些东西看起来没变"，**不等于**派生文本一定相同
  （环境里的隐藏变量、非确定性 OCR 都可能不在指纹里）⇒ `ok` 的措辞是
  "**未发现变化**"，不是"保证一致"。真正的保证只有 ② 的 `match`。
- 指纹**不同**也**不等于**区间一定坏了 ⇒ `stale` 的措辞是"**需要复算**"，不是"已经坏了"。
- **源文件字节变了**（`content_hash` 对不上）⇒ `stale`，且措辞点明是**源文件**变了：
  这比"指纹变了"更确定——已存区间是按**旧字节**解析出来的，对新文件不再成立。
- **源文件不在磁盘上** ⇒ `unknown`（取不到当前指纹，更无法复算），**不是 ok**。
- `unavailable` **不是** `ok`：它是 `REVERIFY_STATUSES` 的词（`locator_health` **永远不会**
  返回它）——网页材料没有留存原始字节，**无法**复算，如实说"验不了"。
- 老材料（NULL）一律 `unknown`：**不假装 ok**（这与 §10.39 那条"不知道就别当好"同一原则）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.ingestion import material_ingest as mi
from src.core.storage import material_repo as mr

#: `locator_health` 的取值（**判据的取值域写在一处**，界面/报告别自己发明词）。
#: ⚠ 没有 `no_text` 这一档：解析不出文本的材料**必然** `chunk_count == 0` ⇒ 落到
#: `no_locators`（没有区间可言）。少一个**永远不会被返回**的取值，就少一处"看起来覆盖了"。
HEALTH_STATUSES = ("ok", "stale", "unknown", "no_locators")

#: `reverify_material_locators` 的取值域。
REVERIFY_STATUSES = ("match", "mismatch", "unavailable")


def current_fingerprint_for(material: dict[str, Any]) -> str | None:
    """**现在这台机器**会用什么指纹解析这份材料的源文件（取不到就 None）。

    - 网页材料（`origin='collected'` / 没有 `raw_path`）：指纹是采集通道那一个常量
      （`collect.COLLECT_PARSER_FINGERPRINT`）——它同样会随算法变更而变。
    - 文件材料：按后缀走 `material_ingest._provenance_fingerprint`（**同一个所有者**）。
      ⚠ PDF 那条路的指纹含 `text_layer` / `ocr` 两项，而那两项只有**真解析过**才知道
      ⇒ 这里交给调用方在重解析后判定；**未解析**时返回的指纹是"结构性"的那部分，
      与入库时记的完整指纹**不可直接比**（见 `locator_health` 对 PDF 的处理）。
    """
    from src.core.materials import collect as co
    if (material.get("origin") or "") == "collected" and not material.get("raw_path"):
        return co.COLLECT_PARSER_FINGERPRINT
    raw = material.get("raw_path")
    if not raw:
        return None
    suffix = Path(str(raw)).suffix.lower()
    if suffix not in mi.SUPPORTED_SUFFIXES:
        return None
    return mi._provenance_fingerprint(suffix, deep_fallback=False)  # noqa: SLF001 — 同一所有者


def source_bytes_match(material: dict[str, Any]) -> bool | None:
    """磁盘上的源文件字节**是否与入库时记的一致**（`None` = 判不了）。

    - `True`：一致（`material.content_hash` 与现在的流式 sha256 相同）；
    - `False`：**不一致** ⇒ 输入变了，已存区间是按旧字节算出来的；
    - `None`：判不了——没有源文件（网页采集件）、路径为空、或文件**不在磁盘上**。

    ⚠ 与"解析器指纹"是**两条独立的轴**（独立复核 b9 的 MEDIUM-1）：
    指纹只看**后缀**，所以"换成另一份同名 PDF 再扫一次"不会让指纹变动。
    便宜判据必须**两条都比**，否则"看起来很正常的错引用"恰好出现在输入已经换掉的时候。
    """
    raw = str(material.get("raw_path") or "")
    recorded = material.get("content_hash")
    if not raw or not recorded:
        return None
    path = Path(raw)
    if not path.is_file():
        return None
    return mi.file_hash(path) == str(recorded)  # noqa: SLF001 — 同一个所有者（源文件字节哈希）


def locator_health(material: dict[str, Any]) -> dict[str, Any]:
    """**便宜**的锚点健康度：比指纹 + 比源文件字节，不重解析。见模块 docstring。"""
    mid = str(material.get("material_id") or "")
    recorded = material.get("parser_fingerprint")
    recorded_hash = material.get("derived_text_hash")
    out: dict[str, Any] = {
        "material_id": mid,
        "status": "unknown",
        "fingerprint_recorded": recorded,
        "fingerprint_current": None,
        "derived_text_hash_recorded": recorded_hash,
        "source_bytes_match": None,
        "why": "",
    }
    if mr.chunk_count(mid) == 0:
        out["status"] = "no_locators"
        # ⚠ 两种成因要分开说（复核 b9 的 INFO-5）：① 压根没解析出文本（扫描件没开 OCR）；
        # ② 有派生文本但**切块没产出**。旧写法共用一句"没有切片（没有区间可失效）"，
        # 读者分不清该去查解析还是查切块。判据用**入库时记的派生文本哈希**：
        # 有它 ⇒ 当时确实产出过文本；没有 ⇒ 没产出（或入库早于该列，如实带上这一支）。
        out["why"] = (
            "这份材料没有切片（没有区间可失效）：入库时**没有派生文本**"
            "（解析不出文本——扫描件？或入库早于派生哈希那一列）"
            if recorded_hash is None else
            "这份材料没有切片（没有区间可失效）：**有派生文本但切块没产出**"
            "（切分参数或内容形态导致零切片）")
        return out
    if recorded_hash is None or recorded is None:
        out["status"] = "unknown"
        out["why"] = ("入库时没有登记派生文本哈希/解析器指纹"
                      "（2026-09-17 之前的材料）——**不知道**区间还对不对，"
                      "要下结论请走 reverify（重解析比对）")
        return out
    # ---- 输入这一轴：源文件还在不在 / 字节还是不是原来那份（MEDIUM-1）----
    raw = str(material.get("raw_path") or "")
    is_web = (material.get("origin") or "") == "collected" and raw == ""
    if raw and not is_web:
        match = source_bytes_match(material)
        out["source_bytes_match"] = match
        if match is None:
            out["status"] = "unknown"
            out["why"] = (f"源文件不在磁盘上（{raw}）⇒ 取不到当前指纹、也无法复算——"
                          "**不是 ok**；要恢复请把源文件放回原位，或重新入库")
            return out
        if match is False:
            out["status"] = "stale"
            out["why"] = ("**源文件字节已变**（与入库时记的 content_hash 不一致）⇒ "
                          "已存区间是按**旧字节**解析出来的，对新文件不再成立 ⇒ "
                          "**需要复算**（走 reverify 重建区间，或弃用这份材料）")
            return out
    current = current_fingerprint_for(material)
    out["fingerprint_current"] = current
    if current is None:
        out["status"] = "unknown"
        out["why"] = "取不到当前解析器指纹（源文件缺失或后缀不支持）——无法比较"
        return out
    if (material.get("raw_path") or "").lower().endswith(".pdf"):
        # PDF 的完整指纹含只有解析后才知道的 text_layer/ocr ⇒ 这里只能比"结构性前缀"。
        # **不要把"前缀相同"说成 ok**：那正是本模块要防的假保证。
        if current.split(";text_layer=")[0] == str(recorded).split(";text_layer=")[0]:
            out["status"] = "unknown"
            out["why"] = ("PDF 的指纹含只有解析后才有的 text_layer/ocr 两项，"
                          "便宜比对判不了 ⇒ 要结论请走 reverify（重解析比对）")
        else:
            out["status"] = "stale"
            out["why"] = "解析器身份已变（JSON 前缀不同）⇒ 已存区间需要复算"
        return out
    if current == recorded:
        out["status"] = "ok"
        out["why"] = ("解析器身份与入库时一致 ⇒ **未发现变化**"
                      "（这不是'保证一致'：真正的保证是 reverify 的 match）")
    else:
        out["status"] = "stale"
        out["why"] = (f"解析器身份变了：入库时 `{recorded}` → 现在 `{current}` ⇒ "
                      "已存区间**需要复算**（不代表一定坏了）")
    return out


def reverify_material_locators(material_id: str) -> dict[str, Any]:
    """**重解析比对**（贵）：用当前解析器重算派生文本哈希，与入库时记的比。

    返回 `{material_id, status, recorded, recomputed, why}`。
    `mismatch` 的含义很重：**这份材料的已存区间（以及一切基于它的引用）不再可信**。
    """
    mat = mr.get_material(material_id)
    if mat is None:
        raise ValueError(f"材料不存在: {material_id}")
    recorded = mat.get("derived_text_hash")
    out: dict[str, Any] = {"material_id": material_id, "status": "unavailable",
                           "recorded": recorded, "recomputed": None, "why": ""}
    raw = mat.get("raw_path")
    if not raw:
        out["why"] = ("这份材料**没有留存源文件**（网页采集件就是这样）⇒ "
                      "无法重解析复算；指纹不一致时只能按'验不了'处理，**不是 ok**")
        return out
    path = Path(str(raw))
    if not path.is_file():
        out["why"] = f"源文件不在: {path}"
        return out
    if path.suffix.lower() not in mi.SUPPORTED_SUFFIXES:
        out["why"] = f"不支持的材料格式 {path.suffix!r}"
        return out
    pages, _fp = mi.extract_pages_with_provenance(path, deep_fallback=False)
    text, _spans = mi.build_document(pages)
    if not text.strip():
        # ⚠ 顺序很要紧（独立复核 b9 的 MEDIUM-2）：入库时**有**派生文本、而现在重解析
        # **一个字都得不到** ⇒ 这是**确定的失效**（存留文件被截断/换成扫描件/文本层丢了），
        # 不是"验不了"。原先无条件回 `unavailable`，于是这条在界面/报告里**一个标记都没有**
        # （`unavailable` 不是 health 状态 ⇒ attention 与 ⚠ 都不收它）。
        if recorded is not None:
            out["status"] = "mismatch"
            out["why"] = ("入库时**有**派生文本，而重解析**一个字都得不到** ⇒ "
                          "已存区间**必然失效**（不是'验不了'：基准是存在的，对不上）")
            return out
        out["why"] = "重解析没有得到任何文本（扫描件？）⇒ 无法复算"
        return out
    recomputed = mi.text_hash(text)
    out["recomputed"] = recomputed
    if recorded is None:
        out["why"] = ("入库时没有登记派生文本哈希 ⇒ 只能报告**这次**算出来的值，"
                      "没有可比对的基准（不要把它当成'一致'）")
        return out
    if recomputed == recorded:
        out["status"] = "match"
        out["why"] = "重解析得到的派生全文与入库时**逐字节一致** ⇒ 已存区间仍然有效"
    else:
        out["status"] = "mismatch"
        out["why"] = ("重解析得到的派生全文与入库时**不一致** ⇒ "
                      "**已存区间已失效**（引用位置会指错），必须重建或弃用这份材料")
    return out


def project_locator_summary(project_id: str) -> dict[str, Any]:
    """项目级锚点总览（每份材料的状态 + 计数 + 有问题的清单）——给界面/报告用。

    ⚠ 一次给**全部**材料的状态（`statuses`），而不是只给有问题的：界面每行都要画标记，
    而"每行发一次请求"在有几十份材料时就是请求风暴。
    ⚠ **但它不是"零 I/O"**（2026-09-18 复核 b10 的 MEDIUM-2）：这里对**每份材料**调
    `locator_health`，而那个判据会**流式 sha256 一次源文件**（§10.54 加的"源文件字节"轴）
    ⇒ 几十份 PDF 就是一次真实磁盘读。所以调用它的端点**必须声明成 `def`**（线程池），
    不能是 `async def`——判据见
    `tests/test_material_api.py::TestSlowEndpointsAreDeclaredSync`。
    真嫌贵，正确的优化是**缓存源文件 size/mtime**（登记为待办），**不是**删掉那条判据。
    """
    counts: dict[str, int] = {s: 0 for s in HEALTH_STATUSES}
    statuses: dict[str, str] = {}
    attention: list[dict[str, Any]] = []
    for m in mr.list_materials(project_id):
        mid = str(m["material_id"])
        try:
            h = locator_health(m)
        except Exception as exc:  # noqa: BLE001 — 见下：一份材料的判据挂掉不该毁掉整个总览
            # ⚠ 与 `_attach_locator_status` 同族（2026-09-18 复核 b9 的 INFO-3 的**同型**问题，
            # 本步顺带修）：旧写法让异常直接冒出去 ⇒ 整个项目总览 500 / 界面把这次失败
            # **静默吞掉**（面板对总览失败是 `.catch(()=>{})`）⇒ 结果是一份**一个 ⚠ 都没有**的
            # 材料列表，读起来像"全部健康"。**"结论没拿到"必须自己说出来**。
            # `health_error` **不是**健康状态（`locator_health` 永远不会返回它，
            # 它表示"我们的判据跑挂了"），所以单列一个取值、单列一条 attention。
            statuses[mid] = "health_error"
            counts["health_error"] = counts.get("health_error", 0) + 1
            attention.append({"material_id": mid, "title": m.get("title"),
                              "status": "health_error",
                              "why": f"锚点健康度计算失败：{type(exc).__name__}: {exc}"})
            continue
        statuses[mid] = h["status"]
        counts[h["status"]] = counts.get(h["status"], 0) + 1
        if h["status"] in ("stale", "unknown"):
            attention.append({"material_id": mid, "title": m.get("title"),
                              "status": h["status"], "why": h["why"]})
    return {"project_id": project_id, "counts": counts, "statuses": statuses,
            "attention": attention,
            "note": ("`unknown` 包含两类：入库时没记指纹的老材料、以及 PDF 便宜比对判不了的那些；"
                     "`health_error` 不是健康状态，是**判据本身算不出来**（工具问题，不是材料问题）；"
                     "要给结论请对具体材料跑重解析比对")}
