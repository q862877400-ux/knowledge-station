# 模态核验残留误报：根因与修复方案（2026-10-19 真机实测）

> 范围：`src/core/verification/typed_verifier.py` 的 rule 型模态核验，以及它依赖的
> `src/core/knowledge/classifier.py::extract_modality` 与 `src/core/domain/models.py::MODALITY_STRENGTH`。
> 本报告**只读**，未改任何代码。复现脚本全部落在 `var/tmp/`（不进仓）。

## 一句话结论

**残留误报不是「`[[c:i]]` 没解析」，而是「窗口从引用标记处向后取」——中文引用标记后置在句尾，向后取恰好跳过本条款自己那句话，取到的是下一句的模态词；再叠加「同一 `clause_number` 对应多条 evidence 时窗口逐字共用」和「模型未引用的证据回退整篇」两个放大器。**

## 五条要点

1. **「不应」被定得比「应」高，但这不是方向写反**：`MODALITY_STRENGTH` 里 `'应': 3`、`'不应': 4`。按表算 `应 -> 不应` 就是 `strengthened`。**那 4 条是误报**，但错因不在强度表，而在窗口把**别的条款**的「不应」算到了本条头上。强度表把「肯定义务」和「否定义务」放在同一个标量轴上比大小，本身还有一层语义问题（见 §4）。
2. **主因是窗口方向**：`_clause_mention_window` 用 `text[pos:pos + 240]`（标记处**向后** 240 字），而 `FORENSIC_SYSTEM_PROMPT` 规则 1 要求的写法是「每条结论后紧跟引用标记」⇒ 标记在句尾。实测同一句话，把「可按」那句放到文本末尾 vs 后面再接一句，窗口内容完全不同（`'[[c:0]]。'` vs 一段含「应」的后文）。
3. **同 `clause_number` 多条 evidence 会串**：GB 30871-2014 和 GB 30871-2022 都有 `5.1.1` / `5.1.4`。`wanted` 把同号 evidence 的下标**全部**收下，两条 evidence 拿到**逐字相同**的窗口（实测 62 字 / 467 字两处都逐字相同）。
4. **`extract_modality` 取的不是「第一个」**：docstring 写「抽取首个有效模态词」，实现是按**词长降序**扫 `MODALITY_STRENGTH.keys()`。实测「应 … 不应」取到 `不应`、「可 … 应」取到 `应`、「严禁 … 原则上」取到 `原则上`(2)。取词与文中顺序无关，与强度也无关。
5. **现有 3 条判据不够**：第 1 条只断言 `not strengthened`，不断言 `is_valid`；而且它的输出里「可按」那句恰好在**文本末尾**，窗口只剩 `'[[c:0]]。'`。实测同一份输入 `is_valid=False`（有 `modality_missing` 与 `modality_weakened`），判据照样绿。

---

# 第一部分：我们的证据（复现与根因）

## 1.1 强度表原文

`src/core/domain/models.py`，可搜索片段：

```python
# v4.3 模态强度字典 (R4a) —— 权威常量，变更需走契约变更流程
MODALITY_STRENGTH: dict[str, int] = {
    '严禁': 5, '禁止': 5,
    '不得': 4, '不应': 4, '不能': 4,
    '应当': 3, '应': 3, '必须': 3,
    '宜': 2, '一般应': 2, '原则上': 2,
    '可以': 1, '有权': 1, '可': 1,
    '鼓励': 0, '提倡': 0, '支持': 0,
}
```

**回答业主最关心的那一条**：`不应` = **4**，`应` = **3**。「不应」确实被定得比「应」高。

比较规则在 `src/core/verification/typed_verifier.py`：

```python
                    out_strength = MODALITY_STRENGTH.get(out_mod, -1)
                    if out_strength < src_strength:
                        vtype: Optional[Literal[
                            'modality_weakened', 'modality_strengthened']] = "modality_weakened"
                    elif out_strength > src_strength:
                        vtype = "modality_strengthened"
```

⇒ `源=应(3) → 输出=不应(4)` 落进 `out_strength > src_strength` 分支 ⇒ 报 `modality_strengthened`。**这是按表算出来的，不是代码写反。**

设计意图写在 `docs/REQUIREMENTS-v4.3.md`，可搜索片段：

