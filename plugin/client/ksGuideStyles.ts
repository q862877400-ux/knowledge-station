/**
 * ks-dsh-plugin — client/ksGuideStyles.ts
 *
 * 运行时注入的样式表（**为什么不是 CSS module**：见下）。
 *
 * ## 为什么用注入而不是 `import css from './x.module.css'`
 * 我们的 client 构建是 `scripts/build-client.mjs` 里的单一 esbuild 调用，**没有配 CSS loader**
 * （`entryPoints:[client/entry.ts]` → `bundle:true` + `outfile` + `external:['react','react-dom','@deepseek-ai/*']`）。
 * 在 JS 里 import `.css` 会让 esbuild 产出**第二个 .css 文件**，而宿主只加载我们的
 * `client.js`（`/plugins/ks-dsh-plugin/client.js`）——那份 CSS **永远不会被加载**，
 * 症状是"类名在、样式没了"。所以样式必须**由 JS 自己带进去**。
 *
 * ## 数值从哪来
 * 卡片几何**逐条抄**宿主已发货的 `ui-sidebar-terminal/src/client/TerminalGuide.module.css`
 * （业主指名"像新建终端一样"，那就是它的真实数值）：
 *   .entry      flex / border .5px --dsw-alias-border-l4 / radius 24px / bg --dsw-alias-bg-layer-1
 *   .main       flex:1 / gap 14px / min-height 56px / padding 14px 20px / radius 24px 0 0 24px
 *   .title      15px --dsw-alias-label-primary
 *   .description 13px --dsw-alias-label-caption
 *   .trigger    width 44px / radius 0 24px 24px 0
 * 颜色一律走**宿主活的 token**（`var(--dsw-alias-*)`），所以深浅色/换肤自动跟随，我不用管两套色值。
 */

const STYLE_ID = 'ks-dsh-plugin-styles'

