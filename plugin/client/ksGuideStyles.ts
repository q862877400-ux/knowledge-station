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
     ⚠ 行高分两档：60 是**全宽**文档列表的数；我们侧栏是 ~300px 窄列，用 44（口径见 UI-BASELINE 二）。
     ⚠ 卡高（136）在 5a 定义后**长期没人用**（P0-2 点名的"死 token"）——2026-09-20 已由
       .ks-kb-cards>*{min-height:var(--ks-card-h)} 真正消费掉（同列卡因此等高），不再是暗账。
     ⚠ 表头 40（--ks-head-h）同类的暗账在 P1-8 才被消费（.ks-lhead 实测 33px → 40px）。
     ⚠ **P1-3（2026-09-20）第三档：--ks-row-h-list:52px** —— 文件行从"一行塞满"改成
       **两行信息**（文件名 + 元数据行）后的行高。为什么不是参照的 61：WeKnora 表格页行高 61
       不在我们的 4px 网格上（52 = 13 个网格单位），且窄侧栏里 61 会把 4 行挤出一屏；
       目标值 52 是 weknora-ui-vs-ours §7.4 定的（"行 52px 两行"）。44 那一档**保留**：
       树的节点行（.ks-kb-tline）仍在用它，别一起改。 */
  --ks-card-h:136px; --ks-card-gap:var(--ks-space-3); --ks-row-h:60px; --ks-row-h-narrow:44px;
  --ks-row-h-list:52px; --ks-head-h:40px;
  /* 描边宽度：0.5px 是**分隔线**档（--ks-sep）；1px 是**结构化描边**档 —— 表格外框/表头底线
     与状态徽章的描边要"真的看得见"（P1-2/P1-5 的验收就是量到这条 1px），用 0.5px 在 1x 屏上
     会退化成半透明发丝、量不出"左右各一行描边色"。两者都进 token，不许在规则里写死 px。 */
  --ks-stroke:1px;
  /* 宿主 Button size=sm 的**档位**（P1-6：批量条按钮实测 28px —— 那是 .ks-batch 的
     align-items:center 加上图标把它撑起来的，不是宿主给的档）。批量条里显式钉 24px。 */
  --ks-btn-h-sm:24px;
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
/* 诚实告知条（**降级版**，2026-09-20 P0-1）
   —— 它曾经是"整块 warn 底色 + 描边 + 8/12 内边距"的 4 行警告块：实测 520 下 **92px 高**、
      1300 下 **56px**，而页标题只有 26px ⇒ 视觉权重是标题的 2.2–3.5 倍，成了全页**唯一的大色块**。
      但它承载的是**诚实告知**（"数据是占位、后端未接"），内容**不许删** ⇒ 只降视觉权重：
      去底色、去描边、padding 收 0、文字走 tertiary，长句压成一行（细则进 title=，hover 才看）。
      参照的等价物是 WeKnora config.png 里那条**单行**带图标条，不是一块橙色面板。 */
.ks-kb-banner{display:flex;align-items:center;gap:var(--ks-space-1);
  font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-tertiary)}
/* ---------- 页面骨架（照 WeKnora 列表页：大标题 + 一行副标题 + 细分隔线） ----------
   ⚠ 0.5px 分隔线用 border-top 而不是 height:1px（后者在 1x 屏上是 1px，比参照粗一倍） */
.ks-page-head{display:flex;flex-direction:column;gap:var(--ks-space-1);padding:var(--ks-space-1) 0 var(--ks-space-3)}
.ks-page-title{font-size:var(--ks-fs-title);line-height:1.3;font-weight:600;color:var(--dsw-alias-label-primary)}
.ks-page-sub{font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-tertiary)}
.ks-page-rule{height:0;flex:none;border-top:var(--ks-sep) solid var(--dsw-alias-border-l2)}

