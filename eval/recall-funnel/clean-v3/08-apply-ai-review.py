#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""08-apply-ai-review.py —— 把「AI 复核」的逐条判定落成机器可读产物（T015 的收口件）。

## 这是什么、不是什么

- **是**：业主 2026-10-07 裁定后，`specs/002-recall-funnel/tasks.md` T015 的处置方式
  ——「放弃人工审核，改用外部高级 AI 复核，事实与语言两半分开」—— 的**执行记录**。
- **不是**：人工确认。本仓 `contracts/benchmark.schema.md` 要求 `confirmed_by` **必须是人**；
  这份产物**不满足** FR-004 / SC-003，**不许**被读成"基准已确认"。判定者是一个 AI 模型。

## 输入（`07-build-ai-review.py` 的产物，两者都是 40 条）

- `ai-review-fact.jsonl` —— 事实半：给**问法 + 标准号 + 条文原文**，判
  「这条条文是不是该问法的正确答案」（对 / 错 / 多个都对 / 说不清）+「问法有没有泄漏答案」（有 / 无 / 说不清）。
- `ai-review-lang.jsonl` —— 语言半：**只给问法**，判「像不像真外行说的话」
  （自然度 像真人 / 像机器 / 说不清、对象锚点 有 / 无）+「是不是硬凑」（是 / 否 / 说不清）。

## 输出

- `ai-review-verdicts.jsonl` —— 每条一行，事实半与语言半合并，带 `reviewer` 身份字段。
- `ai-review-summary.json`   —— 汇总计数 + 被点名的条目清单 + 对基准可信度的结论。

## 判据（防自己放水）

1. `VERDICTS` 必须**覆盖全部 40 个 id**，少一个即 `SystemExit`（不许静默漏判）。
2. 判定取值必须在允许集合里，否则 `SystemExit`（防手滑写出「差不多」这种词）。
3. 事实半**不采信** `system_suspicion` 当结论（它只是机械提示）；但提示里说"另有 N 篇定义同一术语"
   时，按"gold 可能不唯一"如实判 `多个都对`，理由里写明这是**机械提示、未逐条核**。
4. 语言半**只看问法**（不给条文）—— 判定表里也不含条文，防止"像不像抄条文"混淆成"像不像人话"。
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
FACT = HERE / "ai-review-fact.jsonl"
LANG = HERE / "ai-review-lang.jsonl"
OUT_VERDICTS = HERE / "ai-review-verdicts.jsonl"
OUT_SUMMARY = HERE / "ai-review-summary.json"

REVIEWER = {
    "kind": "AI",
    "is_human": False,
    "model": "deepseek-v4.1-flash",
    "note": (
        "由本仓自动续接链的 AI 代理逐条判定（业主 2026-10-07 裁定的「外部高级 AI 复核」）；"
        "**不是人工**，不满足 contracts/benchmark.schema.md 的 confirmed_by=人。"
    ),
    "reviewed_at": "2026-10-09",
}

FACT_OK = {"对", "错", "多个都对", "说不清"}
LEAK_OK = {"有", "无", "说不清"}
NAT_OK = {"像真人", "像机器", "说不清"}
ANCHOR_OK = {"有", "无"}
FORCED_OK = {"是", "否", "说不清"}