/** 开始页入口卡 + 知识库页的样式（类名统一 `ks-` 前缀，避免与宿主类名撞）。 */
export const KS_STYLES = `
/* ===================================================================================
   尺度系统（第 5 步第一块；规格与出处见 docs/UI-BASELINE.md 第二节）
   —— 照 WeKnora 知识库管理的**成体系**做法：4px 网格、受限字号表、受限圆角表、
      受限动效时长。上一轮 UI 难看的根因就是**没有它**（13px/18px 这种现场拍的数字满地都是）。

   ⚠ 为什么挂 \`:root\` 而不是我们某个面板的根类：
     我们的面板分布在宿主的多个插槽里（开始页入口卡 / 右侧栏各 tab / 知识库页…），
     **没有一个共同的祖先**是我们自己的。挂 \`:root\` 只是把 20 来个 \`--ks-*\` 自定义属性
     声明出来（带 \`ks-\` 前缀 = 我们自己的命名空间）：自定义属性**本身不产生任何样式**，
     宿主不读它们就完全无感；代价是宿主 DOM 会继承到这批变量（惰性）。
     若哪天要收窄作用域，把它们挪到我们各面板根类上即可（规则里用的 \`var(--ks-*)\` 不用改）。
   =================================================================================== */
:root{
  /* 间距：4px 网格（4/8/12/16/20/24/32/40） */
  --ks-space-1:4px; --ks-space-2:8px; --ks-space-3:12px; --ks-space-4:16px;
  --ks-space-5:20px; --ks-space-6:24px; --ks-space-8:32px; --ks-space-10:40px;
  /* 字号：受限表（页面标题 20/24、区块标题 16、正文 13/14、辅助 11/12） */
  --ks-fs-xs:11px; --ks-fs-sm:12px; --ks-fs-base:13px; --ks-fs-md:14px;
  --ks-fs-lg:16px; --ks-fs-title:20px; --ks-fs-hero:24px;
  /* 圆角（WeKnora 的 4/6/8/10/12/999） */
  --ks-r-sm:4px; --ks-r-md:6px; --ks-r-lg:8px; --ks-r-card:10px; --ks-r-xl:12px; --ks-r-pill:999px;
  /* 动效时长 */
  --ks-dur-fast:120ms; --ks-dur-base:150ms; --ks-dur-modal:200ms;
  /* 分隔线一律 0.5px（宿主侧本来就是 .5px，跟着它） */
  --ks-sep:.5px;
  /* 卡片/列表几何（WeKnora：卡片高 136 / 网格 gap 12 / 列表行高 60 / 表头 40 / 左右 16） */
  --ks-card-h:136px; --ks-card-gap:var(--ks-space-3); --ks-row-h:60px; --ks-head-h:40px;
}

/* ---------- 开始页入口卡（照 TerminalGuide.module.css 的数值） ---------- */
.ks-guide-entry{box-sizing:border-box;display:flex;align-items:stretch;width:100%;overflow:hidden;
  border:.5px solid var(--dsw-alias-border-l4);border-radius:24px;background:var(--dsw-alias-bg-layer-1)}
.ks-guide-main{flex:1;justify-content:flex-start;gap:14px;min-width:0;height:auto;min-height:56px;
  padding:14px 20px;border-radius:24px 0 0 24px;text-align:left}
.ks-guide-icon{flex:none;color:var(--dsw-alias-label-secondary)}
.ks-guide-text{display:flex;flex-direction:column;gap:3px;min-width:0}
.ks-guide-title{overflow:hidden;color:var(--dsw-alias-label-primary);font-size:15px;line-height:1.4;
  white-space:nowrap;text-overflow:ellipsis}
.ks-guide-desc{overflow:hidden;color:var(--dsw-alias-label-caption);font-size:13px;line-height:1.4;
  white-space:nowrap;text-overflow:ellipsis}
.ks-guide-trigger{align-self:stretch;flex:none;height:auto;width:44px;padding:0;border-radius:0 24px 24px 0}

/* ---------- 知识库页 ---------- */
.ks-kb{display:flex;flex-direction:column;gap:var(--ks-space-2);font-size:var(--ks-fs-base);color:var(--dsw-alias-label-primary);
  min-height:100%;box-sizing:border-box}
.ks-kb-banner{font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-state-warn-label);
  background:var(--dsw-alias-state-warn-tertiary);border:.5px solid var(--dsw-alias-border-l2);
  border-radius:var(--ks-r-lg);padding:var(--ks-space-2) var(--ks-space-3)}
/* ---------- 页面骨架（照 WeKnora 列表页：大标题 + 一行副标题 + 细分隔线） ----------
   ⚠ 0.5px 分隔线用 border-top 而不是 height:1px（后者在 1x 屏上是 1px，比参照粗一倍） */
.ks-page-head{display:flex;flex-direction:column;gap:var(--ks-space-1);padding:var(--ks-space-1) 0 var(--ks-space-3)}
.ks-page-title{font-size:var(--ks-fs-title);line-height:1.3;font-weight:600;color:var(--dsw-alias-label-primary)}
.ks-page-sub{font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-tertiary)}
.ks-page-rule{height:0;flex:none;border-top:var(--ks-sep) solid var(--dsw-alias-border-l2)}

.ks-kb-row{display:flex;align-items:center;gap:var(--ks-space-2)}
.ks-kb-grow{flex:1;min-width:0}
.ks-kb-hint{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
.ks-kb-btn{border:var(--ks-sep) solid var(--dsw-alias-border-l4);border-radius:var(--ks-r-lg);padding:var(--ks-space-1) var(--ks-space-3);font-size:var(--ks-fs-sm);
  color:var(--dsw-alias-label-secondary);background:transparent;cursor:pointer}
.ks-kb-btn:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-kb-btn-primary{background:var(--dsw-alias-brand-primary);color:var(--dsw-alias-bg-base);
  border-color:transparent;font-weight:600}
.ks-kb-card{border:var(--ks-sep) solid var(--dsw-alias-border-l2);border-radius:var(--ks-r-card);padding:var(--ks-space-2) var(--ks-space-3);
  background:var(--dsw-alias-bg-base)}
.ks-kb-card:hover{border-color:var(--dsw-alias-border-l4)}
.ks-kb-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:var(--ks-card-gap)}
.ks-kb-sec{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary);margin-top:4px}
.ks-kb-tree{font-size:var(--ks-fs-base)}
.ks-kb-tline{display:flex;align-items:center;gap:var(--ks-space-1);padding:var(--ks-space-1) var(--ks-space-2);border-radius:var(--ks-r-md);cursor:pointer}
.ks-kb-tline:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-kb-tw{width:12px;flex:none;text-align:center;font-size:10px;color:var(--dsw-alias-label-caption)}
.ks-kb-tn{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ks-kb-tc{font-size:11px;color:var(--dsw-alias-label-caption)}
.ks-kb-doc{display:flex;gap:var(--ks-space-2);padding:var(--ks-space-1) var(--ks-space-2);border-radius:var(--ks-r-md)}
.ks-kb-doc:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-kb-no{flex:none;font-weight:600;font-family:ui-monospace,Consolas,monospace;font-size:12px}
.ks-kb-nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  color:var(--dsw-alias-label-secondary)}
.ks-kb-badge{flex:none;font-size:var(--ks-fs-xs);border-radius:var(--ks-r-sm);padding:0 var(--ks-space-1);
  background:var(--dsw-alias-markdown-tag);color:var(--dsw-alias-label-secondary)}
.ks-kb-badge-ok{background:var(--dsw-alias-state-success-tertiary);color:var(--dsw-alias-state-success-primary)}
.ks-kb-badge-warn{background:var(--dsw-alias-state-warn-tertiary);color:var(--dsw-alias-state-warn-label)}
.ks-kb-badge-bad{background:var(--dsw-alias-state-error-secondary);color:var(--dsw-alias-state-error-primary)}

/* ---------- 知识库页：三段式（目录轨 | 文件列表 | 详情） ---------- */
/* 一列放不下就换行：右栏宽度是业主自己拖的，不许假设它有多宽。 */
.ks-split{display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap;min-height:0}
.ks-rail{flex:0 1 208px;min-width:172px;display:flex;flex-direction:column;gap:8px}
.ks-main{flex:1 1 320px;min-width:280px;display:flex;flex-direction:column;gap:8px;min-height:0}
.ks-detail{flex:0 1 232px;min-width:200px;display:flex;flex-direction:column;gap:6px}
/* 列表头：全选 + 计数 + 新建 */
.ks-lhead{display:flex;align-items:center;gap:8px;padding:2px 2px 6px;
  border-bottom:.5px solid var(--dsw-alias-border-l1)}
.ks-lhead-name{font-size:13px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* 一行文件：勾选框（label 里就是文件名）+ 标签 + 常驻「+标签」 */
.ks-item{display:flex;align-items:center;gap:6px;padding:5px 6px;border-radius:6px}
.ks-item:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-item-on{background:var(--dsw-alias-interactive-bg-hover)}
.ks-item .ks-check{flex:1 1 auto;min-width:0}
/* Checkbox 的可见文字就是文件名：撑开、可截断，别换行把行搞高 */
.ks-item .ks-check>span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  color:var(--dsw-alias-label-secondary);font-size:13px}
.ks-item .ks-check>input{flex:none}
.ks-item-tags{display:flex;align-items:center;gap:4px;flex:none;flex-wrap:wrap;max-width:46%}
.ks-item-add{flex:none;opacity:0}
/* 常驻：业主明确要"名字后面常驻一个 +标签"，所以不是 hover 才出现，只是 hover 时更显眼 */
.ks-item .ks-item-add{opacity:.35}
.ks-item:hover .ks-item-add,.ks-item-on .ks-item-add{opacity:1}
/* 悬浮批量条（有选中才出现）。
   ⚠ 官方硬规则：「Elevated surfaces … set "border: 0" and take "box-shadow:
   var(--dsw-elevation-panel|prominent|soft)". **Never pair a --dsw-alias-border-*
   border with an lv/elevation shadow**」—— 描边由阴影自己画，颜色用
   --dsw-elevation-stroke-color 给（官方 stat-dialog.module.css:21-25 就是这个写法）。
   我第一版写成 "border:.5px solid var(--dsw-alias-border-l4)" + 阴影，属于明令禁止的配对。
   ⚠ 这里**不能写反引号**：整段 CSS 是一个模板字符串，反引号会把它截断（本轮第三次踩）。 */
.ks-batch{position:sticky;bottom:0;display:flex;align-items:center;gap:6px;flex-wrap:wrap;
  margin-top:6px;padding:7px 9px;border:0;border-radius:10px;
  background:var(--dsw-specific-menu);
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l1);
  box-shadow:var(--dsw-elevation-prominent)}
.ks-batch-n{font-size:12px;font-weight:600}
/* 详情字段：日期这一类 label/value 成对 */
.ks-fields{display:flex;flex-direction:column;gap:4px}
.ks-field{display:flex;gap:8px;font-size:12px;line-height:1.5}
.ks-field-k{flex:0 0 62px;color:var(--dsw-alias-label-tertiary)}
.ks-field-v{flex:1;min-width:0;color:var(--dsw-alias-label-primary);word-break:break-word}
.ks-field-v-mono{font-family:ui-monospace,Consolas,monospace}
/* 页内二级 tab（文件 / 标签） */
.ks-subtabs{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
/* 标签视图：一行一个标签 + 它跨了哪些大文件夹 + 在该标签下提问 */
.ks-tagrow{display:flex;align-items:flex-start;gap:8px;padding:6px 7px;border-radius:6px}
.ks-tagrow:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-tagrow-main{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}
.ks-tagrow-name{font-size:13px;font-weight:600}
.ks-tagrow-scope{font-size:11.5px;color:var(--dsw-alias-label-tertiary);word-break:break-word}
/* 检索语法解析预览：把 + / - 的结果**当场显示出来**，省得用户猜 */
.ks-parse{display:flex;gap:6px;align-items:center;flex-wrap:wrap;font-size:11.5px;
  color:var(--dsw-alias-label-tertiary)}
.ks-parse-in{flex:1 1 220px;min-width:180px}
.ks-empty{padding:14px 8px;text-align:center;font-size:12px;color:var(--dsw-alias-label-tertiary)}
/* ⚠ corner-shape:round 是**必须的配对**：官方 docs/web-styling.md「Pair "corner-shape: round"
   with every full-round "border-radius" ("50%", "100%", or a pill radius) so circles and capsules
   keep circular arcs」—— 少了它，支持 superellipse 的 Chromium 上圆点会被压成方角。
   （本行刻意不用反引号：整段 CSS 是一个模板字符串，反引号会把它截断——本轮已踩过 4 次。） */
.ks-dot{flex:none;width:6px;height:6px;border-radius:50%;corner-shape:round;
  background:var(--dsw-alias-label-caption)}

/* ---------- 能力页（一功能一卡一窗） ---------- */
.ks-cap-card{display:flex;flex-direction:column;gap:2px;border:.5px solid var(--dsw-alias-border-l2);
  border-radius:10px;padding:9px 10px;background:var(--dsw-alias-bg-base)}
.ks-cap-card:hover{border-color:var(--dsw-alias-border-l4)}
/* 引擎侧现状：低调一行，别抢卡片的注意力 */
.ks-cap-engine{font-size:11px;color:var(--dsw-alias-label-caption);margin-bottom:6px}
.ks-cap-inline{display:flex;flex-direction:column;gap:5px;margin-bottom:4px}
/* 窗里/卡上的一行旋钮：label 左、控件右（多选时可换行） */
.ks-knobs{display:flex;flex-direction:column;gap:9px}
.ks-knob-row{display:flex;align-items:flex-start;gap:8px;flex-wrap:wrap}
.ks-knob-label{flex:0 0 118px;font-size:12px;color:var(--dsw-alias-label-secondary);
  line-height:24px;overflow:hidden;text-overflow:ellipsis}
.ks-knob-ctl{flex:1 1 160px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;min-width:0}
`