.ks-kb-row{display:flex;align-items:center;gap:var(--ks-space-2)}
.ks-kb-grow{flex:1;min-width:0}
.ks-kb-hint{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
/* ---------- 卡片标题档（P0-2，2026-09-20） ----------
   原来卡片标题写死 13px（行内 style 与 --ks-fs-base）⇒ **卡标题与正文差 0px**，只靠字重分。
   对照 WeKnora resource-card.less 的 15px/22px w600 + letter-spacing .01em：我们取受限字号表的
   14px（--ks-fs-md）—— 窄列（208px 的轨）里 15px 会把标题顶得比页面副标题还大、且不在我们的
   字号表上；14px + 600 已经把"标题 ≠ 正文"这一档立起来了。
   ⚠ 单行截断（省略号）是刻意的：卡片标题只做识别，不做阅读；长名靠 title= 悬停看全。 */
.ks-kb-ct{font-size:var(--ks-fs-md);font-weight:600;letter-spacing:.01em;line-height:1.4;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* 卡片描述（与"计数"分开：计数走 .ks-kb-badge 徽章，描述才是这一档）
   —— 12px secondary（原来是 tertiary，比正文还淡）+ 两行截断（描述长了不再把卡撑高）。 */
.ks-kb-cd{font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-secondary);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
  margin:var(--ks-space-1) 0 var(--ks-space-2)}
/* 卡片页脚（放计数/元数据）：一条 0.5px 上分隔线把它和内容分开（卡内原来三块信息糊成一段）。
   margin-top:auto 让它在"卡被 min-height 撑高"时贴到卡底（父级是 flex column）。 */
.ks-kb-foot{display:flex;align-items:center;gap:var(--ks-space-2);
  margin-top:auto;padding-top:var(--ks-space-2);
  border-top:var(--ks-sep) solid var(--dsw-alias-border-l2)}
.ks-kb-btn{border:var(--ks-sep) solid var(--dsw-alias-border-l4);border-radius:var(--ks-r-lg);padding:var(--ks-space-1) var(--ks-space-3);font-size:var(--ks-fs-sm);
  color:var(--dsw-alias-label-secondary);background:transparent;cursor:pointer}
.ks-kb-btn:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-kb-btn-primary{background:var(--dsw-alias-brand-primary);color:var(--dsw-alias-bg-base);
  border-color:transparent;font-weight:600}
/* ---------- 卡片（P0-3，2026-09-20）：从"描边幽灵"改成宿主 elevation 面 ----------
   之前只有 .5px 描边 + 与页面同色的白底 ⇒ 520 的图上"是不是卡片"要靠猜，同列高度还有
   212/115/85 三档。现在：内边距走 12px（网格值）、阴影走**宿主的 elevation 档**
   （不自己编 rgba —— 深浅色/换肤自动跟随），卡底 0.5px 分隔线（.ks-kb-foot）。
   ⚠ 官方硬规则：「Elevated surfaces … set border: 0 and take box-shadow: var(--dsw-elevation-*)。
      Never pair a --dsw-alias-border-* border with an lv/elevation shadow」⇒ 这里 **border:0**，
      发丝描边由阴影里的 --dsw-elevation-stroke 画（颜色重绑成 border-l2，与改前的描边同档，
      视觉上只多出一层极淡柔光）。hover 只把描边色提一档，语义与改前一致。 */
.ks-kb-card{box-sizing:border-box;display:flex;flex-direction:column;
  border:0;border-radius:var(--ks-r-card);padding:var(--ks-space-3);
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l2);
  background:var(--dsw-alias-bg-base);box-shadow:var(--dsw-elevation-soft);
  transition:box-shadow var(--ks-dur-fast)}
.ks-kb-card:hover{--dsw-elevation-stroke-color:var(--dsw-alias-border-l4);
  box-shadow:var(--dsw-elevation-panel)}
/* 卡片网格：**同列卡等高**（align-items:stretch 是 grid 的默认值，这里写出来当"正面约束"）
   + 子项吃 --ks-card-h 这门**曾被定义却从未消费**的高度档（见 :root 的说明）。
   ⚠ 用 min-height 而不是 height：内容多的卡（内联旋钮的能力卡）仍能长高，不会被截断。 */
.ks-kb-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:var(--ks-card-gap);
  align-items:stretch}
.ks-kb-cards>*{min-height:var(--ks-card-h)}
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
/* ⚠ P2 头条（2026-09-20）：.ks-main 是**容器查询的容器**（container-type:inline-size）
   —— 表格的列档（窄档 3 列 / 宽档 5 列）按**它自己的宽度**切，不是按视口切。
   为什么不能用 @media：宿主右栏的宽度是业主自己拖的，与视口宽**没有关系**
   （1300 视口下 .ks-main 只有 820px，而 520 视口下它是 496px，都在同一个视口区间里）。
   ⚠ container-type:inline-size 只加"行内尺寸不依赖内容"的包含 ⇒ 它是 flex 项（flex:1 1 320px），
     宽度由 flex 行给，不受影响。 */
.ks-main{flex:1 1 320px;min-width:280px;display:flex;flex-direction:column;gap:var(--ks-space-2);
  min-height:0;container-type:inline-size}