```
     | 5（最强禁止） | 严禁、禁止 | 行为无效，可能违法 |
     | 4（强禁止） | 不得、不应、不能 | 行为无效 |
     | 3（强义务） | 应当、应、必须 | 不履行=违法 |
```

即：需求文档明确把「不应」定为**比「应」更强的禁止**。所以这一组是**误报**，但强度表本身「没写反」——它是有意这样定的。

## 1.2 复现：那两题的窗口里到底有什么

脚本：`var/tmp/modality-repro.py`（只读，直接调 `verify_llm_output`）。

**证据集来源的诚实交代（未确认项）**：真机落盘的 `debug_dump` 里只有一条含「动火」的记录
（`dump_01M59TWD984RT2C2D3DS7KW7JH`，2026-10-19 10:21:28），但那次的 `llm_output` 是
`大模型不可用（DeepSeek 取证调用失败: Connection error.）` 的降级占位，**不是**报出这 2 条违规的那次运行。
所以证据集是我**按 `var/tmp/after_fix.json` 里 derivation 的 `[[c:i]]` 逐句比对库内原文重建**的
（`clause_revision` 表，只读连接 `mode=ro`）。**重建结果与真机吻合到条数、方向、`clause_revision_id` 三级**
（两题的 `clause_revision_id` 与真机报的完全一致），但**证据排列顺序是推的，标为未确认**。

### 题一「动火作业怎么分级」——复现出 2 条，与真机逐字段一致

```
=> is_valid=False  模态违规 2 条
  modality_strengthened: 可(1) -> 应(3)
  被核验条款: GB 30871-2022 5.1.4  rev=clrev_01M2FY0CR1FYD8T1FS9YM2TG3F
  同条款号 evidence 下标（会被一起当成"本条款的提及"）: [5, 6]
    → 标准号: ['GB 30871-2022', 'GB 30871-2014']
  字面提及位置=[]  [[c:i]]提及位置=[196, 294, 677, 705, 766, 1044]
  窗口长度=1213  取到模态词='应'
  modality_weakened: 不应(4) -> 应(3)
  被核验条款: GB 30871-2014 5.3  rev=clrev_01M4A5P7NNSZZJ5G52S0KPBR44
  同条款号 evidence 下标: [7]  → 标准号: ['GB 30871-2014']
  字面提及位置=[]  [[c:i]]提及位置=[]
  窗口长度=0  取到模态词=None
  ⚠ 窗口为空 ⇒ 回退整篇；extract_modality(整篇) = '应'
```

窗口原文（题一第 1 条，节选开头）——**注意窗口是从 `[[c:5]]` 这个标记之后开始的，本句被排除**：

```
    [[c:5]]；
    生产装置或系统全部停车，……动火作业可按二级动火作业管理 [[c:5]]。
    依据 GB 30871-2014：
    固定动火区外的动火作业一般分为二级动火、一级动火、特殊动火三个级别 [[c:2]]；
    遇节日、假日或其他特殊情况，动火作业应升级管理 [[c:2]]；
    注：企业应划定固定动火区及禁火区 [[c:2]]。
```

⇒ 本条款的「可按」**不在窗口里**，窗口里第一个模态词是后面 2014 版 5.1.1 的「应」。
**这就是「可 -> 应」那条误报的全部成因。**

题一第 2 条（`不应 -> 应`）：模型**从头到尾没引用过** GB 30871-2014 §5.3，
所以 `wanted=[7]` 有值但输出里没有任何 `[[c:7]]`，字面也没出现 `5.3` ⇒ 窗口空 ⇒ 回退整篇 ⇒
`extract_modality(整篇)` 取到全文第一个有效模态词「应」⇒ 判 `不应 -> 应` weakened。
**这是「模型没引某条证据，却仍被拿整篇去核验」的形态。**

### 题二「特殊动火作业有什么要求」——复现出 4 条，`is_valid=True`

```
=> is_valid=True  模态违规 4 条
  modality_strengthened: 可(1) -> 不应(4)   GB 30871-2022 5.1.4  窗口 481 字  取到 '不应'
  modality_strengthened: 应(3) -> 不应(4)   GB 30871-2022 5.1.1  窗口 467 字  取到 '不应'
  modality_strengthened: 应(3) -> 不应(4)   GB 30871-2014 5.1.1  窗口 467 字  取到 '不应'
  modality_strengthened: 可(1) -> 不应(4)   GB 30871-2014 5.1.2  窗口 0 字 → 回退整篇  取到 '不应'
```

