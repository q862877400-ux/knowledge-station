/**
 * ks-dsh-plugin — src/compliance-sentry.js  （合规护航三件套 C1，2026-09-22）
 *
 * 省 token 硬约束（业主 2026-09-22：「不能搞了半天是在每次对话的默认提示词里塞了一大段的
 * 合规性问题规范，每次对话都发一遍」）的落地：
 *   L0 **哨句**（每轮 ≈30 字，常驻一段的全部内容）；
 *   L1 **按需段**（轻量前置判据命中才带；未命中**零增量**）；
 *   **规范全文 = 技能文件**（`.dsh/skills/compliance-qa/SKILL.md`，唯一出处）。
 *
 * ## 单一出处纪律（判据钉死，结构上防漂移）
 * - `KS_COMPLIANCE_SENTRY` / `COMPLIANCE_SKILL_BODY` 唯一住在这里；
 * - SKILL.md 的正文**由 COMPLIANCE_SKILL_BODY 生成**（判据钉字节相等——谁改一边不同步就红）；
 * - L1 段文**运行时从 COMPLIANCE_SKILL_BODY 抽取**（`extractL1()`）——不是第二份手写常量，
 *   复制漂移在结构上不可能。
 */

/** L0 哨句（唯一所有者；全库判据钉"字面只此一处"）。 */
export const KS_COMPLIANCE_SENTRY =
  '涉及法规/国标/行标/公司制度的结论，必须先用 ks 工具核验（先查库拿原文）。'

/** 预判据词族（宽进：误触发可容忍——多花一次 L1；漏触发由哨句兜底）。
 *  `(?<![方算想说])法` 覆盖"安全生产法"这类法名形（宽进；方法/算法/想法/说法除外）。 */
const TRIGGER_WORDS = /法规|法律|条例|办法|规定|标准|国标|行标|团标|地标|制度|合规|审批|许可|资质|禁止|不得|应当|必须|(?<![方算想说])法/

/**
 * 标准号模式的**前缀表**——与 `src/core/knowledge/doc_catalog.py` 的 `_STD_NO_PREFIX`
 * 同源（长的在前；判据 smoke-compliance-sentry 钉两表逐词相等，防两份漂移）。
 */
export const STD_NO_PREFIXES = [
  'GB/T', 'GBT', 'GBZ', 'GB', 'AQ', 'JGJ', 'JG', 'CJJ', 'DB', 'SH', 'HG', 'TSG', 'YS', 'SN', 'JB', 'QB', 'NY', 'SL', 'DL',
]

const STD_NO_RE = new RegExp(`(?:${STD_NO_PREFIXES.join('|')})(?![A-Za-z])\\s*\\d`)

/** 轻量前置判据（零 token）：这段话里有没有受规管事项/标准号/强制词？ */
export function matchComplianceSentry(text) {
  const t = typeof text === 'string' ? text : ''
  return TRIGGER_WORDS.test(t) || STD_NO_RE.test(t)
}

/** 按需段名（照 FORENSIC_SECTION_NAME 的机制加；旧段一个字不动）。 */
export const COMPLIANCE_SECTION_NAME = 'ks:compliance-sentry'