.ks-detail{flex:0 1 232px;min-width:200px;display:flex;flex-direction:column;gap:var(--ks-space-2)}
/* ---------- 列表容器 + **真表格**（P1-2 建容器；P2 头条 2026-09-20 把它变成真表格） ----------
   改前：「.ks-item」 是 「.ks-main」 的**直接子元素**（DOM 里 4 个裸行），页面上量不到任何一条
   竖边 ⇒ 列表像散落的行而不是一个列表。P1-2 把「.ks-lhead」 与所有 「.ks-item」 包进这一层。
   P2 头条：表头从"全选 + 目录名 + 计数"改成**真列头行**（文件名 / 效力 / 生效日期 / 标签），
   每一行按同一份列定义排 —— 列宽的**唯一所有者**就是这里的 --ks-cols：

     ⚠⚠ **列模板只许有一处定义**（这是 P2 头条的验收口径）：表头与行都只写
        grid-template-columns:var(--ks-cols)，谁也不许再写一套列宽。
        渲染级证据在 ui-render-shot.mjs 的 #cols（真 Chrome 里量 header 与 row 的
        computed grid-template-columns，两者必须逐字相同）。
     列宽都落在 4px 网格上（72 / 80 / 132 / 36），未引入任何非网格值。
     窄档（宿主侧栏 520 ⇒ .ks-main 496px）：名称(2 行) | 效力 | ⋮ 三列。
     宽档（≥660px，1300 下 .ks-main = 820px）：再加**生效日期**与**标签**两列。
     ⚠ 窄档是"隐藏两列"，不是"删 DOM"：DOM 结构两个档**完全一样** ⇒ 渲染级冒烟
       （jsdom 不做布局、也不认 @container）量到的 cell 结构恒为 5 列，与真机一致。
     ⚠ 为什么窄档舍掉的是这两列：496px 里塞 5 列会把**名称**挤到 200px 以内，而行里最需要
       宽度的就是名称（P1-3 的验收就是"文件名不再被截断"）；效力是 20px 的徽章、信息密度最高，
       留下。参照的 1114px 才有资格摆 6 列。
   ⚠ 只包"列头 + 行"——空态卡、搜索框与批量条**不在**盒子里（空态是"这里没有行"，其余是浮层/控件）。
   ⚠ 描边走**宿主 elevation**（border:0 + box-shadow）——官方硬规则：描边不许与 elevation 配对
     （.ks-kb-card 已是同一写法）。发丝描边由阴影里的 --dsw-elevation-stroke 画。 */
.ks-list{--ks-col-status:72px;--ks-col-date:80px;--ks-col-tags:132px;--ks-col-more:36px;
  --ks-cols:minmax(0,1fr) var(--ks-col-status) var(--ks-col-more);
  border:0;border-radius:var(--ks-r-card);overflow:hidden;
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l2);
  background:var(--dsw-alias-bg-base);box-shadow:var(--dsw-elevation-soft)}
/* 窄档把这两列**藏起来**（DOM 还在，只是不占格）—— 与 --ks-cols 的三列模板配套。
   ⚠ 选择器写成 .ks-list .ks-cell.ks-col-*（0,3,0）：它必须压过下面
     「.ks-lhead .ks-cell{display:flex}」与「.ks-item .ks-col-tags」这两条 (0,2,0)；
     而它自己又要被**后面**那条 @container 覆盖 —— 所以它必须写在 @container **之前**
     （同权重时后者胜；第一版把顺序写反，实测宽档下两列仍然是 display:none）。 */
.ks-list .ks-cell.ks-col-date,.ks-list .ks-cell.ks-col-tags{display:none}
/* 宽档：5 列（名称 | 效力 | 生效日期 | 标签 | ⋮）。容器查询挂在 .ks-main 上（见上）。
   ⚠ 必须放在上面那条 display:none **之后**（同权重、靠源码顺序覆盖）。 */
@container (min-width:660px){
  .ks-list{--ks-cols:minmax(0,1fr) var(--ks-col-status) var(--ks-col-date) var(--ks-col-tags) var(--ks-col-more)}
  .ks-list .ks-cell.ks-col-date,.ks-list .ks-cell.ks-col-tags{display:flex}
}
/* 表格的两种行（列头行 / 数据行）**只共用这一条列模板**（全表唯一的一处
   grid-template-columns:var(--ks-cols)：别在下面任何一条规则里再写一遍）。 */