# id -> (事实判定, 泄漏, 理由)
VERDICTS_FACT: dict[str, tuple[str, str, str]] = {
    "s1": ("对", "无", "条文即「微生物采样器」的定义，与问法描述的小圆盒子一一对应。"),
    "s2": ("对", "无", "「重要旅客行李牌」就是拴挂/粘贴在重要旅客行李上的识别标识牌；问法问的正是这个。"),
    "s3": ("多个都对", "无", "条文与问法吻合；⚠ 机械提示另有 5 篇文档定义同一术语「高压系统」⇒ gold 可能不唯一（提示未逐条核）。"),
    "s4": ("对", "无", "「放水试验」的定义与问法（利用天然静水压力自行泄水）一致。"),
    "s5": ("对", "无", "「容性运行」= 不交换有功功率的情况下发出无功功率，与问法吻合。"),
    "s6": ("对", "无", "「生物燃料」含乙醇与石油的调和混合物 ⇒ 覆盖问法的 E10 汽油。"),
    "s7": ("对", "无", "「自动化焊接」定义与问法（启动后自动完成、无需监视）一致。"),
    "s8": ("对", "无", "「疏干排水」注中明写用于矿产开采，与问法一致。"),
    "s9": ("对", "无", "CEC 即「阳离子交换吸附容量」，条文为其定义；条文里没有出现「CEC」字样，不构成泄漏。"),
    "s10": ("对", "无", "「分子筛吸附器」明写用于净除空气中的水分与 CO₂，与问法一致。"),
    "s11": ("对", "无", "「分室定位回转反吹」与问法（轮流给分隔袋室定位吹风）一致。"),
    "s12": ("对", "无", "「定量阀体」= 装在固定盖里支承其他元件并确定定量值的元件，与问法一致。"),
    "s13": ("对", "无", "「截割机构」= 采掘机械上直接实现截割功能的构件组成，与问法一致。"),
    "s14": ("对", "无", "「应力控制式无侧限压缩仪」= 以恒荷重速率加荷，与问法一致。"),
    "s15": ("对", "无", "「托盘转户」= 承租使用权从一方转移到另一方，与问法一致。"),
    "s16": ("对", "无", "「微型瓦楞」定义与问法（波纹特别细的纸板）一致。"),
    "s17": ("对", "无", "「多周波控制」= 改变导电与不导电周波数之比，与问法一致。"),
    "s18": ("对", "有", "答案正确；但**问法里直接写出了术语「足背发」**（条文标题就是它）⇒ 关键词能直接搜到，构成泄漏。"),
    "s19": ("对", "有", "答案正确；问法用了条文里的词「压头」⇒ 弱泄漏（未写出被定义的「预压力」）。"),
    "s20": ("对", "无", "「热链盒饭」= 加温/保温环境配送、无需加热即可直接食用，与问法一致。"),
    "s21": ("对", "无", "「服务绩效模型」= 对各属性加权分析的评价方法，与问法一致。"),
    "s22": ("对", "无", "条文把「通风机」定义为输送空气的动力机械；抽油烟用的排风机属其下位，判对（定义较宽）。"),
    "s23": ("对", "无", "「土壤板结」定义与问法（硬得像石头、浇不进水）一致。"),
    "s24": ("多个都对", "无", "条文与问法吻合；⚠ 机械提示另有 2 篇文档定义同一术语「脱硫效率」⇒ gold 可能不唯一（提示未逐条核）。"),
    "s25": ("对", "无", "「油水分离设备」= 船上处理机舱污水的装置，与问法一致。"),
    "s26": ("对", "无", "「手足皲裂」定义与问法（干硬粗糙、裂缝渗血）一致。"),
    "s27": ("对", "无", "条文虽是分节标题，但**带实质定义**（泛指脾及其络属脏腑功能障碍的一类疾病）；问法问的正是该大类 ⇒ 判对。⚠ 机械提示说「外行可能问的是子条款」，本判定未排除该风险。"),
    "s28": ("对", "无", "条文虽是分节标题，但**带实质定义**（为增强可识别性而粘贴的反光材料）；问法问的正是它 ⇒ 判对。"),
    "s29": ("对", "无", "「初始显影电压」= 墨粉开始附着到光导体上时的电压，与问法一致。"),
    "s30": ("对", "无", "「提示标志」= 提示安全行为或指示安全设备/设施/疏散路线位置的标志，与问法一致。"),
    "s31": ("对", "无", "「岩溶泉域」= 有共同补给边界、统一地下径流场的流域范围，与问法一致。"),
    "s32": ("多个都对", "无", "条文与问法吻合；⚠ 机械提示另有 5 篇文档定义同一术语「测量时间」⇒ gold 可能不唯一（提示未逐条核）。"),
    "s33": ("对", "无", "条文给出判据（实验室间差值应不大于表 G.1 的允许差），问法问的正是「算不算违规」⇒ 该条即答案所在（具体阈值在表里）。"),
    "s34": ("对", "无", "条文限值 2 mm，问法给 3 mm ⇒ 该条正是判定依据。"),
    "s35": ("多个都对", "无", "条文与问法吻合；⚠ 机械提示**该段条文在 13 篇文档里字节级重复**⇒ gold 明确不唯一。"),
    "s36": ("对", "无", "条文（除非采购方在协议中放弃，否则应做生产验证载荷试验）与问法一致。"),
    "s37": ("对", "无", "条文要求呼吸软管在任何扭曲状况下不影响连接与性能，与问法一致。"),
    "s38": ("对", "无", "条文要求卷筒公称直径与钢丝绳直径比值符合 GB/T 3811，与问法一致。"),
    "s39": ("对", "无", "答案（20 个工作日核实）确在该条正文。⚠ 条文正文头部**夹带解析残留**（「标题：」「索引号：」「发」），但正文本身非空壳，仍判对。"),
    "s40": ("对", "无", "「安全检查的程序」含初检/复检，问法问的正是复检环节 ⇒ 该条即答案所在。"),
}

