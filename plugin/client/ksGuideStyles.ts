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
  /* 间距：4px 网格（4/8/12/16/20/24/32/40）。
     ⚠ 没有 2/3/6/7/9/10/14px 这些档 —— 它们曾经散在 17 处（第 5 步 5c 全部收掉）。
       6px 这一档**刻意不设**：它只会被用来当"8px 的近似值"，而近似值是漂移的入口
       （5c 实测：成对出现的 padding:2px 2px 6px / 9px 10px 正是这么来的）。
       护栏见 plugin/scripts/smoke-ui-scale.mjs（只减不增的棘轮）。 */
  --ks-space-1:4px; --ks-space-2:8px; --ks-space-3:12px; --ks-space-4:16px;
  --ks-space-5:20px; --ks-space-6:24px; --ks-space-8:32px; --ks-space-10:40px;
  /* 字号：受限表（页面标题 20/24、区块标题 16、正文 13/14、辅助 11/12） */
  --ks-fs-xs:11px; --ks-fs-sm:12px; --ks-fs-base:13px; --ks-fs-md:14px;
  --ks-fs-lg:16px; --ks-fs-title:20px; --ks-fs-hero:24px;
  /* ⚠ 一个**不在上面受限表里**的字号，只有它一个例外，理由如下（5c 定）：
     10px 是"徽章/树形小箭头/分子分母"这一档的尺寸。受限表最小的 11px 在 260px 窄列里
     会让「▾」和 Tag 胶囊明显发胖、行节距跟着涨（--ks-row-h-narrow 是 44px 的硬约束）。
     它**不是**"11px 的近似值"，是上面那三处的专档 ⇒ 加 token 而不是硬掰回 11px。 */
  --ks-fs-2xs:10px;
  /* 圆角（WeKnora 的 4/6/8/10/12/999） */
  --ks-r-sm:4px; --ks-r-md:6px; --ks-r-lg:8px; --ks-r-card:10px; --ks-r-xl:12px; --ks-r-pill:999px;
  /* 动效时长 */
  --ks-dur-fast:120ms; --ks-dur-base:150ms; --ks-dur-modal:200ms;
  /* 分隔线一律 0.5px（宿主侧本来就是 .5px，跟着它） */
  --ks-sep:.5px;
  /* 卡片/列表几何（WeKnora：卡片高 136 / 网格 gap 12 / 列表行高 60 / 表头 40 / 左右 16）
     ⚠ 行高分两档：60 是**全宽**文档列表的数；我们侧栏是 ~300px 窄列，用 44（口径见 UI-BASELINE 二）。 */
  --ks-card-h:136px; --ks-card-gap:var(--ks-space-3); --ks-row-h:60px; --ks-row-h-narrow:44px; --ks-head-h:40px;
}

/* ---------- 开始页入口卡（照 TerminalGuide.module.css 的数值） ----------
   ⚠ 5c 收口：这里原是 gap 14px / padding 14px 20px（逐字抄宿主 TerminalGuide）。宿主那份是
     它自己的组件、也**不用**我们这套 token，所以抄数值在"像宿主"上是对的；但在我们这张表里
     它就是两处离网格字面值。5c 的处置：**收进 4px 网格**（gap 12 / padding 12px 20px），
     视觉差 2px、肉眼不可辨，换来的是这张表里再没有"14px"这一档（棘轮计数 17→0）。 */
.ks-guide-entry{box-sizing:border-box;display:flex;align-items:stretch;width:100%;overflow:hidden;
  border:.5px solid var(--dsw-alias-border-l4);border-radius:24px;background:var(--dsw-alias-bg-layer-1)}
.ks-guide-main{flex:1;justify-content:flex-start;gap:var(--ks-space-3);min-width:0;height:auto;min-height:56px;
  padding:var(--ks-space-3) var(--ks-space-5);border-radius:24px 0 0 24px;text-align:left}
.ks-guide-icon{flex:none;color:var(--dsw-alias-label-secondary)}
.ks-guide-text{display:flex;flex-direction:column;gap:var(--ks-space-1);min-width:0}
.ks-guide-title{overflow:hidden;color:var(--dsw-alias-label-primary);font-size:var(--ks-fs-lg);line-height:1.4;
  white-space:nowrap;text-overflow:ellipsis}