.ks-lhead,.ks-item{display:grid;grid-template-columns:var(--ks-cols);
  column-gap:var(--ks-space-2);align-items:center;box-sizing:border-box}
/* 列头行：全选 + 列名。⚠ P1-8（2026-09-20）消费了 --ks-head-h:40px（改前实测只有 33px，
   与 --ks-card-h 同类暗账）；少了 box-sizing 的话 min-height 只约束**内容盒**。
   底色踩过一个坑（P1-9b 实测）：先写 --dsw-alias-bg-layer-2、再写 layer-3，两个**都是白的**
   —— 本仓主题 light 下 layer-1/2/3 同值（全是 neutral-bluish-00 = #ffffff）⇒ 等于没有底色。
   ⇒ 用 --dsw-alias-markdown-tag（light = bluish-75 #f1f3f5、dark = bluish-850 #2c2c2e）。
   ⚠ 边界：light 下表头底与行底差 255→241 一档（可见但克制）；参照是 #f3f3f3（≈243）——
     同一量级，只是没抄他们的字面色。 */
.ks-lhead{min-height:var(--ks-head-h);padding:0 var(--ks-space-3);
  background:var(--dsw-alias-markdown-tag);border-bottom:var(--ks-stroke) solid var(--dsw-alias-border-l2);
  font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
/* 列表题头（目录名 + 计数）：P2 头条把它从 .ks-lhead 里**上移一行** ——
   表头变成"真列头行"之后，目录名再占着"文件名"那一格就会与列头抢位置。 */
.ks-list-cap{display:flex;align-items:center;gap:var(--ks-space-2);min-width:0}
.ks-lhead .ks-cell{display:flex;align-items:center;gap:var(--ks-space-2);min-width:0}
.ks-lhead-name{font-size:var(--ks-fs-base);font-weight:600;color:var(--dsw-alias-label-primary);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ks-lhead-col{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* 列表上方那个**真的会过滤**的搜索框（P2 头条）：宿主 Input（32px 高、自带描边与放大镜位）
   拉满整行宽。⚠ 它只是**本地列表过滤**（筛当前目录已加载的行），不是语料检索 ——
   一个接口都没调；与业主"知识库界面不做搜索"的关系见 KsKnowledgePage.tsx 顶部的翻案留痕。 */
.ks-search{display:flex;width:100%;min-width:0}
.ks-search>span{width:100%}
.ks-search input{font-size:var(--ks-fs-sm)}
/* 数据行（P1-1/P1-3 → **P2 头条 2026-09-20 改成真表格的一行**）：
   一行 = **5 个 cell**（与列头行同一份 COLUMNS 定义、同一条 --ks-cols 模板）：
     文件名（**两行**：名 + 标准号）| 效力 | 生效日期 | 标签 | ⋮
   改前是"两行自由布局"：第 1 行勾选框+文件名、第 2 行拼元数据 + 徽章（不是列对齐）。
   ⚠ 行高仍是 --ks-row-h-list（52px）：**不抄参照的 61px** —— 61 不在 4px 网格上，
     窄侧栏里还会把 4 行挤出一屏（weknora-ui-vs-ours §7.3/§7.4 已裁定）。
   ⚠ 正面约束**一条都没撤**（5b 修「详情」竖排折行的那组）：box-sizing:border-box +
     min-width:0 仍在；行尾触发器有 .ks-item-more{flex:none;white-space:nowrap}。
   ⚠ **"整行可点"没有做**（清单 P1-1 里那条建议，见 KsKnowledgePage.tsx 的同一段注释）。 */
.ks-item{padding:var(--ks-space-1) var(--ks-space-3);
  min-width:0;min-height:var(--ks-row-h-list)}
/* 行间 1px 分隔线（参照是"只在行间、没有竖分隔线"）。
   ⚠ 用 「+」 相邻兄弟：第一行不该有上分隔线（表头自己的 border-bottom 就是那条线）。 */
.ks-item + .ks-item{border-top:var(--ks-stroke) solid var(--dsw-alias-border-l1)}

/* ⚠ 行高口径（**历史，别删**）：5d 之前 .ks-item 是 content-box ⇒ min-height:44px 只约束
   内容盒，实测真实行高 52px、节距 60px，而文档/token 写 44 —— 暗账。第三轮加 box-sizing
   后实测 44/52。**P1-3（2026-09-20）改成两行结构后** token 换成 --ks-row-h-list:52px。
   **P2 头条**把两行结构收进"文件名"**一列**（第 2 行 = 标准号），行高仍由同一个 token 给。
   真实值以 ui-render-shot.mjs 的 measured 为准，写进 docs/UI-BASELINE.md —— 不许照 token 反推。
   ⚠ 注释里不许出现反引号（整段 CSS 是一个模板字符串）—— 已踩第七次。 */
.ks-item:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-item-on{background:var(--dsw-alias-interactive-bg-hover)}
/* 每个 cell 的公共约束：**不给宽度**（宽度归 --ks-cols 管），只保证不撑破列。
   ⚠ 这里刻意**不写 grid-template-columns**：列模板只有 .ks-list 上那一处。 */
.ks-cell{min-width:0;overflow:hidden}
/* 文件名列（两行）：
   第 1 行 = 文件图标(16px) + 勾选框(它的 label **就是**文件名，宿主原语，见下)
   第 2 行 = 标准号（真字段 no；法规没有号就按全站约定给破折号）
   ⚠ 图标只能在勾选框**之前**：名字与勾选框是**同一个元素**（Checkbox 的可见 label），
     插不进它们中间 —— 参照是 [勾选][图标][名字]，我们是 [图标][勾选+名字]。
   ⚠ 为什么这一格用**嵌套 grid 两行**（不是 flex-wrap）：第 2 行必须落在**名字那一段**的正下方
     （左缘与勾选框对齐，与 .ks-item-sub 的 grid-area:2/2 是同一个手法）。 */
.ks-item .ks-col-name{display:grid;grid-template-columns:16px minmax(0,1fr);
  column-gap:var(--ks-space-2);row-gap:0;align-items:center}
.ks-fileico{grid-area:1/1;grid-row:1/3;display:inline-flex;align-items:center;justify-content:center;
  width:16px;height:16px;color:var(--dsw-alias-label-tertiary)}
/* 第 1 行：勾选框 + 文件名。
   ⚠ 宿主 Checkbox 的 label **一定是可见文字**（Checkbox.tsx 原文："localized visible and
     accessible label"，DOM 是 <label class=checkbox><input><span>文字</span></label>）
     ⇒ 文件名就交给它渲染（它天然带省略号能力）。但**文字那层 span 是宿主的**，样式改不动
     （CSS Module 哈希类，只声明不了），所以文件名先用我们自己的一层包着：
     .ks-check > span（宿主的可见文字层）里再放我们的字号/颜色。
   ⚠ **整行可点：未做（不是做不了）** —— 2026-09-20 复核打回更正（B6）：可见 label 只否掉了
     "整行无差别再吃一次 click"这一种写法（会与点勾选框打架）；正当做法至少三条：
     ① 行 onClick + event.target.closest('label,input,button') 排除；② onClick 只绑文件名那一列；
     ③ Checkbox 传 sr-only label + 独立的文件名元素（③ 宿主是否支持 sr-only label **未核**）。
     本轮未做、理由与代价见 docs/UI-BASELINE.md 5f 三处留痕第 1 条；已登记 P2
     （docs/research/weknora-ui-vs-ours.md §8.1 的 P2-2）。 */
.ks-item .ks-check{grid-area:1/2;min-width:0}
.ks-item .ks-check>span{display:block;flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  color:var(--dsw-alias-label-primary);font-size:var(--ks-fs-md);line-height:1.4}
.ks-item .ks-check>input{margin-top:2px}
/* 第 2 行（.ks-item-sub）：标准号（12px tertiary），落在**文件名那一段**的正下方。 */
.ks-item-sub{grid-area:2/2;display:flex;align-items:center;gap:var(--ks-space-2);
  min-width:0;flex-wrap:nowrap}
.ks-item-meta{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-tertiary)}
/* 效力列 / 生效日期列 / 标签列（宽档才显示后两列，见 .ks-list 的容器查询） */
.ks-item .ks-col-status{display:flex;align-items:center}
.ks-item .ks-col-date{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary)}
/* 标签列 = **行内可见的 chip**（P2 头条）：只展示，不是控件（理由见 KsKnowledgePage.tsx
   的 tags 分支：做成 button 会把行内可见控件从 3 提到 4，而"≤3"是真控件口径的真护栏）。
   nowrap + overflow:hidden 保证它**永不折行**（列宽由 --ks-cols 钉死）。
   ⚠ 这里**不写 display**：显示/隐藏由上面 .ks-list 的窄/宽档唯一决定（写了会与它抢，
     同权重靠顺序 —— 那个坑在本文件里已经踩过）。 */
.ks-item .ks-col-tags{align-items:center;gap:var(--ks-space-1);
  flex-wrap:nowrap;overflow:hidden}
/* 状态徽章（P1-5，2026-09-20）：从**实心 Tag** 改成"浅底 + 1px 描边 + 同色系文字"。
   改前：宿主 Tag(success) 量到 **37×13** 的实心块（底色 #e8f9ef、字 #22c55e、**没有描边**）；
   参照真机 「23-kb-detail-list-1440.png」 是 **46×20**、浅底 + 1px 描边 + 同色字（§7.1 的 scan 线
   在徽章左右各量到一条 1px 的 state 色列）。
   ⇒ 高度 13 → 20（--ks-space-5），描边 1px（--ks-stroke，**不是** --ks-sep：验收要量到那 1px）。
   色调全部由调用方挂修饰类给（.ks-status-ok / -warn / -bad），与 .ks-kb-badge-* 同一套语义；
   **一个字面色值都没有**（描边+文字=state-*-primary，底色=state-*-tertiary/secondary）。 */
.ks-status{flex:none;display:inline-flex;align-items:center;box-sizing:border-box;
  height:var(--ks-space-5);padding:0 var(--ks-space-2);border:var(--ks-stroke) solid;
  border-radius:var(--ks-r-sm);font-size:var(--ks-fs-sm);font-weight:600;white-space:nowrap}
.ks-status-ok{background:var(--dsw-alias-state-success-tertiary);color:var(--dsw-alias-state-success-primary);
  border-color:var(--dsw-alias-state-success-primary)}
.ks-status-warn{background:var(--dsw-alias-state-warn-tertiary);color:var(--dsw-alias-state-warn-label);
  border-color:var(--dsw-alias-state-warn-label)}
.ks-status-bad{background:var(--dsw-alias-state-error-secondary);color:var(--dsw-alias-state-error-primary);
  border-color:var(--dsw-alias-state-error-primary)}
/* 「被替代」这一档没有专属状态色（参照也没有第四档）⇒ 走**中性档**：与另外三档**同形**
   （同高、同 1px 描边、同圆角），只差色调 —— 这样四个徽章并排时"形"是齐的。 */
.ks-status-neutral{background:var(--dsw-alias-markdown-tag);color:var(--dsw-alias-label-secondary);
  border-color:var(--dsw-alias-border-l4)}
/* 标签（行内/详情里共用）：与状态徽章同高同形（浅底 + 1px 描边 + 中性色）——照 .ks-status 的形状，
   颜色走中性档（border-l2 + label-secondary）。 */
.ks-tag{flex:none;display:inline-flex;align-items:center;box-sizing:border-box;
  height:var(--ks-space-5);padding:0 var(--ks-space-2);
  border:var(--ks-stroke) solid var(--dsw-alias-border-l2);border-radius:var(--ks-r-sm);
  background:var(--dsw-alias-markdown-tag);color:var(--dsw-alias-label-secondary);font-size:var(--ks-fs-xs)}
/* 行尾溢出菜单（P1-1，2026-09-20）：原来「＋标签」与「详情」是两个**常驻**行内按钮
   （一行里 5 个可见控件）。现在收进这里，触发器只留一个「⋮」。
   ⚠ P2 头条（2026-09-20）后它住在**表格的最后一列**（.ks-col-more，36px）里 ⇒
     grid-area 不再需要（列位置由 COLUMNS 的顺序给），改为把触发器推到该列右缘。
   ⚠ flex:none + white-space:nowrap 是 5b 那组"永不压缩、永不折字"的正面约束**原样搬过来**
     （当时修的是「详情」被压成「详／情」竖排）。 */
.ks-item-more{display:inline-flex;align-items:center;flex:none;white-space:nowrap}
.ks-item .ks-col-more{display:flex;align-items:center;justify-content:flex-end}
/* 触发器钉 --ks-btn-h-sm(24px)：宿主 size=sm 的 28px 会**顶高整个第一行**（grid 的 auto 行）
   ⇒ 行高被撑到 64px。24px 正好落在 52px 的行高预算里（28 + 20 + 上下 4 = 52）。
   ⚠ 与 .ks-batch-btn 同一个 token，同一份理由（"宿主档位被内容撑大"），不是新拍的数。 */
.ks-item-more button{height:var(--ks-btn-h-sm)}
/* 悬浮批量条（有选中才出现）。
   ⚠ 官方硬规则：「Elevated surfaces … set "border: 0" and take "box-shadow:
   var(--dsw-elevation-panel|prominent|soft)". **Never pair a --dsw-alias-border-*
   border with an lv/elevation shadow**」—— 描边由阴影自己画，颜色用
   --dsw-elevation-stroke-color 给（官方 stat-dialog.module.css:21-25 就是这个写法）。
   我第一版写成 "border:.5px solid var(--dsw-alias-border-l4)" + 阴影，属于明令禁止的配对。
   ⚠ 这里**不能写反引号**：整段 CSS 是一个模板字符串，反引号会把它截断（本轮第三次踩）。
   ⚠ P1-6（2026-09-20）：从**通栏 sticky** 改成**居中限宽** —— 参照真机
     「24-kb-detail-batchbar-1440.png」 是 330×46 的**居中**白条，我们原来是 496 通栏
     （measured: x=12 w=496）。改法只是 width:fit-content + margin 左右 auto：
     「border:0」 与 elevation **照旧不动**（官方禁止"中性描边 + elevation"配对，
     不许为了更像参照而加描边）；危险动作仍是 error 色**文字**（.ks-batch .ks-danger），不是红底。
     按钮高度：宿主 Button size=sm 在这一格被 align-items:center + 图标撑到 **28px**
     （measured .ks-item-btn.btnH=28）—— 由 .ks-batch-btn 显式钉 --ks-btn-h-sm(24px)。 */
.ks-batch{position:sticky;bottom:0;display:flex;align-items:center;gap:var(--ks-space-2);flex-wrap:wrap;
  width:fit-content;max-width:100%;margin:var(--ks-space-2) auto 0;
  padding:var(--ks-space-2) var(--ks-space-3);border:0;
  border-radius:var(--ks-r-card);
  background:var(--dsw-specific-menu);
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l1);
  box-shadow:var(--dsw-elevation-prominent)}