后两条的窗口**逐字相同**（467 字，`同条款号 evidence 下标: [3, 4]`），
因为 2022 和 2014 都有 `5.1.1`，`wanted` 把 3 和 4 都收下，两条 evidence 共用同一批提及位置。

**判断：这 4 条全是误报。** 模型原文是对的——a) 项写「不应」，b)~e) 项写「应」，
`conclusion` 里写「生产不稳定时不应进行带压不置换动火作业，并应在正压条件下作业」。
误报来源是窗口把 **§5.3 a) 项的「不应」** 算到了 `5.1.1` / `5.1.4` / `5.1.2` 头上。

## 1.3 主因定位：窗口方向错了（标记后置 vs 向后取窗）

`src/core/verification/typed_verifier.py`，可搜索片段：

```python
    parts = []
    seen = set()
    for pos in sorted(set(starts)):
        win = text[pos:pos + 240]
```

`pos` 是**标记的起始位置**。取证输出里标记在句尾（`FORENSIC_SYSTEM_PROMPT` 规则 1：
「每条结论后紧跟引用标记」；规则 7：「derivation 内在引用证据处用 [[c:i]] 标记」）。
⇒ 窗口起点 = 句尾 ⇒ 本句被整体排除。

探针 `var/tmp/modality-probe-direction.py` 实测：

```
输出原文：
  生产装置或系统全部停车……经危险化学品企业生产负责人批准，动火作业可按二级动火作业管理 [[c:5]]。
  遇节假日、公休日、夜间或其他特殊情况，动火作业应升级管理。

窗口（从标记处向后 240 字）= '[[c:5]]。\n遇节假日、公休日、夜间或其他特殊情况，动火作业应升级管理。\n'
extract_modality(窗口) = '应'

本条款那句话（含模态词「可按」）= '生产装置或系统全部停车……动火作业可按二级动火作业管理 [[c:5]]'
标记位置=44，窗口起点=44（== 标记本身）
⇒ 窗口起点在标记处，而标记在句尾 ⇒ 本句被整体排除在窗口之外。

若改成「标记前 240 字 + 标记后 60 字」：
  前向窗口 = '生产装置或系统全部停车……动火作业可按二级动火作业管理 [[c:5]]'
  extract_modality = '可'  ← 这才是本条款的模态词
```

**这条探针是整个报告里最硬的一条证据**：同一份输出、同一份证据、同一份实现，
只要窗口改成向前取，误报当场消失、且取到正确的「可」。

## 1.4 放大器一：同一 `clause_number` 对应多条 evidence

`src/core/verification/typed_verifier.py`，可搜索片段：

```python
    # 形态 B：[[c:i]] / [[m:i]] 序号标记
    if evidence_clauses:
        # 该条款在本轮证据里的下标（同一条款可能被检索到多次，全部收下）
        wanted = [i for i, c in enumerate(evidence_clauses)
                  if str(c.get("clause_number") or "") == str(clause_number)]
```

`wanted` 只按 `clause_number` 比对，**不看 `standard_no`**。GB 30871-2014 与 GB 30871-2022
都有 `5.1.1` / `5.1.2` / `5.1.3` / `5.1.4`（库里实测，见 `var/tmp/modality-probe-clauses.py` 输出）。
⇒ 两部标准的同名条款互相污染。

探针 `var/tmp/modality-probe-forms.py` 实测：

```
A. 同 clause_number 多条 evidence —— 窗口被另一部标准的同名条款污染
  核验 c:0 (GB 30871-2022 5.1.4): 窗口长度=62
    窗口='[[c:0]]。带压不置换动火作业按特殊动火作业管理，特殊动火作业应符合 5.3 的规定 [[c:1]]。\n[[c:1]]。'
  核验 c:1 (GB 30871-2014 5.1.4): 窗口长度=62
    窗口='[[c:0]]。带压不置换动火作业按特殊动火作业管理，特殊动火作业应符合 5.3 的规定 [[c:1]]。\n[[c:1]]。'
  ⇒ 两条 evidence 的窗口**逐字相同**
```