# id -> (自然度, 对象锚点, 硬凑, 理由)
VERDICTS_LANG: dict[str, tuple[str, str, str, str]] = {
    "s1": ("像真人", "有", "否", "「呼呼吸空气测细菌的小圆盒子」是典型的外行描述，锚点清楚。"),
    "s2": ("像真人", "有", "否", "口语自然，对象（拉杆箱/贵宾）明确。"),
    "s3": ("像真人", "有", "否", "「行业里一般管它叫啥」是真实提问语气。"),
    "s4": ("像真人", "有", "否", "描述性提问，自然。"),
    "s5": ("像真人", "有", "是", "「没输送实际电量却在补偿电压」不是真人的说法（条文原词是「不交换有功功率」「发出无功功率」）⇒ 像照着条文绕着写。"),
    "s6": ("像真人", "有", "否", "「标着E10含一成酒精的汽油」自然。"),
    "s7": ("像真人", "有", "否", "「按一下绿钮机子自己焊完」自然。"),
    "s8": ("像真人", "有", "否", "自然。"),
    "s9": ("像真人", "有", "否", "「泥巴有多肥」是外行说法，自然。"),
    "s10": ("像真人", "有", "否", "自然。"),
    "s11": ("像真人", "有", "否", "自然（但用了行业词「布袋除尘器」）。"),
    "s12": ("像真人", "有", "否", "自然。"),
    "s13": ("像真人", "有", "是", "「破岩旋转总成」是生造复合词（条文原词是「截割机构」）⇒ 像为了避开原词硬凑。"),
    "s14": ("像真人", "有", "否", "自然。"),
    "s15": ("像真人", "有", "否", "自然。"),
    "s16": ("像真人", "有", "否", "自然。"),
    "s17": ("像真人", "有", "否", "自然。"),
    "s18": ("像真人", "有", "否", "自然（但事实半判它泄漏了术语）。"),
    "s19": ("像真人", "有", "否", "自然（但用了条文词「压头」）。"),
    "s20": ("像真人", "有", "否", "自然。"),
    "s21": ("像真人", "有", "否", "自然。"),
    "s22": ("像真人", "有", "否", "自然。"),
    "s23": ("像真人", "有", "否", "自然。"),
    "s24": ("像真人", "有", "否", "自然。"),
    "s25": ("像真人", "有", "否", "自然。"),
    "s26": ("像真人", "有", "否", "自然。"),
    "s27": ("像机器", "有", "是", "「中医讲的**这个**脏腑问题」的「这个」没有先行语 ⇒ 像从分节标题反推出来的问法。"),
    "s28": ("像真人", "有", "否", "自然（「发亮的发光贴纸」略重复，但仍像口语）。"),
    "s29": ("像真人", "有", "否", "自然。"),
    "s30": ("像真人", "有", "否", "自然。"),
    "s31": ("像真人", "有", "否", "自然。"),
    "s32": ("像真人", "有", "否", "自然。"),
    "s33": ("像真人", "有", "否", "自然。"),
    "s34": ("像真人", "有", "否", "自然。"),
    "s35": ("像真人", "有", "否", "自然。"),
    "s36": ("像真人", "有", "否", "自然。"),
    "s37": ("像真人", "有", "否", "自然。"),
    "s38": ("像真人", "有", "否", "自然。"),
    "s39": ("像真人", "有", "否", "自然。"),
    "s40": ("像真人", "有", "否", "自然。"),
}