.ks-batch-btn{height:var(--ks-btn-h-sm);min-height:var(--ks-btn-h-sm)}
.ks-batch-n{font-size:var(--ks-fs-sm);font-weight:600}
/* 危险动作（批量删除）的文字色：走宿主 state-error（**参照里也是红字**）。
   ⚠ 选择器写成 .ks-batch .ks-danger（0,2,0）：宿主的 Button CSS Module 类也是 (0,1,0)，
     同权重时"谁在后面谁赢"不可控 ⇒ 必须靠权重压过去，不能靠插入顺序。 */
.ks-batch .ks-danger{color:var(--dsw-alias-state-error-primary)}
/* 详情字段：日期这一类 label/value 成对 */
.ks-fields{display:flex;flex-direction:column;gap:var(--ks-space-1)}
.ks-field{display:flex;gap:var(--ks-space-2);font-size:var(--ks-fs-sm);line-height:1.5}
.ks-field-k{flex:0 0 62px;color:var(--dsw-alias-label-tertiary)}
.ks-field-v{flex:1;min-width:0;color:var(--dsw-alias-label-primary);word-break:break-word}
.ks-field-v-mono{font-family:ui-monospace,Consolas,monospace}
/* 页内二级 tab（文件 / 标签） */
.ks-subtabs{display:flex;align-items:center;gap:var(--ks-space-2);flex-wrap:wrap}
/* ---------- 筛选/切换：一排**等高胶囊**（P1-4，2026-09-20） ----------
   参照真机 「22-kb-detail-1440.png」 / 「23-kb-detail-list-1440.png」 是一排 **5 个 140×32 等高胶囊**
   （图标 + 文案 + ∨，间距 12px，底 #f3f3f3）；我们页内原来只有两个 Pill（文件/标签），
   筛选**根本不存在**，行内筛选件还各是一套高度（.ks-ing-chip ≈24px）。
   ⇒ 这一档统一成：**高 32px（--ks-space-8）+ 字号 12px（--ks-fs-sm）+ 水平间距 12px（--ks-space-3）**
     + 图标位固定（gap 4px）。
   ⚠ 底色**不抄**参照的 #f3f3f3：走宿主 interactive 档（hover/selected），深浅色自动跟随。
   ⚠ 胶囊形（999px）配 corner-shape:round —— 官方硬规则（见 .ks-dot 的注释）。 */