## 1.5 放大器二：模型未引用的证据，窗口空 ⇒ 回退整篇

调用处 `src/core/verification/typed_verifier.py`，可搜索片段：

```python
        window = _clause_mention_window(llm_output, c["clause_number"],
                                        evidence_clauses) or llm_output
```

`or llm_output` 这个兜底本来是「修好 `[[c:i]]` 之前」的权宜；修好之后它**还在**，
而且正好覆盖了「模型压根没引这条证据」这种最常见的情形。

探针 `var/tmp/modality-probe-forms.py` 实测：

```
D. 模型未引用的证据 ⇒ 回退整篇
  输出只引用了 c:0，完全没提 5.3
  modality_missing: 应 ->  (rev-cited)
  modality_weakened: 不应 -> 应 (rev-uncited)
  is_valid=False
```

题一那条 `不应 -> 应` 就是这个形态。

## 1.6 取词规则：不是「第一个」，是「词长降序」

`src/core/knowledge/classifier.py`，可搜索片段：

```python
def extract_modality(text: str) -> tuple[Modality | None, float]:
    """抽取首个有效模态词（跳过复合词误命中）。返回 (词, 置信度)。"""
    for word in sorted(MODALITY_STRENGTH.keys(), key=len, reverse=True):
```

**docstring 与实现不一致**：注释说「首个」，代码按**词长降序**遍历词表。

探针 `var/tmp/modality-probe-extract.py` 实测：

```
---- 候选顺序（就是 extract_modality 的扫描顺序）----
  '一般应' len=3 strength=2
  '原则上' len=3 strength=2
  '严禁' len=2 strength=5
  ...
  '应' len=1 strength=3
  '宜' len=1 strength=2
  '可' len=1 strength=1
  ↑ 扫描顺序 = 词长降序（同长按字典字面顺序），**不是**在文中出现的先后

---- 同一段里两个模态词的取词结果 ----
  应 ... 不应（应在前）          -> 取到 '不应'(4)   文中最先出现 '应'   ⚠ 与「首个」不一致
  可 ... 应                -> 取到 '应'(3)   文中最先出现 '可'   ⚠ 与「首个」不一致
  严禁 ... 原则上             -> 取到 '原则上'(2)   文中最先出现 '严禁'   ⚠ 与「首个」不一致
  宜 ... 应                -> 取到 '应'(3)   文中最先出现 '宜'   ⚠ 与「首个」不一致
```

⇒ 一个窗口里同时有多个模态词时，取到的是**词表里最长的那个**（同长取字典序最前的）。
题二那 4 条全取到「不应」，就是因为「不应」是 2 字词、排在「应」（1 字）前面。

## 1.7 另外两处小串（都在探针里复现了）

**`[[m:i]]` 被当成 `[[c:i]]`**——`src/core/verification/typed_verifier.py`，可搜索片段：

```python
_CITE_MARK = re.compile(r"\[\[(?:c|m):(\d+)\]\]")
```

`ks_answer.py` 里这两个标记是**刻意分开**的，可搜索片段：

```python
# 参考资料的引用标记：[[m:i]] 指参考资料第 i 条（编号由 materials.authority 分配）。
# ⚠ 与 [[c:i]] **必须是不同的标记**：法条证据与材料是**两个平面**，混用会让
# `parse_llm_answer` 的越界校验把材料序号当成法条序号（或反之）。
_MATERIAL_MARK = re.compile(r'\[\[m:' + _MARK_NUM + r'\]\]')
```

`typed_verifier` 这边把两个平面合成了一个正则 ⇒ 材料序号会锚定到 `evidence[i]`。
实测（`var/tmp/modality-probe-forms.py`）：

```
B. [[m:i]] 被当成 [[c:i]]
  _CITE_MARK.pattern = '\\[\\[(?:c|m):(\\d+)\\]\\]'
  输出里没有 [[c:0]]，只有参考资料标记 [[m:0]]
  核验 5.1.1 取到的窗口长度=18  窗口='[[m:0]]。法律层面应升级管理。'
  ⇒ 窗口被 [[m:0]] 错误锚定（串了）
```