def _load(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    facts = _load(FACT)
    langs = _load(LANG)
    fact_ids = [r["id"] for r in facts]
    lang_ids = [r["id"] for r in langs]

    # 判据 1：id 集合必须完全一致、且判定表覆盖全部
    if fact_ids != lang_ids:
        raise SystemExit(f"两半的 id 序列不一致：{fact_ids} vs {lang_ids}")
    missing_f = [i for i in fact_ids if i not in VERDICTS_FACT]
    missing_l = [i for i in lang_ids if i not in VERDICTS_LANG]
    if missing_f or missing_l:
        raise SystemExit(f"判定表没覆盖全：fact 缺 {missing_f}，lang 缺 {missing_l}")

    lang_by_id = {r["id"]: r for r in langs}
    records = []
    for r in facts:
        i = r["id"]
        fv, leak, freason = VERDICTS_FACT[i]
        nat, anchor, forced, lreason = VERDICTS_LANG[i]
        # 判据 2：取值必须在允许集合里
        for val, allowed, what in ((fv, FACT_OK, "事实判定"), (leak, LEAK_OK, "泄漏"),
                                   (nat, NAT_OK, "自然度"), (anchor, ANCHOR_OK, "对象锚点"),
                                   (forced, FORCED_OK, "硬凑")):
            if val not in allowed:
                raise SystemExit(f"{i} 的{what}取值非法：{val!r}（允许 {sorted(allowed)}）")
        # 判据 4：语言半只给问法 —— 这里断言两条问法逐字相同，防"语言半偷偷看了条文/改过问法"
        if lang_by_id[i]["query"] != r["query"]:
            raise SystemExit(f"{i} 两半的问法不一致")
        records.append({
            "id": i,
            "query": r["query"],
            "gold_std": r["gold_std"],
            "gold_clause": r["gold_clause"],
            "system_suspicion": r["system_suspicion"],
            "fact": {"verdict": fv, "leak": leak, "reason": freason},
            "lang": {"naturalness": nat, "anchor": anchor, "forced": forced, "reason": lreason},
            "reviewer": REVIEWER,
        })

    OUT_VERDICTS.write_text(
        "\n".join(json.dumps(rec, ensure_ascii=False) for rec in records) + "\n", encoding="utf-8")

    def counts(key, sub):
        out: dict[str, int] = {}
        for rec in records:
            out[rec[key][sub]] = out.get(rec[key][sub], 0) + 1
        return out

    fact_counts = counts("fact", "verdict")
    leak_counts = counts("fact", "leak")
    nat_counts = counts("lang", "naturalness")
    anchor_counts = counts("lang", "anchor")
    forced_counts = counts("lang", "forced")

    summary = {
        "n_items": len(records),
        "reviewer": REVIEWER,
        "fact": {
            "counts": fact_counts,
            "leak_counts": leak_counts,
            "not_correct_ids": [r["id"] for r in records if r["fact"]["verdict"] == "错"],
            "ambiguous_ids": [r["id"] for r in records if r["fact"]["verdict"] == "多个都对"],
            "unclear_ids": [r["id"] for r in records if r["fact"]["verdict"] == "说不清"],
            "leaked_ids": [r["id"] for r in records if r["fact"]["leak"] == "有"],
            "note": "「多个都对」= 该题 gold 不唯一（库里另有同样贴切的条款）；判定只采信条文本身，机械提示仅作线索。",
        },
        "lang": {
            "naturalness_counts": nat_counts,
            "anchor_counts": anchor_counts,
            "forced_counts": forced_counts,
            "machine_like_ids": [r["id"] for r in records if r["lang"]["naturalness"] == "像机器"],
            "forced_ids": [r["id"] for r in records if r["lang"]["forced"] == "是"],
            "no_anchor_ids": [r["id"] for r in records if r["lang"]["anchor"] == "无"],
            "note": "语言半只看问法（不给条文），判的是「像不像真外行说的话」，不是「像不像抄条文」。",
        },
        "does_it_satisfy_FR004": False,
        "satisfies_FR004_reason": (
            "不满足。FR-004 / SC-003 与 contracts/benchmark.schema.md 要求每条的答案经**人工确认**；"
            "本次是 AI 判定（业主 2026-10-07 裁定的规格例外），confirmed_by 仍是空。"
            "⇒ 引用 REPORT.md 的百分比时必须继续带「基准未经人工确认」这条限制。"
        ),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"已写 {OUT_VERDICTS.name}（{len(records)} 条）与 {OUT_SUMMARY.name}")
    print("事实判定：", fact_counts)
    print("泄漏：", leak_counts)
    print("自然度：", nat_counts, "｜对象锚点：", anchor_counts, "｜硬凑：", forced_counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