.ks-filters{display:flex;align-items:center;gap:var(--ks-space-3);flex-wrap:wrap;
  font-size:var(--ks-fs-sm)}
.ks-chip{display:inline-flex;align-items:center;gap:var(--ks-space-1);box-sizing:border-box;
  height:var(--ks-space-8);padding:0 var(--ks-space-3);
  border:0;border-radius:var(--ks-r-pill);corner-shape:round;
  background:var(--dsw-alias-interactive-bg-hover);
  font-size:var(--ks-fs-sm);font-family:inherit;line-height:1;color:var(--dsw-alias-label-primary);
  cursor:pointer}
.ks-chip:hover{background:var(--dsw-alias-interactive-bg-active)}
.ks-chip-on{background:var(--dsw-alias-interactive-bg-active);font-weight:600}
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
/* ---------- 空态卡（P0-5，2026-09-20）：把"一句话居中灰字"升级成分层空态 ----------
   照 WeKnora EmptyState：30px 图标装在 **64px 圆**里 + 标题 + 描述（限宽 360）+ 可选主按钮。
   ⚠ 标题用 --ks-fs-lg(16px) 而不是参照的 15px：15 不在我们的受限字号表里（见 :root），
     为"逐字像参照"把 15px 塞回来正是这份 UI 基线明令禁止的（尺度表要成体系）。
   圆点必须配 corner-shape:round（官方 web-styling 的硬规则，见 .ks-dot 的注释）。 */