**字面条款号子串匹配**——`for m in re.finditer(re.escape(clause_number), text)` 没有词边界。
实测：核验 `5.2` 时找到的位置=`[3, 23]`，其中位置 3 是 `5.2.1` 的开头 ⇒
核验 `5.2` 时把 `5.2.1` 的出现也当成本条款的提及。

## 1.8 源侧问题：一条只存一个 `modality`

`src/core/knowledge/classifier.py`，可搜索片段：

```python
    modality, mod_conf = extract_modality(text)
```

`classify_clause` 对**整条** `content_text` 调一次，结果写进 `clause_revision.modality`（单值列）。
GB 30871-2014 §5.3 有 a)~e) 五个子项（1 个「不应」+ 4 个「应」）。库里实测
（`var/tmp/modality-probe-source.py`）：

```
extract_modality(整条) = '不应'  strength=4 conf=0.92
库里存的 modality = ('不应', 4)

---- 逐子项各自该是什么 ----
  '应'      ← 特殊动火作业在符合5.2规定的同时，还应符合以下规定：
  '不应'     ← a）在生产不稳定的情况下不应进行带压不置换动火作业；
  '应'      ← b) 应预先制定作业方案，落实安全防火措施，必要时可请专职消防队到现场监护；
  '应'      ← c) 动火点所在的生产车间(分厂)应预先通知工厂生产调度部门及有关单位;
  '应'      ← d) 应在正压条件下进行作业；
  '应'      ← e) 应保持作业现场通排风良好。
```

**后果：正确输出被拦。** 探针 `var/tmp/modality-probe-srcmodel.py` 实测：

```
模型正确复述 b) 子项（原文就是「应」）
  is_valid = False
    modality_weakened: 源 不应(4) -> 输出 '应'(3)

模型正确复述 a) 子项（原文是「不应」）
  is_valid = True
    （无违规）
```

⇒ 模型照抄 b) 项的「应」，因为源侧只存了「不应」，被判**减弱并拦截**。
这是与窗口取词**无关**的第二类误报，必须单独记账。

## 1.9 现有 3 条判据为什么全绿却没抓住

`tests/test_modality_window_false_positive.py` 第 1 条，可搜索片段：

```python
    r = verify_llm_output(out, EV_KEKE)
    strengthened = [v for v in r.modality_violations
                    if v.violation_type == "modality_strengthened"]
    assert not strengthened, (
```

**它只断言「没有 strengthened」，不断言 `is_valid`。** 而且它的 `out` 里「可按」那句恰好在
**文本最后**（后面没有别的句子）⇒ 窗口只剩 `'[[c:0]]。'`。

探针 `var/tmp/modality-probe-testgreen.py`（用测试文件的**原样**输入）实测：

```
---- 测试文件原样输入 ----
  GB 30871-2014 5.1.2 (modality='可') 窗口='[[c:0]]。'
  GB 30871-2014 5.1.1 (modality='应') 窗口='[[c:1]]。凡生产装置或系统全部停车，……动火作业可按二级动火作业管理 [[c:0]]。'
  is_valid = False
    modality_missing: 可 -> ''
    modality_weakened: 应 -> '可'

  ⇒ 判据 1 断言的是 `not strengthened`，而这里是 modality_missing + modality_weakened，
    所以判据 1 **绿**；但这份答案实际被核验器判成**不通过**（is_valid=False）。
```

⇒ **这 3 条判据是靠「标记在文本末尾」这个侥幸条件通过的**，它证明的是
「`[[c:i]]` 能被解析到」，不是「窗口取对了」。

---

# 第二部分：业界做法（外部资料，**不是**我们的证据）

> 以下全部是「业界/标准文本怎么做」，用来判断我们的强度序和归因方式是否站得住。
> 它们**不构成**对本仓任何行为的证据。

## 2.1 中文标准的能愿动词分级：应/不应**同档**，只有肯定否定之别

GB/T 1.1—2020 的能愿动词表（第三方转载的表格，原表在 GB/T 1.1—2020 附录 C）：