/**
 * 样式表在文档里的**所有权标记**（`data-plugin-css` 的值）。
 *
 * ## 为什么必须标（2026-09-19 整改，官方 preset 同形）
 * 宿主的样式所有权是**按标签属性**认的（`packages/client/modules/src/client/`）：
 * - `system.ts` 的 `claimStyles(id)` **只认** materialization 那一刻已在文档里的
 *   `style:not([data-plugin])`，认领后记进 `record.styles`；
 * - `entry-lifecycle.ts` 的 `removeOwnedStyles(id)` **按 `data-plugin` 删**；
 * - HMR 字节码替换的第 5/6 步就是"删 owned style → 重新注入"。
 *
 * 我们此前只设了 `id`（不设这两个属性），后果有两条**都会真实发生**：
 * 1. **改样式必须整页刷新**：`removeOwnedStyles` 找不到我们的标签，而 `ensureKsStyles`
 *    又按 `#id` 去重直接 return ⇒ 新 CSS **永远不会生效**（这正是官方所说
 *    "只有 bootstrap / 静态装配库 / shell 才需要重建页面"之外，我们自找的例外）；
 * 2. **样式可能被别人认领后删掉**：任何插件 materialize 时 `claimStyles` 会把我们的
 *    无名标签收进它的 record，它卸载时一并删除，而我们没有 CSS Module 兜底。
 *
 * ⇒ 两个属性都写上（与官方 preset `tsdown.client.ts` 的注入同形），
 * 并把**首次注入放到模块顶层**（见文件末尾）——只有"factory 执行期"注入才落在
 * `claimStyles` 的窗口内。
 */