.ks-empty-card{display:flex;flex-direction:column;align-items:center;gap:var(--ks-space-2);
  padding:var(--ks-space-8) var(--ks-space-4);text-align:center}
.ks-empty-ico{display:flex;align-items:center;justify-content:center;width:64px;height:64px;
  border-radius:50%;corner-shape:round;background:var(--dsw-alias-bg-layer-3);color:var(--dsw-alias-label-tertiary)}
.ks-empty-t{font-size:var(--ks-fs-lg);font-weight:600}
.ks-empty-d{max-width:360px;font-size:var(--ks-fs-base);line-height:1.5;color:var(--dsw-alias-label-secondary)}
/* ⚠ corner-shape:round 是**必须的配对**：官方 docs/web-styling.md「Pair "corner-shape: round"
   with every full-round "border-radius" ("50%", "100%", or a pill radius) so circles and capsules
   keep circular arcs」—— 少了它，支持 superellipse 的 Chromium 上圆点会被压成方角。
   （本行刻意不用反引号：整段 CSS 是一个模板字符串，反引号会把它截断——本轮已踩过 4 次。） */
.ks-dot{flex:none;width:6px;height:6px;border-radius:50%;corner-shape:round;
  background:var(--dsw-alias-label-caption)}

/* ---------- 能力页（一功能一卡一窗） ---------- */
.ks-cap-card{box-sizing:border-box;display:flex;flex-direction:column;gap:var(--ks-space-1);
  border:0;border-radius:var(--ks-r-card);padding:var(--ks-space-3);
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l2);
  background:var(--dsw-alias-bg-base);box-shadow:var(--dsw-elevation-soft);
  transition:box-shadow var(--ks-dur-fast)}