| 条款类型 | 能愿动词 | 等效表述 |
| --- | --- | --- |
| 要求 | **应** / **不应** | 应该、只准许 / 不应该、不准许 |
| 推荐 | 宜 / 不宜 | 推荐、建议 / 不推荐、不建议 |
| 允许 | 可 / 不必 | 可以、允许 / 可以不、无须 |
| 陈述 | 能 / 不能、可能 / 不可能 | 能够 / 不能够、有可能 / 没有可能 |

- <https://hbba.sacinfo.org.cn/portal/download/9b76d2a3ebae9e3b295573bbb7123fad8b043648c4810381d1269fb9b5b2055f>
- <http://tc578.org.cn/upload/portal/20210331/86cb3b4c32b8583daf6d4c6e7700f372.pdf>
- <http://in.iphy.ac.cn/upload/s41/a/03393_20240830132169776.pdf>（中国标准出版社审校手册，含「能愿动词不准确」计错条目）

**关键一条**：标准把「应」和「不应」放在**同一行、同一档**（都是「要求」），
只有**肯定/否定**之别，**没有强弱之别**。我们把它拆成 3 和 4 两个强度，是为了让
「应→不应」这种翻转能被察觉，代价是「方向」这个词失去意义（翻转不是加强也不是减弱）。

## 2.2 道义逻辑：禁止不是「更强的义务」，是「对否定的义务」

标准道义逻辑（SDL）的三个算子：

- `O p`（义务）、`P p`（许可）、`F p`（禁止）
- `F p ⇔ O ¬p`（禁止 p = 有义务不做 p）
- `P p ⇔ ¬O ¬p`（许可 p = 不禁止 p）

- <http://fitelson.org/piksi/piksi_18/cariani_notes.pdf>（含三算子互相定义的等价表）

**对我们的直接含义**：`应` 与 `不应` 是**极性相反**的两个算子，不是同一标量轴上的两点。
用 `strength(不应)=4 > strength(应)=3` 去判「加强」，在道义逻辑上说不通
——「应做 A」变成「不应做 A」不是义务加强，是**义务翻转**。

## 2.3 LegalRuleML：道义算子是**带主体**的定向算子

OASIS LegalRuleML 把 Obligation / Prohibition / Permission 建模为 directed operator，
必须带 Bearer（义务主体）；`[PRO]p = [OBL]¬p`；优先级用 suborder list 表达，
并明确「Obligations and Prohibitions should not be preceded by Permissions and Rights」。

- <https://mirelproject.eu/publications/D1.2.pdf>
- <https://interoperable-europe.ec.europa.eu/sites/default/files/news/2024-07/A%20LegalRuleML%20specialisation.pdf>
- <https://groups.oasis-open.org/higherlogic/ws/public/download/66862/legalruleml-core-spec-v1.0-cs01-errata.docx/latest>

**可借的一条**：模态词必须绑定到「哪个主体、哪个动作」，不能只绑到「哪条条款」。
我们的窗口是**纯文本邻近**，没有主体/动作绑定 —— 这是同窗口多模态词取错的根本原因。

## 2.4 多模态同句：业界已从「整段分类」转向「按 span 抽取」

NLLP 2023 / IEEE 2025 关于 deontic modality classification（DMC）的论文明确指出：

> "As deontic modalities in legal text are not mutually exclusive, a key challenge with DMC
> is that it classifies the provided text into a single modality while in reality it might
> have multiple deontic modalities."

并因此把任务改成 NER（按 span 抽模态词 + 作用域）。

- <https://ieeexplore.ieee.org/document/10977902/>
- <https://gz.nstl.gov.cn/paper_detail.html?id=75dd387541aab66caf52cc2cb1c6a022>

EMNLP 2022 的合同道义标注更进一步：一句话里有多个模态时，**按主体（tenant/landlord）分别标注**，
同一句话对不同主体可以一个是 prohibition、一个是 none。

- <https://aclanthology.org/2022.emnlp-main.795.pdf>

**对我们的直接含义**：我们现在的做法（整条 clause 抽一个 `modality` + 整段窗口抽一个 `output_modality`）
正是这两篇论文在批的「single modality」假设。§1.8 那条「正确复述 b) 项却被拦」就是这个假设的直接后果。

## 2.5 作用域绑定：用「终止词」而不是固定字数窗口

NegEx / ConText / PyConTextNLP 是临床 NLP 里做「否定/推测作用域」的成熟方案，做法是：

