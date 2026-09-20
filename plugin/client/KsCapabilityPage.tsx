/**
 * ks-dsh-plugin — client/KsCapabilityPage.tsx
 *
 * 「能力」页（业主 2026-09-19 **亲定**的结构）：
 * > `/platform/agents` 这一页的结构思路也可以抄——不是我们也要搞 agents，而是说我们的
 * > 制度修订、自动生成检查清单、合同审计这些功能，都可以在这样一个页面里**对每一个单独功能
 * > 留一个设置窗口**，点一下就能设置各种东西，**而不是全部塞进设置按钮里**。
 *
 * ## 抄的是两条**结构**（不是抄它那 17 组）
 * 1. **「自带」本身是一个分组**；
 * 2. **每张卡点开就是"它自己的全部旋钮"**。
 *
 * ## 业主给的两条边界（本文件照做，不许违反）
 * 1. **别抄它那 17 组**：248 KB 的设置窗正是"什么都往里塞"的下场。
 *    我们每个能力的窗**只放它自己的旋钮，3–6 组为上限**；超过就说明该拆。
 * 2. **旋钮少于 3 个的能力不配独立窗口**，直接在**卡片上内联**（否则点开一个空窗更烦）。
 *    ⇒ 代码里由 `knobs.length < 3` 决定是"开窗"还是"内联"，**不是靠人记着**。
 *
 * ## 本轮性质（同知识库页）
 * **只有 UI**：卡、分组、旋钮全是本文件里的占位常量，**一个引擎接口都没调**；
 * 页首黄条写在界面上。但**交互是真的**（开关能拨、下拉能选、窗能开能关），可以点着体验。
 *
 * ## 为什么用宿主原语而不是自己画
 * 官方规定「Reuse the control before restyling one」⇒ 开关用 `Switch`、多选用 `Checkbox`、
 * 文本用 `Input`、枚举用 `Pill`、窗用 `Modal`（**这四个都是宿主已发货的**，
 * props 逐个读过源码，见 `ksHostPrimitives.d.ts`）。自己不画窗、不画开关。
 */

import { useState, type ReactNode } from 'react'
import { Button, Checkbox, IconInfoOutline14, IconPlusOutline16, Input, Modal, Pill, Switch, Tag } from '@deepseek-ai/dsh-client-ui-primitives'

import { ensureKsStyles } from './ksGuideStyles'

/** 一个旋钮（占位）。`kind` 决定用哪个宿主原语渲染。 */
interface Knob {
  readonly id: string
  readonly label: string
  readonly kind: 'bool' | 'text' | 'enum' | 'multi'
  /** enum/multi 的候选值。 */
  readonly options?: readonly string[]
  /** 占位默认值（bool 用；text 用 string）。 */
  readonly initial?: string | boolean | readonly string[]
  /** 这个旋钮是干什么的（hover 提示）。 */
  readonly hint?: string
}

/** 一项能力（= 一张卡）。 */
interface Capability {
  readonly id: string
  readonly name: string
  readonly desc: string
  /** `builtin` 自带且不可删；`mine` 我启用的；`experimental` 实验性。 */
  readonly group: 'builtin' | 'mine' | 'experimental'
  /** 引擎侧现状（诚实标注：有的引擎有但界面没接）。 */
  readonly engine: string
  readonly knobs: readonly Knob[]
}

/** 三个分组（业主点名：「自带」本身是一个分组）。 */
const GROUPS: readonly { readonly id: Capability['group']; readonly name: string; readonly note: string }[] = [
  { id: 'builtin', name: '自带', note: '法规/标准相关的基础能力，不可删' },
  { id: 'mine', name: '我启用的', note: '按需开启的能力；关掉就不出现在工作流里' },
  { id: 'experimental', name: '实验性', note: '还在验证，口径可能变；默认关' },
]

/**
 * 八项能力（来自 `INTERACTION-DESIGN.md` §6.2 的表，**含引擎现状的诚实标注**）。
 *
 * 旋钮数刻意照业主的边界设计：**< 3 个的不给窗**（例如"条款释义"只有输出格式一个开关）。
 */