.ks-cap-card:hover{--dsw-elevation-stroke-color:var(--dsw-alias-border-l4);
  box-shadow:var(--dsw-elevation-panel)}
/* 补位卡（P0-5）：把每组卡的**末行补满**（照 WeKnora skill-catalog 那张虚线「＋」）。
   ⚠ 关键是 grid-column-end:-1 —— **负行号数的是显式网格的最后一条列线**，而 repeat(auto-fill,…)
     生成的轨道**就是**显式网格 ⇒ 这张卡自动"从下一个空位铺到本行末尾"。于是列数由 CSS 自己算，
     2 列/3 列/5 列都铺满，不必让 JS 去量列宽（本仓的离屏渲染器跑在 jsdom 里，没有 ResizeObserver
     也量不出 grid-template-columns ⇒ 任何"JS 量列数"的写法在截图里都看不见、无法自检）。
   它只占位、不可点（后端未接，做一个假按钮更糟）⇒ aria-hidden + title 说明。
   高度由 .ks-kb-cards>*{min-height:var(--ks-card-h)} 与 grid 的 stretch 保证与同排卡齐平。 */
.ks-cap-card-add{grid-column:auto / -1;box-sizing:border-box;display:flex;align-items:center;justify-content:center;
  gap:var(--ks-space-2);border:var(--ks-sep) dashed var(--dsw-alias-border-l4);border-radius:var(--ks-r-card);
  color:var(--dsw-alias-label-tertiary);font-size:var(--ks-fs-sm)}
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