.ks-guide-desc{overflow:hidden;color:var(--dsw-alias-label-caption);font-size:var(--ks-fs-base);line-height:1.4;
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
.ks-kb-sec{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary);margin-top:var(--ks-space-1)}
.ks-kb-tree{font-size:var(--ks-fs-base)}
.ks-kb-tline{display:flex;align-items:center;gap:var(--ks-space-1);padding:var(--ks-space-1) var(--ks-space-2);border-radius:var(--ks-r-md);cursor:pointer}
.ks-kb-tline:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-kb-tw{width:12px;flex:none;text-align:center;font-size:var(--ks-fs-2xs);color:var(--dsw-alias-label-caption)}
.ks-kb-tn{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ks-kb-tc{font-size:var(--ks-fs-xs);color:var(--dsw-alias-label-caption)}
.ks-kb-doc{display:flex;gap:var(--ks-space-2);padding:var(--ks-space-1) var(--ks-space-2);border-radius:var(--ks-r-md)}
.ks-kb-doc:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-kb-no{flex:none;font-weight:600;font-family:ui-monospace,Consolas,monospace;font-size:var(--ks-fs-sm)}
.ks-kb-nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  color:var(--dsw-alias-label-secondary)}
.ks-kb-badge{flex:none;font-size:var(--ks-fs-xs);border-radius:var(--ks-r-sm);padding:0 var(--ks-space-1);
  background:var(--dsw-alias-markdown-tag);color:var(--dsw-alias-label-secondary)}
.ks-kb-badge-ok{background:var(--dsw-alias-state-success-tertiary);color:var(--dsw-alias-state-success-primary)}
.ks-kb-badge-warn{background:var(--dsw-alias-state-warn-tertiary);color:var(--dsw-alias-state-warn-label)}
.ks-kb-badge-bad{background:var(--dsw-alias-state-error-secondary);color:var(--dsw-alias-state-error-primary)}

/* ---------- 知识库页：三段式（目录轨 | 文件列表 | 详情） ---------- */
/* 一列放不下就换行：右栏宽度是业主自己拖的，不许假设它有多宽。 */
.ks-split{display:flex;gap:var(--ks-space-2);align-items:flex-start;flex-wrap:wrap;min-height:0}
.ks-rail{flex:0 1 208px;min-width:168px;display:flex;flex-direction:column;gap:var(--ks-space-2)}
.ks-main{flex:1 1 320px;min-width:280px;display:flex;flex-direction:column;gap:var(--ks-space-2);min-height:0}
.ks-detail{flex:0 1 232px;min-width:200px;display:flex;flex-direction:column;gap:var(--ks-space-2)}
/* 列表头：全选 + 计数 + 新建 */
.ks-lhead{display:flex;align-items:center;gap:var(--ks-space-2);padding:var(--ks-space-1) 0 var(--ks-space-2);
  border-bottom:.5px solid var(--dsw-alias-border-l1)}