const CAPABILITIES: readonly Capability[] = [
  {
    id: 'ask',
    name: '取证问答',
    desc: '按三段式作答，只引现行版，证据可点回原文',
    group: 'builtin',
    engine: '✅ 引擎已有',
    knobs: [
      { id: 'mode', label: '默认口径', kind: 'enum', options: ['轻量', '取证'], initial: '取证', hint: '取证口径会强制走三段式并给证据链接' },
      { id: 'conflict', label: '冲突处理', kind: 'enum', options: ['全量列出', '取一'], initial: '全量列出' },
      { id: 'rankRedline', label: '排序红线开关', kind: 'bool', initial: true, hint: '低于红线的候选不进答案' },
    ],
  },
  {
    id: 'duty',
    name: '义务清单 → 检查表',
    desc: '从条款里抽义务，生成可执行的检查表',
    group: 'builtin',
    engine: '✅ 引擎有、界面没接',
    knobs: [
      { id: 'types', label: '义务类型', kind: 'multi', options: ['应当', '必须', '禁止'], initial: ['应当', '必须'] },
      { id: 'scope', label: '范围', kind: 'text', initial: '公司制度、C65/74 劳动安全技术', hint: '哪些文件夹参与抽取' },
      { id: 'template', label: '输出模板', kind: 'enum', options: ['表格', '逐条'], initial: '表格' },
      { id: 'cite', label: '带出处链接', kind: 'bool', initial: true },
    ],
  },
  {
    id: 'contract',
    name: '合同审计',
    desc: '对着标准/法规审合同条款，三色判定',
    group: 'mine',
    engine: '✅ 引擎有、界面没接',
    knobs: [
      { id: 'reviewType', label: '审查类型', kind: 'enum', options: ['安全条款', '环保条款', '全部'], initial: '安全条款' },
      { id: 'judge', label: '判定口径', kind: 'enum', options: ['严格', '常规'], initial: '常规' },
      { id: 'range', label: '依据范围', kind: 'text', initial: '法律、行政法规、国家标准' },
      { id: 'llm', label: 'LLM 精判', kind: 'bool', initial: false, hint: '开了更准但更慢、更费 token' },
    ],
  },
  {
    id: 'gap',
    name: '制度差距分析',
    desc: '内部制度 vs 外部要求，列出缺什么',
    group: 'mine',
    engine: '✅ 引擎有、界面没接',
    knobs: [
      { id: 'inner', label: '内部制度文件', kind: 'text', initial: '公司制度' },
      { id: 'against', label: '对照范围', kind: 'text', initial: '安全生产法、GB 30871-2022' },
      { id: 'rule', label: '判定规则', kind: 'enum', options: ['缺项', '缺项+弱项'], initial: '缺项' },
    ],
  },
  {
    id: 'explain',
    name: '条款释义 / 批量问答',
    desc: '单条释义，或对一批条款批量提问',
    group: 'mine',
    engine: '✅ 引擎有、界面没接',
    // ⚠ 只有 1 个旋钮 ⇒ 按业主的边界**不配独立窗口**，直接在卡上内联
    knobs: [{ id: 'format', label: '输出格式', kind: 'enum', options: ['一句话', '分点'], initial: '分点' }],
  },
  {
    id: 'inspection',
    name: '每日巡检',
    desc: '定时扫官方渠道，发现发布/修订/废止',
    group: 'builtin',
    engine: '✅ 已有',
    knobs: [
      { id: 'time', label: '时刻', kind: 'text', initial: '06:30' },
      { id: 'channels', label: '渠道范围', kind: 'multi', options: ['国家标准全文公开系统', '应急管理部', '生态环境部', '地方标准信息平台'], initial: ['国家标准全文公开系统'] },
      { id: 'retry', label: '失败重试', kind: 'bool', initial: true },
      { id: 'notify', label: '通知方式', kind: 'enum', options: ['仅站内', '站内+邮件'], initial: '仅站内' },
    ],
  },
  {
    id: 'materials',
    name: '材料评审',
    desc: '上传资料分级评审（批准只能由人做）',
    group: 'experimental',
    engine: '🟡 未真机跑过',
    knobs: [
      { id: 'axisA', label: '轴 A 来源层级默认值', kind: 'enum', options: ['T0 原始出处', 'T3 仅线索'], initial: 'T3 仅线索' },
      { id: 'keep', label: '保留策略', kind: 'enum', options: ['不保留', '保留 30 天'], initial: '不保留' },
    ],
  },
  {
    id: 'ingest',
    name: '文件导入',
    desc: '把本地法规/制度文件灌进知识库',
    group: 'builtin',
    engine: '✅ 已有',
    knobs: [
      { id: 'folder', label: '默认落到哪个文件夹', kind: 'text', initial: '公司制度' },
      { id: 'dryRun', label: '默认 Dry-Run', kind: 'bool', initial: true, hint: '先只看会写什么，不真写' },
      { id: 'bucket', label: '分桶阈值', kind: 'text', initial: '0.75' },
    ],
  },
]