- 触发词表（pre / post / pseudo 三类）
- **作用域终止词**（conjunction、逗号、分号、句末）
- 句子级作用域，而不是固定 token 窗口

- <https://pmc.ncbi.nlm.nih.gov/articles/PMC4264258/>（ContextD，含作用域与终止词的详细说明）
- <https://ep.liu.se/ecp/085/035/ecp1385035.pdf>（NegEx / PyConTextNLP / SynNeg 三种作用域界定对比）

**可借的一条**：我们现在是「标记处向后固定 240 字」。业界做法是
「从标记往前/往后，遇到句末或分号就停」。对中文取证输出（子项用 `；` 分隔）尤其合适。

## 2.6 RFC 2119：也是成对定档，不是一条标量轴

MUST / MUST NOT / SHOULD / SHOULD NOT / MAY / OPTIONAL —— 六个关键词，
三档语义（绝对要求、推荐、可选），每档**成对**给肯定/否定。

- <https://www.rfc-editor.org/rfc/rfc2119.html>

**对我们的直接含义**：与 §2.1 的国标表结构一致。业界没有把「MUST」和「MUST NOT」
放在一条数轴上比大小。

---

# 第三部分：修复方案（文件级、可回退）

> 全部为**建议**，本报告未实施。按「先止血、再补判据、最后才动契约」排序。

## 3.1 方案 A（止血，只动 `typed_verifier.py`，可整体 revert）

改一个文件：`src/core/verification/typed_verifier.py`。

1. **窗口改双向（主修）**：`text[pos:pos + 240]` → 向前取本句 + 向后取一小段。
   最贴近业界（§2.5）的写法是「从标记向前，遇到句末/分号停」；
   最小改动版是 `text[max(0, pos - 240):pos + 60]`。
   实测依据：§1.3 的探针里，只改成向前取，`extract_modality` 立刻从 `'应'` 变回 `'可'`。
2. **拆开两个标记平面**：`_CITE_MARK` 只认 `[[c:...]]`，`[[m:...]]` 另起一个正则（或干脆不认）。
   理由：`ks_answer.py` 自己写着「法条证据与材料是**两个平面**」。
3. **字面条款号加边界**：`(?<![\d.])` + `re.escape(clause_number)` + `(?![\d.])`，
   避免核验 `5.2` 时命中 `5.2.1`。
4. **同号 evidence 不再共用窗口**：把 `wanted` 从「按 `clause_number` 反查」改成
   「只用**这一条自己的下标** `[[c:i]]`」；字面条款号形态作为兜底保留，
   但字面形态命中时**要求附近出现本条的 `standard_no`**（`_STD_MENTION` 已有现成正则可用）。
5. **窗口空时不再回退整篇**：`or llm_output` 改成「记一条 `modality_unverified`，不参与 `is_valid`」。
   这是**会改口径**的一条（从「宁误报」转向「宁漏报」），需要业主/门禁拍板，见 §3.5。

**回退**：只改这一个文件，`git checkout -- src/core/verification/typed_verifier.py` 即回退。
**风险**：第 5 条会降低拦截面；`modality_weakened` 是 `is_valid` 的拦截项，放松它要慎重。
建议第 5 条单独一个提交，方便单独回退。

## 3.2 方案 B（改契约，动 `models.py`；不建议现在做）

把一条标量轴拆成两条轴：

- `MODALITY_POLARITY`：肯定 / 否定
- `MODALITY_TIER`：要求(3) / 推荐(2) / 允许(1) / 陈述(0)

比较规则：

- **极性不同** ⇒ 报**新**违规类型 `modality_polarity_flipped`（这才是真问题：
  「应→不应」「不应→应」都是把义务翻成禁止或反之），不叫 strengthened/weakened。
- **极性相同** ⇒ 比 tier，沿用现有 strengthened/weakened 语义。

**代价**：`ModalityViolation.violation_type` 是 `Literal['modality_weakened', 'modality_strengthened', 'modality_missing']`
（`src/core/domain/models.py`），加值要走契约变更流程（`MODALITY_STRENGTH` 的注释写着
「权威常量，变更需走契约变更流程」）。前端 `plugin/client` 与 `docs/REQUIREMENTS-v4.3.md` 都要跟。