.ks-lhead-name{font-size:var(--ks-fs-base);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* 一行文件：勾选框（label 里就是文件名）+ 标签 + 常驻「+标签」 */
.ks-item{box-sizing:border-box;display:flex;align-items:center;gap:var(--ks-space-2);padding:var(--ks-space-1) var(--ks-space-2);
  border-radius:var(--ks-r-md);min-width:0;flex-wrap:nowrap;min-height:var(--ks-row-h-narrow)}
/* ⚠ 行高口径（**改在 2026-09-20 第三轮，依据 ui5 复核实测**）：
   原来这里没有 box-sizing ⇒ .ks-item 是 **content-box** ⇒ min-height:44px 只是**内容盒**下限，
   再加上 padding 4/8 ⇒ 真实行高 **52px**、行节距 **60px**，而文档/token 说的是 44 —— 暗账。
   现在加 box-sizing:border-box ⇒ min-height:44px 就是**边框盒**下限，与 token 同口径。
   ⚠ 但**实测**结论是：即便改成 border-box，宿主 Checkbox 自带的行高仍可能把行撑过 44px
   （min-height 只是**下限**）。真实值以 ui-render-shot.mjs 量出来的 measured 为准，
   写进 docs/UI-BASELINE.md（"实测"那两栏）——**文档必须与实测一致**，不许再照 token 反推。
   ⚠ 注释里不许出现反引号（整段 CSS 是一个模板字符串）—— 本轮已踩**第六次**（2026-09-20 第三轮：
     上面这段初稿用了反引号包属性名，esbuild 报 Expected ";" but found "min"）。 */
.ks-item:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-item-on{background:var(--dsw-alias-interactive-bg-hover)}
/* 文件名（Checkbox 的可见文字）宽度：**给上限、不给 flex:1**。
   5c 实测（kb@1300，行宽 820）：原来是 flex:1 ⇒ 文件名盒子吃到 46% 上限、
   标签簇被挤到最右边，**文件名与标签之间空 285~390px**（离屏渲染量出来的 deadGap）。
   改法（克制，不动行结构）：① 文件名只用**内容宽**、上限 40%（窄列下自然更小）；
   ② 标签簇改成"内容宽 + 可缩"，紧跟在文件名后面 ⇒ 不再有那 300px 死白；
   ③ 右侧按钮组的第一个 btn 用 margin-left:auto 钉在行尾（操作列对齐，与文件名长短无关）。
   ⚠ 注释里不许出现反引号（整段 CSS 是一个模板字符串）—— 本轮已踩**第五次**（2026-09-20 5c：
     写了一句『右侧按钮组 「margin-left:auto」钉在行尾』，那对反引号把模板截断，
     esbuild 报 "Expected ; but found margin"）。写 CSS 属性名时**直接写**，不要加引号装饰。 */
.ks-item .ks-check{flex:0 1 auto;min-width:0;max-width:40%}
/* Checkbox 的可见文字就是文件名：撑开、可截断，别换行把行搞高 */
.ks-item .ks-check>span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  color:var(--dsw-alias-label-secondary);font-size:var(--ks-fs-base)}
.ks-item .ks-check>input{flex:none}
/* 标签组：**允许自己内部换行**（标签多了就长高），但**不许把右边的按钮挤扁**
   —— 无宽约束时「详情」会被压成两行「详／情」（2026-09-20 离屏截图实测，见 UI-BASELINE 第六节）。
   ⚠ 注释里**不许出现反引号**（整段 CSS 是一个模板字符串）—— 本轮已经踩了四次。 */
.ks-item-tags{display:flex;align-items:center;gap:var(--ks-space-1);flex:0 1 auto;min-width:0;flex-wrap:wrap}
/* 行内按钮：**永不压缩、永不折字**（这条是上面那个缺陷的正面约束）。
   第一个行内按钮吃下剩余空间 ⇒ 按钮组钉在**行尾**（操作列对齐），文件名/标签留在左边。 */
.ks-item-btn{flex:none;white-space:nowrap}
.ks-item-btn:first-of-type{margin-left:auto}
.ks-item-add{flex:none;opacity:0;white-space:nowrap}
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
.ks-batch{position:sticky;bottom:0;display:flex;align-items:center;gap:var(--ks-space-2);flex-wrap:wrap;
  margin-top:var(--ks-space-2);padding:var(--ks-space-2) var(--ks-space-3);border:0;
  border-radius:var(--ks-r-card);
  background:var(--dsw-specific-menu);
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l1);
  box-shadow:var(--dsw-elevation-prominent)}
.ks-batch-n{font-size:var(--ks-fs-sm);font-weight:600}
/* 详情字段：日期这一类 label/value 成对 */
.ks-fields{display:flex;flex-direction:column;gap:var(--ks-space-1)}
.ks-field{display:flex;gap:var(--ks-space-2);font-size:var(--ks-fs-sm);line-height:1.5}
.ks-field-k{flex:0 0 62px;color:var(--dsw-alias-label-tertiary)}
.ks-field-v{flex:1;min-width:0;color:var(--dsw-alias-label-primary);word-break:break-word}
.ks-field-v-mono{font-family:ui-monospace,Consolas,monospace}
/* 页内二级 tab（文件 / 标签） */
.ks-subtabs{display:flex;align-items:center;gap:var(--ks-space-2);flex-wrap:wrap}
/* 标签视图：一行一个标签 + 它跨了哪些大文件夹 + 在该标签下提问 */
.ks-tagrow{display:flex;align-items:flex-start;gap:var(--ks-space-2);padding:var(--ks-space-2);border-radius:var(--ks-r-md)}
.ks-tagrow:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-tagrow-main{flex:1;min-width:0;display:flex;flex-direction:column;gap:var(--ks-space-1)}
.ks-tagrow-name{font-size:var(--ks-fs-base);font-weight:600}
.ks-tagrow-scope{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary);word-break:break-word}
/* 检索语法解析预览：把 + / - 的结果**当场显示出来**，省得用户猜 */
.ks-parse{display:flex;gap:var(--ks-space-2);align-items:center;flex-wrap:wrap;font-size:var(--ks-fs-sm);
  color:var(--dsw-alias-label-tertiary)}