/** 一个旋钮的控件（**按 kind 选宿主原语**，不自己画）。 */
function KnobControl({ knob, value, onChange }: {
  readonly knob: Knob
  readonly value: string | boolean | readonly string[] | undefined
  readonly onChange: (next: string | boolean | readonly string[]) => void
}): ReactNode {
  if (knob.kind === 'bool') {
    return (
      <Switch
        checked={value === true}
        onChange={(next) => { onChange(next) }}
        label={knob.label}
        title={knob.hint}
      />
    )
  }
  if (knob.kind === 'enum') {
    return (
      <div className="ks-knob-row">
        <span className="ks-knob-label">{knob.label}</span>
        <span className="ks-knob-ctl">
          {(knob.options ?? []).map((opt) => (
            <Pill
              key={opt}
              active={value === opt}
              onClick={() => { onChange(opt) }}
            >
              {opt}
            </Pill>
          ))}
        </span>
      </div>
    )
  }
  if (knob.kind === 'multi') {
    const picked = Array.isArray(value) ? value : []
    return (
      <div className="ks-knob-row">
        <span className="ks-knob-label">{knob.label}</span>
        <span className="ks-knob-ctl">
          {(knob.options ?? []).map((opt) => (
            <Checkbox
              key={opt}
              checked={picked.includes(opt)}
              onChange={(next) => {
                const set = new Set(picked)
                if (next) set.add(opt)
                else set.delete(opt)
                onChange([...set])
              }}
              label={opt}
            />
          ))}
        </span>
      </div>
    )
  }
  return (
    <div className="ks-knob-row">
      <span className="ks-knob-label">{knob.label}</span>
      <span className="ks-knob-ctl">
        <Input
          value={typeof value === 'string' ? value : ''}
          title={knob.hint}
          aria-label={knob.label}
          onChange={(event) => { onChange(event.target.value) }}
        />
      </span>
    </div>
  )
}

/** 一张能力卡。`knobs.length < 3` ⇒ **内联**它的旋钮（业主边界 2）；否则点开它自己的窗。 */
function CapabilityCard({ cap, onOpen, open, setKnobValue, values }: {
  readonly cap: Capability
  readonly onOpen: (id: string) => void
  readonly open: boolean
  readonly setKnobValue: (knobId: string, next: string | boolean | readonly string[]) => void
  readonly values: Readonly<Record<string, string | boolean | readonly string[]>>
}): ReactNode {
  const inline = cap.knobs.length < 3
  return (
    <div className="ks-cap-card">
      <div className="ks-kb-row">
        <strong className="ks-kb-grow ks-kb-ct" title={cap.name}>{cap.name}</strong>
        <Tag tone={cap.group === 'experimental' ? 'warning' : 'neutral'}>{cap.knobs.length} 个旋钮</Tag>
      </div>
      <div className="ks-kb-cd">{cap.desc}</div>
      <div className="ks-cap-engine">{cap.engine}</div>
      {inline ? (
        <>
          {/* 旋钮少于 3 个 ⇒ 直接内联在卡上（业主：点开一个空窗比塞在设置里更烦） */}
          <div className="ks-cap-inline">
            {cap.knobs.map((k) => (
              <KnobControl key={k.id} knob={k} value={values[k.id]} onChange={(next) => { setKnobValue(k.id, next) }} />
            ))}
          </div>
          {/* 5c：原为字面 **不单独开窗**（Markdown 粗体标记被当纯文本画出来）⇒ 改 <strong>，
              强调语义保留。同页另三处同理（页首黄条里的两处 + 卡上的这一处）。 */}
          <div className="ks-kb-hint">（旋钮少于 3 个：按约定<strong>不单独开窗</strong>，就地设置）</div>
        </>
      ) : (
        <Button variant="outline" size="sm" onClick={() => { onOpen(cap.id) }} aria-expanded={open}>
          设置…
        </Button>
      )}
    </div>
  )
}

/**
 * 能力页。
 *
 * @returns 三个分组的能力卡网格 + 点开的设置窗；纯 UI（旋钮全是占位）。
 */