/** 规范全文（**唯一出处**）。SKILL.md 由它生成；L1 由它抽取。 */
export const COMPLIANCE_SKILL_BODY = `## 一、什么时候用本技能

用户在问法规 / 国标 / 行标 / 公司制度相关的判断、要求、义务、能不能做、怎么做才合规——
无论他有没有明说"合规"两个字（隐性合规问题同样适用：提到动火、高处、吊装、用电、环保、
劳动保护、合同条款、内部制度等受规管的事项，本技能自动生效）。

## 二、作答铁律（违反任何一条 = 整条作废）

1. 禁止用模型预训练知识直接给合规结论。凡涉法律法规/国标/行标/公司制度的任何数字、
   等级、阈值、强制语气、时限，都必须有库内原文支撑。
2. 先查库（本机知识库）：用检索取回条款原文（含条款号、效力状态）。取到 ⇒ 以原文作依据作答。
3. 库内没有 ⇒ 先上网调研应服从的法规与权威出处（谁发布、哪一版、现行与否），
   然后每次都先问用户（原话征求同意）：要不要把这份下载入库？——未经同意不得入库，
   同意后入库、入库后以入库原文核验再作答。
4. 结论一律给可点的原文链接（红色定位箭头定位到那一页那一行）；链接来自库内条目的
   evidence_url，不自拼。
5. 结论分三段：引用的依据（条款号+原文摘句）/ 推导 / 结论。强制性语气不许说软
   （"必须/严禁/应"照原词），例外条款不许吞掉，数值逐字核对。
6. 效力状态如实标注：现行有效 / 即将实施（写明生效日）/ 已被替代（给替代件）/ 已废止（明说）。
   排序红线：现行有效 > 效力次之 > 匹配度。
7. 公司制度（非公开）走参考资料平面同待遇：只用已批准材料；来源层级（T0~T4）与任务内效力
   （必须遵守/仅供参考）按用户设的说，不合成"可信度分数"。
8. 查不到就说查到什么程度、缺什么——绝不编条款号、不编数值、不给"大概"。

## 三、隐性问题的轻量前置判据（哨句触发后的第一动作）

- 这段话里有没有受规管事项（作业类型/设备/物质/人员资质/时限/禁止事项）？
- 有没有该有依据却没给依据的合规断言（"这样就行/没问题/按惯例"）？
- 有没有与库内条款可能冲突的方案（数值、等级、流程顺序）？
命中任意一条 ⇒ 按"作答铁律"走查库流程；全不命中 ⇒ 正常干活，不打扰。

## 四、触发后的会话内状态（省 token）

只带一句短状态标记（形如「⚖ 合规护航：待命」），不把本技能全文重复进上下文。
本技能全文只在技能被加载时进一次上下文。

## 五、默认提示词里的哨句（只此一句常驻）

涉及法规/国标/行标/公司制度的结论，必须先用 ks 工具核验（先查库拿原文）。

## 六、与既有规则的关系

SYSTEM_PROMPT 的规则 1~9（三段式/效力门/数值核对/强制语气/链接面/排序红线/查不到不说满）继续有效，
本技能是流程层的增强，不替代、不改写；两边冲突时以更严者为准。`

/**
 * L1 段文 = 从规范全文**运行时抽取**（「二、作答铁律」整节 + 一句指路）——
 * 不是第二份手写常量 ⇒ 复制漂移结构上不可能（判据另钉 L1 每行 ⊆ SKILL_BODY）。
 */
export function extractL1(body = COMPLIANCE_SKILL_BODY) {
  const start = body.indexOf('## 二、作答铁律')
  const end = body.indexOf('## 三、')
  const core = start >= 0 && end > start ? body.slice(start, end).trim() : body.trim()
  return `合规护航（轻量前置判据命中 ⇒ 本段按需注入）：\n${core}\n完整规范见 compliance-qa 技能（唯一出处）。`
}

/**
 * systemPrompt.section 的构造（照 makeChatModeSection 的形状：同步 text provider）。
 * opts.isTriggered(sessionId)：本回合预判据是否命中（触发源接线归 C2：KsScopeChip 载体）；
 * 缺省 = 只带 L0 哨句（每轮 ≈30 字——省 token 硬约束的底线）。
 */
export function buildComplianceSection(opts = {}) {
  return {
    name: COMPLIANCE_SECTION_NAME,
    text: (context) => {
      const sessionId = context?.agent?.session?.id
      const triggered = typeof opts.isTriggered === 'function' ? opts.isTriggered(sessionId) === true : false
      return triggered ? `${KS_COMPLIANCE_SENTRY}\n\n${extractL1()}` : KS_COMPLIANCE_SENTRY
    },
  }
}