.ks-parse-in{flex:1 1 220px;min-width:180px}
.ks-empty{padding:var(--ks-space-4) var(--ks-space-2);text-align:center;font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
/* ⚠ corner-shape:round 是**必须的配对**：官方 docs/web-styling.md「Pair "corner-shape: round"
   with every full-round "border-radius" ("50%", "100%", or a pill radius) so circles and capsules
   keep circular arcs」—— 少了它，支持 superellipse 的 Chromium 上圆点会被压成方角。
   （本行刻意不用反引号：整段 CSS 是一个模板字符串，反引号会把它截断——本轮已踩过 4 次。） */
.ks-dot{flex:none;width:6px;height:6px;border-radius:50%;corner-shape:round;
  background:var(--dsw-alias-label-caption)}

/* ---------- 能力页（一功能一卡一窗） ---------- */
.ks-cap-card{display:flex;flex-direction:column;gap:var(--ks-space-1);border:.5px solid var(--dsw-alias-border-l2);
  border-radius:var(--ks-r-card);padding:var(--ks-space-2) var(--ks-space-3);background:var(--dsw-alias-bg-base)}
.ks-cap-card:hover{border-color:var(--dsw-alias-border-l4)}
/* 引擎侧现状：低调一行，别抢卡片的注意力 */
.ks-cap-engine{font-size:var(--ks-fs-xs);color:var(--dsw-alias-label-caption);margin-bottom:var(--ks-space-1)}
.ks-cap-inline{display:flex;flex-direction:column;gap:var(--ks-space-1);margin-bottom:var(--ks-space-1)}
/* 窗里/卡上的一行旋钮：label 左、控件右（多选时可换行） */
.ks-knobs{display:flex;flex-direction:column;gap:var(--ks-space-2)}
.ks-knob-row{display:flex;align-items:flex-start;gap:var(--ks-space-2);flex-wrap:wrap}
.ks-knob-label{flex:0 0 118px;font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary);
  line-height:24px;overflow:hidden;text-overflow:ellipsis}
.ks-knob-ctl{flex:1 1 160px;display:flex;align-items:center;gap:var(--ks-space-2);flex-wrap:wrap;min-width:0}

/* ================================================================================
   入库面板（KsIngestPanel）—— 第 5 步 5c 把它的**行内样式全量搬到这里**
   --------------------------------------------------------------------------------
   搬之前它整页 0 个 var(--dsw-*)/var(--ks-*) + 21 处硬编码色值（#1a7f37 / #9a6700 /
   #b42318 / #57606a / #0969da / #d0d7de / #eaeef2 / #c4c4c4 / #7f7f7f / #111111 /
   #e9e9e9 / #ffffff …）⇒ 深浅色/换肤时它是唯一"不跟队"的一页，业主的观感就是
   "不像同一个产品"。现在颜色一律走宿主活 token，间距/圆角/字号一律走 --ks-*。
   三色分级（可入库/需人工确认/不建议入库）的**语义没变**，变的只是它取色/取间距的方式。
   ================================================================================ */
.ks-ing{display:flex;flex-direction:column;gap:var(--ks-space-2);font-size:var(--ks-fs-base);
  color:var(--dsw-alias-label-primary);padding:var(--ks-space-1) 0}