export function KsCapabilityPage(): ReactNode {
  ensureKsStyles()
  const [openId, setOpenId] = useState<string | null>(null)
  /** 所有旋钮的当前值（占位状态，刷新即还原）。 */
  const [values, setValues] = useState<Record<string, string | boolean | readonly string[]>>(() => {
    const init: Record<string, string | boolean | readonly string[]> = {}
    for (const cap of CAPABILITIES) {
      for (const k of cap.knobs) if (k.initial !== undefined) init[`${cap.id}.${k.id}`] = k.initial
    }
    return init
  })

  const opened = CAPABILITIES.find((c) => c.id === openId) ?? null
  const setKnobValue = (capId: string) => (knobId: string, next: string | boolean | readonly string[]): void => {
    setValues((prev) => ({ ...prev, [`${capId}.${knobId}`]: next }))
  }
  /** 把某一项能力的旋钮值取出来给控件用。 */
  const valuesFor = (capId: string): Record<string, string | boolean | readonly string[]> => {
    const out: Record<string, string | boolean | readonly string[]> = {}
    for (const [key, v] of Object.entries(values)) {
      if (key.startsWith(`${capId}.`)) out[key.slice(capId.length + 1)] = v
    }
    return out
  }

  return (
    // ⚠ 5j（2026-09-20）：`.ks-page` 只做 container-type（页面留边的宽/窄两档靠它切；
    //    CSS 里容器不能用自己的宽度查自己 ⇒ 留边落在后代的 `.ks-kb` 上）。
    //    零内边距零外边距 ⇒ 不是"盒子套盒子"。里面的 JSX 缩进保持原样（本批不重排）。
    <div className="ks-page">
    <div className="ks-kb">
      {/* 页面骨架：**与知识库页同一套**（.ks-page-head/.ks-page-title/.ks-page-sub/.ks-page-rule）。
          5c 之前这里是「inline 14px 粗体」的一行 ⇒ 两个页面的页头**不同级**：知识库页 20px、
          能力页 14px，用户在 tab 间切时会觉得"小的那个是页里的一块"而不是一页。
          ⚠ 副标题是 5c **新写**的一句（原来没有）：骨架要求"标题 + 一行副标题 + 分隔线"，
          少了副标题那一格，分隔线就贴在标题底下、层级又没了。文案只描述这一页是什么。 */}
      <header className="ks-page-head">
        <div className="ks-page-title">能力</div>
        <div className="ks-page-sub">
          一项能力一张卡：旋钮少于 3 个的就地内联，够 3 个的点开它自己的设置窗
        </div>
      </header>
      <div className="ks-page-rule" />

      {/* 诚实告知条（降级版，同知识库页 P0-1）：内容没删，细则进 title=，一行灰字即可 */}
      <div
        className="ks-kb-banner"
        title={'这一页的结构是业主指定的：一个功能一张卡，点开就是它自己的全部旋钮，而不是全部塞进设置里。'
          + '交互是真的（开关能拨、选项能选、窗能开），可以直接点着体验。'}
      >
        <IconInfoOutline14 />
        <strong>UI 先行：旋钮是占位，后端未接</strong>
      </div>

      <div className="ks-kb-row">
        <span className="ks-kb-hint">{CAPABILITIES.length} 项</span>
      </div>

      {GROUPS.map((group) => {
        const items = CAPABILITIES.filter((c) => c.group === group.id)
        return (
          <div key={group.id}>
            <div className="ks-kb-sec">{group.name}（{items.length}）— {group.note}</div>
            <div className="ks-kb-cards" style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(230px,1fr))' }}>
              {items.map((cap) => (
                <CapabilityCard
                  key={cap.id}
                  cap={cap}
                  open={openId === cap.id}
                  onOpen={(id) => { setOpenId(id) }}
                  setKnobValue={setKnobValue(cap.id)}
                  values={valuesFor(cap.id)}
                />
              ))}
              {/* 末行补位（P0-5）：一组一张虚线「＋ 添加能力」卡（照 WeKnora skill-catalog 第 4 格）。
                  ⚠ **列数是 CSS 自己算的，不由 JS 猜**：.ks-cap-card-add 的 grid-column-end 用 -1
                    （= 显式网格的最后一条列线）⇒ 它从"下一个空位"一直铺到本行末尾，
                    于是无论 auto-fill 算出 2 列、3 列还是 5 列，这一行都被**铺满**、不再留孤位。
                    它不可点（后端未接，做成假按钮更糟）⇒ aria-hidden + title 说明。 */}
              <div className="ks-cap-card-add" aria-hidden="true" title="占位：将来在这里添加一项自己的功能">
                <IconPlusOutline16 size={20} />
                添加能力
              </div>
            </div>
          </div>
        )
      })}

      {/* 它自己的设置窗（宿主 Modal；关掉就把它自己的旋钮收起来） */}
      {opened !== null && (
        <Modal
          open
          onClose={() => { setOpenId(null) }}
          title={`${opened.name} · 设置`}
          closeLabel="关闭"
          description={opened.desc}
          footer={(
            <>
              <span className="ks-kb-hint" style={{ marginRight: 'auto' }}>
                {opened.knobs.length} 个旋钮（约定上限 6 组；超了说明这项能力该拆）
              </span>
              <Button variant="ghost" size="sm" onClick={() => { setOpenId(null) }}>关闭</Button>
            </>
          )}
        >
          <div className="ks-knobs">
            {opened.knobs.map((k) => (
              <KnobControl
                key={k.id}
                knob={k}
                value={valuesFor(opened.id)[k.id]}
                onChange={(next) => { setKnobValue(opened.id)(k.id, next) }}
              />
            ))}
          </div>
        </Modal>
      )}
    </div>
    </div>
  )
}