const PLUGIN_NAME = 'ks-dsh-plugin'
const STYLE_OWNER = `${PLUGIN_NAME}/ksGuideStyles.css`

/**
 * 把样式表插进文档（**幂等**：按 `data-plugin-css` 去重；SSR/无 document 环境直接返回）。
 *
 * 为什么去重键从 `#id` 改成属性：HMR 重新执行本模块时，旧标签可能已被
 * `removeOwnedStyles` 删掉，也可能还在；按属性查既能认出**我们自己的**旧标签、
 * 又不会误认别人的。
 */
export function ensureKsStyles(): void {
  if (typeof document === 'undefined') return
  const existing = document.querySelector(`style[data-plugin-css="${STYLE_OWNER}"]`)
  if (existing !== null) return
  const el = document.createElement('style')
  el.id = STYLE_ID                       // 保留 id：便于调试与业主在 devtools 里一眼认出
  el.dataset.plugin = PLUGIN_NAME        // removeOwnedStyles 按它删
  el.dataset.pluginCss = STYLE_OWNER     // claimStyles 按它收/去重
  el.textContent = KS_STYLES
  document.head.appendChild(el)
}

// 模块顶层的**首次注入**：client bundle 的工厂执行期就会跑到这里，
// 于是标签在"插件 materialize"那一刻已在文档里 ⇒ 落在 `claimStyles` 的认领窗口内，
// 归属明确、HMR 能删能重注。组件渲染时再调 `ensureKsStyles()` 只是幂等兜底。
ensureKsStyles()