/* 说明段：正文色的次级档，行高比正文松（成段阅读） */
.ks-ing-note{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary);line-height:1.6}
.ks-ing-toggle{display:flex;align-items:center;gap:var(--ks-space-2);cursor:pointer}
.ks-ing-toggle input{flex:none;margin:0}
.ks-ing-row{display:flex;align-items:center;gap:var(--ks-space-2);flex-wrap:wrap}
.ks-ing-dir{width:62%;min-width:180px}
.ks-ing-mono{font-family:ui-monospace,Consolas,monospace;font-size:var(--ks-fs-sm);word-break:break-all}
.ks-ing-num{width:64px}
.ks-ing-files{display:flex;flex-direction:column;gap:var(--ks-space-1)}
.ks-ing-size{color:var(--dsw-alias-label-tertiary)}
/* 三桶总账的一枚胶囊：颜色由 verdictMeta 的内联边界色给（三类语义色走 --dsw-alias-state-*） */
.ks-ing-buckets{display:flex;align-items:center;flex-wrap:wrap;gap:var(--ks-space-2)}
.ks-ing-chip{display:inline-flex;align-items:center;gap:var(--ks-space-1);padding:0 var(--ks-space-2);
  border:var(--ks-sep) solid var(--dsw-alias-border-l2);border-radius:var(--ks-r-pill);
  font-size:var(--ks-fs-sm);white-space:nowrap}
/* 单本报告的一行（批量的文件行也用它）：0.5px 分隔线，不是 1px */
.ks-ing-line{display:flex;gap:var(--ks-space-2);padding:var(--ks-space-2) 0;
  border-top:var(--ks-sep) solid var(--dsw-alias-border-l1)}
.ks-ing-line-first{border-top:0}
.ks-ing-icon{flex:none;min-width:18px}
.ks-ing-grow{flex:1;min-width:0}
/* 文件名是个**看起来像链接**的按钮（点了拉该本的完整体检报告） */
.ks-ing-link{border:0;background:none;padding:0;cursor:pointer;text-align:left;
  font-size:var(--ks-fs-base);color:var(--dsw-alias-link);font-family:inherit}
.ks-ing-link:hover{text-decoration:underline}
/* 报告本体：一块描边卡片，内部字段成组 */
.ks-ing-card{border:var(--ks-sep) solid var(--dsw-alias-border-l2);border-radius:var(--ks-r-md);
  padding:var(--ks-space-3);margin-top:var(--ks-space-2);background:var(--dsw-alias-bg-base)}
.ks-ing-h{font-size:var(--ks-fs-base);font-weight:600}
.ks-ing-h-sub{font-weight:400;color:var(--dsw-alias-label-secondary);margin-left:var(--ks-space-2)}
.ks-ing-sub{font-size:var(--ks-fs-sm);font-weight:600;margin-top:var(--ks-space-2)}
.ks-ing-indent{padding-left:var(--ks-space-3)}
/* 第三节：异步全量预览（与上面用一条**虚线**分开——它是另一条时间尺度的操作） */
.ks-ing-async{margin-top:var(--ks-space-4);border-top:var(--ks-sep) dashed var(--dsw-alias-border-l2);
  padding-top:var(--ks-space-3)}
.ks-ing-progress{margin-top:var(--ks-space-2);height:8px;border-radius:var(--ks-r-sm);
  background:var(--dsw-alias-bg-layer-3);overflow:hidden}
.ks-ing-progress-fill{height:100%;background:var(--dsw-alias-brand-primary);
  transition:width var(--ks-dur-modal) ease}
/* 语义色只用在这三处：错误红、需确认黄、成功绿 —— 全部是宿主 token */
.ks-ing-err{color:var(--dsw-alias-state-error-primary)}
.ks-ing-warn{color:var(--dsw-alias-state-warn-label)}
.ks-ing-ok{color:var(--dsw-alias-state-success-primary)}
/* 三色分级（可入库 / 需人工确认 / 不建议入库）的**唯一取色处**：都由宿主状态色解出。
   ⚠ 语义一个字没动 —— 5c 之前这三色是 #1a7f37 / #9a6700 / #b42318 三个硬编码值。 */
.ks-ing-tone-ok{color:var(--dsw-alias-state-success-primary);
  border-color:var(--dsw-alias-state-success-primary)}
.ks-ing-tone-warn{color:var(--dsw-alias-state-warn-label);
  border-color:var(--dsw-alias-state-warn-label)}
.ks-ing-tone-block{color:var(--dsw-alias-state-error-primary);
  border-color:var(--dsw-alias-state-error-primary)}
.ks-ing-tone-muted{color:var(--dsw-alias-label-secondary);
  border-color:var(--dsw-alias-border-l2)}
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