**这条是「4 条 `应 -> 不应` 到底叫什么」的正解**，但代价明显大于方案 A，建议排在 A 之后。

## 3.3 方案 C（改源侧，动 `classifier.py` + 表结构；代价最大）

对多子项条款（含 `a)`/`b)`/`c)` 或 `1)`/`2)`）逐子项抽 modality，存成列表
（新列或 JSON）。`clause_revision.modality` 保持向后兼容（取首个子项）。
不做这条，§1.8 那类「正确复述 b) 项却被拦」永远修不掉。

## 3.4 现有 3 条判据够不够：不够，至少补 6 条

现有 3 条（`tests/test_modality_window_false_positive.py`）：

1. `test_correct_keke_not_reported_as_strengthened` —— 只断言 `not strengthened`，**断言太弱**（§1.9）
2. `test_real_weakened_still_intercepted` —— 有效
3. `test_correct_buneng_passes` —— 有效，但只覆盖「单模态、单子项」

**建议补的判据**（每条都能用本报告的探针输入直接写）：

| # | 判据 | 能抓住的形态 | 对应章节 |
| --- | --- | --- | --- |
| 4 | 正确复述「可按」且该句**后面还有别的句子**时，不许报 strengthened | 窗口方向（主因） | §1.3 |
| 5 | 同 `clause_number` 两条 evidence（2014/2022 都有 `5.1.1`）时，两条窗口**不相同**，各自取到自己的模态词 | 同号串 | §1.4 |
| 6 | 输出里只有 `[[m:0]]` 时，不许锚定到 `evidence[0]` | 材料平面串 | §1.7 |
| 7 | 核验 `5.2` 时，`5.2.1` 的出现不算本条款提及 | 子串匹配 | §1.7 |
| 8 | 模型**没引用**某条 evidence 时，不许拿整篇第一个模态词判它 | 回退整篇 | §1.5 |
| 9 | 正确复述 §5.3 b) 项「应预先制定作业方案」不许报 weakened | 源侧单 modality | §1.8 |

判据 4 是最重要的一条：它直接把现有判据 1 的侥幸条件（标记在文本末尾）打掉。
判据 9 会让 `tests/test_t06.py` 那类老判据需要重新审视（因为它是**已知缺陷**的正面暴露，不是回归）。

## 3.5 需要业主拍板的一条

**「模型没引用的证据」该怎么处理？** 现在是「回退整篇照样核验」⇒ 必然误报；
改成「跳过」⇒ 会漏掉「模型确实转述了但没标引用」的情况。
两个方向的代价不同（误报 vs 漏报），这是**口径选择**，不是技术选择。
建议：先按「记 `modality_unverified`、不参与 `is_valid`、但在 `verification` 里如实列出来」，
让用户能看见「这条没核到」，再根据真机跑一段时间的误报率决定是否收紧。

---

# 附：本次用到的只读探针（全部在 `var/tmp/`，不进仓）

| 脚本 | 作用 |
| --- | --- |
| `modality-repro.py` | 按真机 derivation 复现两题的违规，逐条打印窗口内容 |
| `modality-probe-direction.py` | 证明窗口方向错（标记后置 vs 向后取窗） |
| `modality-probe-forms.py` | 同号 evidence 串 / `[[m:i]]` 串 / 子串匹配 / 回退整篇 |
| `modality-probe-extract.py` | 证明 `extract_modality` 是词长降序，不是「第一个」 |
| `modality-probe-source.py` | 源侧 `extract_modality(整条)` 的取词结果 |
| `modality-probe-srcmodel.py` | 证明「正确复述 b) 项却被拦」 |
| `modality-probe-testgreen.py` | 证明现有判据 1 为何绿、`is_valid` 实际为 False |
| `modality-probe-clauses.py` | 导出 GB 30871 两版的分级条款原文（只读连接） |
| `modality-probe-dump3.py` | 导出真机 `debug_dump` 那一条记录 |

跑法（本机 venv）：`.\.venv\Scripts\python.exe var\tmp\modality-repro.py`

回归基线：`tests/test_modality_window_false_positive.py` + `tests/test_t06.py` + `tests/test_phase5.py`
实测 `23 passed`（2026-10-19 修改后，本次只读复跑）。
