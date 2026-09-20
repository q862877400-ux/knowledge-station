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
  /* 卡片带左右**翻页箭头**的方框边长（5h，2026-09-20）。24px = 与 .ks-batch-btn /
     .ks-item-more button 同一个档位（--ks-btn-h-sm），只是这里要的是**宽高都钉死**的方框
     —— 业主今天要"一个小框下面自带一个左右翻页滑动条"，箭头宽度就是那条滑动条的实测口径。
     ⚠ 为什么不直接用 --ks-btn-h-sm 当宽度：那个名字是"按钮高"，借用它表达宽度正是本仓
       反复抓过的"语义漂移"（后来者会以为它俩永远同值）。单开一个名字，值同档。 */
  --ks-band-nav:24px;
  /* 卡片带上**一张卡的固定宽度**（5h-补，2026-09-20）。172px 是"上一版在 1300 下量到的卡宽"
     —— 宽屏框 max-width:720px、5 张卡要能横着滑，卡宽不能跟着容器走（那就是窗口切片了）。
     ⚠ 与 --ks-card-gap(12) 一起决定**一条带的总宽 = 5×172 + 4×12 = 908px** ⇒ 在任何
        ≤720px 的框里都溢出 ⇒ 滚动条必然出现（这是"滑动条"能被看见的前提，不是巧合）。
     ⚠ JS 侧 BAND_STEP_PX = 184（卡宽 + gap）是它的**数值镜像**，只用于 scrollBy 的步长；
        "每屏几张"这个概念已经**不存在**了（上一版正是它与 CSS 两处耦合）。 */
  --ks-band-card-w:172px;
  /* 页面留边（**内容与窗口/面板边缘**的留边；与上面那组"元素之间"的 --ks-space-* 是两件事）。
     ⚠ 5j（2026-09-20）新增 —— **这是补一个规范缺口，不是"一直都有"**：第二节此前只定义了
       元素**之间**的间距与元素**内部**的内边距，**从没定义过"页面内容离窗口边缘多远"**
       ⇒ 每个页面根各自决定留不留（实测改前：页面根 0px，卡片带/表格/批量条全部贴到边缘）。
       业主原话与去向见 UI-BASELINE 第二节同名一段 + 第六节 5j。
     值：窄档 16 / 宽档 24（都在 4px 网格上；竖向同两档）。
     ⚠ 窄档为什么不再大：520 的栏里 .ks-main 最小宽 280 + .ks-detail 最小宽 200 + 间距 8 = 488
       = 520 − 2×16；留 20 就会把它们挤成两行（可用宽 = 页面根宽 − 2×留边）。
     ⚠ 为什么不是参照的 28/32：那是 WeKnora 1440 全宽文档页的数（实测出处见第二节），
       我们的窄档只有 520。 */
  --ks-page-pad-x-narrow:16px; --ks-page-pad-x-wide:24px;
  --ks-page-pad-y-narrow:16px; --ks-page-pad-y-wide:24px;
  --ks-page-pad-x:var(--ks-page-pad-x-narrow);
  --ks-page-pad-y:var(--ks-page-pad-y-narrow);
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
/* ---------- 5h（2026-09-20）**卡片带**：一个框 + 左右翻页箭头 ----------
   业主原话：「**所有卡片横在顶端**」「**一个小框下面自带一个左右翻页滑动条**」。
   ⚠ 树的样式（.ks-kb-tree / .ks-kb-tline / .ks-kb-tw / .ks-kb-tn）与 .ks-rail **已删**：
     业主说"不要展示目录树"、"我建的（真文件夹；与上面两棵平级）这种乱七八糟东西删了" ——
     删了什么、为什么写在 docs/UI-BASELINE.md 5h。
   ⚠ 框宽 max-width:720px（= 180 个 4px 单位）：业主说的是"一个**小**框"，不是通栏。
   ⚠ 5h-补（2026-09-20）后**卡宽与框宽脱钩**：卡固定 --ks-band-card-w(172)，框内能同时看到几张
     由框宽决定（宽屏 720 的框里约 3 张 + 半点露头，窄屏 520 里约 2 张）—— 这正是"能滑"的观感；
     上一版那句"宽屏 3 张各约 202px / 窄屏各缩到约 130px"是**窗口切片**年代的话，已作废。
   ⚠ 本段是模板字符串里的一段 CSS：注释里**不许出现反引号**（会截断模板）—— 这里踩过第 8 次。 */
.ks-kbband{display:flex;align-items:center;gap:var(--ks-space-2);box-sizing:border-box;
  max-width:720px;padding:var(--ks-space-2);
  border:0;border-radius:var(--ks-r-card);
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l2);
  background:var(--dsw-alias-bg-base);box-shadow:var(--dsw-elevation-soft)}
/* 窗口：**卡片带的可视区**（宽度由框减去两个箭头与间距给）。 */
.ks-kbband-clip{flex:1;min-width:0;
  overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;
  scrollbar-width:thin;scrollbar-color:var(--dsw-alias-scrollbar-bg-l1) transparent}
/* ⚠ **滚动条可见性**：这里**不自己画滚动条**（不写 height/background）—— 宿主的
   ui-theme/src/styles/scrollbar.css 已经全局给 ::-webkit-scrollbar 8px 宽 +
   --dsw-alias-scrollbar-* 拇指色；@supports not selector(::-webkit-scrollbar) 那一支
   （Firefox）才落到上面那条 scrollbar-width:thin。两条路互斥、不是两套并存。
   这里只补一件事：overflow-x:auto ⇒ 内容一溢出，那条**原生**滚动条就出现，
   且深浅两套配色走宿主 token（自己画 = 第二套色值，上一版就是这么被点名的）。 */
/* 键盘可达：容器自己有 tabIndex=0（见 KsKnowledgePage.tsx），聚焦环也走宿主 border 档。 */
.ks-kbband-clip:focus-visible{outline:var(--ks-stroke) solid var(--dsw-alias-border-l4);
  outline-offset:calc(-1 * var(--ks-space-1))}
/* 卡宽**只在这里定义一处**：上一版是 BAND_WINDOW=3 常量 + repeat(3,…) 两处耦合
   （改一处忘另一处就错位）⇒ 本轮把"每屏几张"彻底从 CSS 里去掉，换成**固定卡宽**。
   不伸不缩（flex:0 0）⇒ 同排**等宽**；容器 align-items:stretch ⇒ 同排**等高**
   （.ks-kb-cards>*{min-height:var(--ks-card-h)} 仍兜底）。
   ⚠ .ks-kbband .ks-kb-cards 现在是**横向 flex 容器**，不再是网格。 */
.ks-kbband .ks-kb-cards{display:flex;flex-direction:row;align-items:stretch;gap:var(--ks-card-gap);
  width:max-content}
/* 箭头：24px 方框（--ks-band-nav），走宿主 interactive 档；到头/到尾 disabled ⇒ 置灰。 */
.ks-kbband-nav{flex:none;display:inline-flex;align-items:center;justify-content:center;box-sizing:border-box;
  width:var(--ks-band-nav);height:var(--ks-band-nav);padding:0;border:0;border-radius:var(--ks-r-md);
  background:var(--dsw-alias-interactive-bg-hover);color:var(--dsw-alias-label-secondary);cursor:pointer}
.ks-kbband-nav:hover:enabled{background:var(--dsw-alias-interactive-bg-active)}
.ks-kbband-nav:disabled{background:transparent;color:var(--dsw-alias-label-caption);cursor:default}
/* 卡片带上的一张卡：卡面样式仍归 .ks-kb-card（与详情里的占位卡同一份），这里只补
   "它现在是个 button"要清零的原生外观 + 选中态（选中 = 当前正在看的那张库卡）。
   ⚠ 选中态走宿主 interactive-bg-active（与 .ks-chip-on 同一档），**不新增色值**。
   ⚠⚠ **卡宽只有这一处定义**（5h-补 2026-09-20）：flex:0 0 var(--ks-band-card-w) + 不写 width。
      原来这里写的是 width:100% —— 那是"跟着窗口等比缩"的年代（每屏恒 3 张）；现在卡宽钉死，
      一条卡片带的总宽 = 5 × 卡宽 + 4 × gap > 容器宽 ⇒ 滚动条**必然**出现（实测值见 5h 的
      #kbband）。scroll-snap-align:start 与它同一条规则：卡宽与吸附点天生是同一件事。 */
.ks-kbband .ks-kb-card{flex:0 0 var(--ks-band-card-w);scroll-snap-align:start;
  font:inherit;text-align:left;color:inherit;cursor:pointer}
.ks-kbband .ks-kb-card[data-on='true']{--dsw-elevation-stroke-color:var(--dsw-alias-border-l4);
  background:var(--dsw-alias-interactive-bg-active)}
/* ---------- 5h：面包屑 + 「返回上一级」 + 目录层 ---------- */
/* 面包屑行：左边是返回按钮（只在 path.length>0 时渲染），中间是当前路径，右边是计数。
   ⚠ 路径用**节点名**（不是 key）—— 见 KsKnowledgePage.tsx 的 pathNames 注释。
   ⚠⚠ **2026-09-20 头条：路径改成"每一级都能点"**（业主：「这种路径要每一级都能点击跳转」）。
      结构：外层 .ks-crumb-path 里是「条目 / 分隔符 / 条目 / …」——.ks-crumb-item（一级一个）
      + .ks-crumb-sep（斜杠，**与条目是兄弟**，见 KsKnowledgePage.tsx 的同名注释）；
      条目内部要么是可点的 .ks-crumb-go（button），要么是**当前级**的 .ks-crumb-here（span）。
      **收敛口径不变**：整条仍是 nowrap flex，条目 flex:0 1 auto（可缩）+ .ks-crumb 的
      overflow:hidden ⇒ 窄窗（520）下尾巴被裁掉，不会把行撑破；条目自己还有
      text-overflow:ellipsis（长目录名被压缩时给省略号）。
      ⚠ 为什么条目**必须可缩**（不能 flex:none）：不可缩的话整条宽度就是各段之和，
        520 档下它会把右侧的 .ks-crumb-n（"N 个子目录"）挤出可视区（那正是下面这条注释
        记的坑：长面包屑把计数挤到第二行、图上"4"和"篇"分家）。 */
.ks-crumb{display:flex;align-items:center;gap:var(--ks-space-2);min-width:0}
.ks-crumb-path{display:flex;align-items:center;min-width:0;overflow:hidden;
  font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
.ks-crumb-item{display:inline-flex;align-items:center;flex:0 1 auto;min-width:0}
.ks-crumb-sep{flex:none;color:var(--dsw-alias-label-caption);padding:0 var(--ks-space-1)}
/* 可点的那几级：**把 button 打回文字**（透明底 / 零内边距 / 继承字号色）——它长得像路径文本，
   但仍然是个真 button（Tab 可达、Enter/Space 可激活、aria-label 有话说）。
   hover 与文件行同档：宿主 interactive-bg-hover 当底（**不新造色值**）+ label-secondary 提亮。
   ⚠ text-decoration:none 不能省：button 在部分 UA 样式表里会带下划线。 */
.ks-crumb-go{flex:0 1 auto;min-width:0;border:0;background:transparent;padding:0;margin:0;
  font:inherit;color:inherit;cursor:pointer;text-decoration:none;border-radius:var(--ks-r-sm);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ks-crumb-go:hover{background:var(--dsw-alias-interactive-bg-hover);color:var(--dsw-alias-label-secondary)}
.ks-crumb-go:focus-visible{outline:var(--ks-stroke) solid var(--dsw-alias-border-l4);outline-offset:1px}
/* 当前所在那一级：**不可点**（它是 span，不是 disabled button）。
   为了"看得出在哪"：文字用 label-secondary（比其余级的 tertiary 重一档）、去掉所有可点的
   视觉线索（cursor:default + 不给 hover 底）。 */
.ks-crumb-here{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  color:var(--dsw-alias-label-secondary);cursor:default}
/* 目录层的"N 个子目录"：**必须 nowrap + flex:none** —— 第一版用的是 .ks-kb-hint（可压缩），
   长面包屑（四级的"标准 / P 土木、建筑 / P15/19… / P16 工程防火"）会把它挤到第二行，
   图上就是"4"和"篇"分家（520/1300 两张图里都看得到）。 */
.ks-crumb-n{flex:none;white-space:nowrap;font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
.ks-back{flex:none}
/* 目录层的容器：**沿用 .ks-list 这一套**（JSX 里的类是 ks-list / ks-list-dirs / ks-dirs）。
   ⚠ 这里原来是一条**卡片网格**（display:grid + repeat(auto-fill,minmax(220px,1fr))）；
   2026-09-20 头条把它换成**与文件列表同构的列表** ⇒ 旧网格声明**已删**（留着会与下面
   .ks-list-dirs 的 display:block 打架、也让"目录层到底是什么形状"出现两个所有者）。
   ⚠ .ks-dirs 这个类**刻意留在容器上**：它被三处外部锚点**按名**引用，且那三处要求逐字一致
     （ui-render-shot.mjs 的 #kspad 留边适用面与 PAD_SUBJECTS_ALL、smoke-kb-pad-pixels.mjs 的
     SPEC_SUBJECTS）⇒ 改名会同时打断那三处。它现在**只是这个容器的第二个名字**，
     几何一律由 .ks-list-dirs 给（见 .ks-list 那一段）。
   ⚠ .ks-dir-name 也不是死笔名：目录行的名字元素仍用它（见 .ks-list-dirs 那一段的覆盖）。
   ⚠ 这一条**只剩注释、没有声明**：容器的旧网格声明已删、新几何全在 .ks-list-dirs 那一条
     （写在这里只会多一个所有者）。留注释是为了让"这个类还在、别删"这件事有出处。 */
.ks-kb-sec{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary);margin-top:var(--ks-space-1)}
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

/* ---------- 知识库页（5h 起）：**文件列表 | 详情** 两段式 ---------- */
/* 一列放不下就换行：右栏宽度是业主自己拖的，不许假设它有多宽。
   ⚠ 5h 删掉了第三段「目录轨」（.ks-rail）—— 目录改成卡片带下面的**目录层**（.ks-dirs），
     不再占列表左边那一列（业主："不要展示目录树"）。.ks-split 本身没变（它只管换行）。 */
.ks-split{display:flex;gap:var(--ks-space-2);align-items:flex-start;flex-wrap:wrap;min-height:0}
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

/* ══════════ 目录层 = **与文件列表同构的列表**（2026-09-20 头条） ══════════
   业主原话：「把子目录文件夹的视图，做成和文件列表一样的视图」「这种路径要每一级都能点击跳转」。
   容器 / 表头 / 行**复用文件列表那一套类**（JSX 里的类是 ks-list + ks-list-dirs + ks-dirs、
   ks-lhead、ks-item + ks-dir-row），这里只做**目录层自己的两件事**：
     ① 一条**自己的** --ks-cols（同一机制、不同列数：3 列 —— 目录 / 篇数 / 进入提示）；
     ② 旧表单的**卡片外观覆盖**（.ks-list 的 elevation 白底盒、.ks-item 的行为都是为文件行定的）。
   ⚠ 列**宽度**的所有者仍然只有一处：**这条** --ks-cols。.ks-lhead / .ks-item 上照旧只写
     grid-template-columns:var(--ks-cols)（上面那一条），谁也不许再写一套列宽 ——
     与文件层同一条纪律（P2 头条的验收口径）。
   ⚠ 为什么要有 --ks-col-dcount / --ks-col-dgo 这两个中间变量：与文件层 --ks-col-more
     等**同一种写法**（列宽进变量、模板只引用变量）。值都在 4px 网格上（64/16）。
   ⚠ **别把 .ks-list-dirs 写成 .ks-dirs**：.ks-dirs 只是容器的旧名字（三处外部锚点按名引用它，
     见上面那一段注释），**几何归 .ks-list-dirs**。两者在 JSX 里同时挂在同一个 div 上。
   ⚠ 本段注释里**一个反引号都没有**（整段 CSS 在模板字符串里；反引号会截断它 ——
     本批实测踩到过一次：被截断后 .ks-list-dirs 的规则整段没进产物，列对齐自检当场红）。 */
.ks-list-dirs{--ks-col-dcount:64px;--ks-col-dgo:16px;
  --ks-cols:minmax(0,1fr) var(--ks-col-dcount) var(--ks-col-dgo);
  display:block;background:transparent;box-shadow:none;
  --dsw-elevation-stroke-color:transparent}
/* 目录行本身是个 **button**（整行可点 + 键盘可达：Tab 聚焦、Enter/Space 激活）。
   ⚠ 要打回"一行列表项"的样子：原生 button 的 font/text-align/color 都得清零，
     底色/描边清零（默认按钮外观一律不许冒出来）。
   ⚠ 行高与文件行**同一个 token**（--ks-row-h-list，52px）—— "和文件列表一样的视图"最硬的一条：
     两层行高逐像素一致（第一列也是**两行**：目录名 + 整条路径，手法同文件层的名字 + 标准号：
     都用 .ks-item-sub + grid-area:2/2）。
   ⚠ 这里**不写** border / padding（padding 由共享的 .ks-item 给，两条同权重、靠源码顺序叠加）。
   ⚠⚠ **width:100% 是必须的，不是保险**（本批真 Chrome 实测到的坑，正是列对齐自检抓出来的）：
     .ks-item 是 div 时（文件行）作为块级盒**自动铺满**容器宽；换成 button（目录行）之后它是
     **shrink-to-fit**（宽度 = 内容 max-content 之和）⇒ 实测**行宽只有 346px**（容器 1276px），
     而 minmax(0,1fr) 那一列跟着塌到 206.328px ⇒ 同一层里出现**表头 1152px / 行 206.328px**
     这种"同一条模板解出两个值"的假象（ui-render-shot 的 #cols 报的正是它）。
     ⇒ 整行可点改成 button 之后，**必须显式给满宽**。
     ⚠ 用 width:100% 而不是 align-self:stretch：这一层容器是 .ks-list-dirs{display:block}
       （原卡片网格的 grid 已删）⇒ button 是**块级**子盒，100% = 容器内容宽，
       与文件层的 div 行同宽（两层的行对齐口径因此完全一致）。 */
.ks-list-dirs .ks-item{width:100%;font:inherit;text-align:left;color:var(--dsw-alias-label-primary);
  background:transparent;border:0;cursor:pointer;text-decoration:none}
.ks-list-dirs .ks-item:hover{background:var(--dsw-alias-interactive-bg-hover)}
/* 焦点环用 **inset** box-shadow（不是 outline）：容器是 overflow:hidden，外扩的环会被裁掉。 */
.ks-list-dirs .ks-item:focus-visible{outline:none;
  box-shadow:inset 0 0 0 var(--ks-stroke) var(--dsw-alias-border-l4)}
/* 目录名那一列：**嵌套 grid 两行**（第 1 行图标 + 名字，第 2 行整条路径）——与文件层的
   .ks-item .ks-col-name 同一种手法（那里是 16px 图标列 + 名字 / 标准号两行）。
   ⚠ 为什么第 2 行给路径：目录名在**同名的兄弟层**里认不出来（两个「宪法与行政法」分属
     法律 / 行政法规两支）⇒ 整条 key 是唯一的消歧锚（与文件层第 2 行给标准号同一个理由：
     那一行放的都是"这一行的真身份"，不是编出来的描述）。 */
.ks-list-dirs .ks-cell.ks-col-dname{display:grid;grid-template-columns:16px minmax(0,1fr);
  column-gap:var(--ks-space-2);row-gap:0;align-items:center}
/* 目录名（名字那一格）：font-weight:600 —— 原来卡片上的名字就是这个字重（搬家不换样式）。
   ⚠ 这里把旧规则里的 flex:1 **去掉了**：新容器是 grid 单元格，flex 在它上面是死声明
     （留着会让人以为宽度归它管，而宽度归 --ks-cols）。 */
.ks-list-dirs .ks-dir-name{grid-area:1/2;min-width:0;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;font-size:var(--ks-fs-base);font-weight:600}
/* 篇数列 + 进入提示列：与文件层的 .ks-col-status / .ks-col-more 同一档（居中 / 靠右）。
   ⚠ .ks-kb-badge 是 flex:none 的胶囊（卡片上原来是它），放进 grid 单元格里没问题。 */
.ks-list-dirs .ks-cell.ks-col-dcount{display:flex;align-items:center;gap:var(--ks-space-2);min-width:0}
.ks-list-dirs .ks-cell.ks-col-dgo{display:flex;align-items:center;justify-content:flex-end}
.ks-dir-go{display:inline-flex;align-items:center;color:var(--dsw-alias-label-tertiary)}
.ks-list-dirs .ks-item:hover .ks-dir-go{color:var(--dsw-alias-label-secondary)}
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
   拉满整行宽。⚠ 它只是**本地列表过滤**（筛当前层已加载的条目），不是语料检索 ——
   一个接口都没调；与业主"知识库界面不做搜索"的关系见 KsKnowledgePage.tsx 顶部的翻案留痕。
   ⚠ 5i（2026-09-20 收尾批）：这个框现在**每一层都渲染**（目录层过滤目录名），样式**一字未改** ——
     两处渲染点（文件层 .ks-main 内、目录层 .ks-dirs 之前）都靠 width:100% 拉满那一层。 */
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
   **一个字面色值都没有**（描边+文字=state-*-primary，底色=state-*-tertiary/secondary）。
   ⚠⚠ **2026-09-20 P2 复核打回（A）：上面这句"底色=state-*-tertiary/secondary"就是缺陷本身。**
      **曾如此（错的）**：.ks-status-bad 拿 --dsw-alias-state-error-secondary 当**底色**。
      **实测（真 Chrome + PNG 数像素，见 plugin/scripts/ui-badge-pixels.mjs）**：
        · light：文字 rgb(236,19,19) 落在底 rgb(242,90,90) 上 ⇒ 对比度 **1.37**（229 个文字像素）；
        · dark ：state-error-secondary 与 state-error-primary **解出来是同一条**（都 = red-400
          rgb(242,90,90)）⇒ 徽章是**一整块纯色**（rect 内 1045 个像素全是那个色，**可辨文字 0 个**）
          —— 深色下「已废止」三个字与底糊成一片（复核原话：深色只有 6 个 #EC1313 ≈ 0）。
      **更正**：错误色族里**没有** --dsw-alias-state-error-tertiary（2026-09-19 那次"引用不存在的
        token"就抓到过它；渲染级冒烟的 ghost-token 断言现在盯着这类引用）⇒ 底色改用**唯一**语义
        合适的 error 系浅底 token --dsw-alias-interactive-bg-hover-danger
        （light = rgba(236,19,19,.05) 近乎白底红晕 / dark = rgba(242,90,90,.15) 暗红晕）。
        改后实测：light 对比度 **4.1**、dark **4.69**，两边都有 200+ 可辨文字像素。
      ⚠ **归属如实**：.ks-status* 在本区间（57c992b..68ef946）的 git diff **零改动**
        ⇒ 这**不是 P2 回归**，是 **P1-5 起就有的 token 选错**（P1-5 的记录只写了"浅底+描边+同色系
        文字"这个形状，没有把每条 token 在**两套主题**下解出来核一遍）。
      ⚠ **本段注释不许出现反引号**：整段 CSS 是一个模板字符串，反引号会把它截断
        （本文件已经踩过三次；真要用就写成转义的反引号，见上面 :root 那段）。 */
.ks-status{flex:none;display:inline-flex;align-items:center;box-sizing:border-box;
  height:var(--ks-space-5);padding:0 var(--ks-space-2);border:var(--ks-stroke) solid;
  border-radius:var(--ks-r-sm);font-size:var(--ks-fs-sm);font-weight:600;white-space:nowrap}
.ks-status-ok{background:var(--dsw-alias-state-success-tertiary);color:var(--dsw-alias-state-success-primary);
  border-color:var(--dsw-alias-state-success-primary)}
.ks-status-warn{background:var(--dsw-alias-state-warn-tertiary);color:var(--dsw-alias-state-warn-label);
  border-color:var(--dsw-alias-state-warn-label)}
/* 「已废止」的底色 = error 系里**唯一**的浅底 token（详见上面那段更正：
   state-error-secondary 在 dark 与文字色同值 ⇒ 整块纯色、文字读不出来）。 */
.ks-status-bad{background:var(--dsw-alias-interactive-bg-hover-danger);color:var(--dsw-alias-state-error-primary);
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
/* ⚠ **5j（2026-09-20）窄档紧凑化 —— 这是页面留边的连带修复，不是顺手改**：
   留边吃掉 2×16=32px 后，520 档里 .ks-main 从 496 落到 464，而这条批量条的**自然宽是 468**
   ⇒ 实测从**一行 40px** 变成**两行 72px**（"批量删除"被挤到第二行）。留边是业主要的东西、
   不能为它减，所以按**现有 @container 口径**（.ks-main 就是那个容器）在窄档把条子收紧凑：
   gap 8→4、左右内边距 12→8 ⇒ 自然宽 468−16−8=444 < 464，实测回到**一行**。
   阈值 520 取的是"这条条子放不下"的可用宽上界（468），不是拍脑袋的断点。
   ⚠ 与 .ks-batch 主规则同权重 ⇒ 靠**源码顺序**压过它（写在它之后），条件是 max-width。
   ⚠ 本段在模板字符串里：注释里**不许出现反引号**（会截断模板，本轮已踩第 13 次）。 */
@container (max-width:520px){
  .ks-batch{gap:var(--ks-space-1);padding:var(--ks-space-2)}
}
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

/* ===================================================================================
   ---------- 页面留边（5j，2026-09-20；**这是补规范缺口，不是"一直都有"**） ----------

   业主原话：「窗口四周要留点边啊，你这按钮都快跑到侧边栏外面去了，你改一下 UI 设计规范，
   然后应用上」。⇒ 两件事：① 规范原来**只定义了元素之间**的间距（--ks-space-*，4px 网格），
   **从没定义过"页面内容与窗口边缘的最小距离"** —— 所以每个页面根各自决定留不留；
   ② 实测改前：页面根 0px、卡片带 / 表格容器 / 批量条 / ＋新建那一行**全部贴到 shell 内容边**。

   判据（与第二节同名一段逐字一致）：**页面根 / 卡片带外框 / 表格容器 / 批量条 / 页面级按钮行
   的元素外缘（页面根看它的**内容盒**外缘）到 shell 内容边的最小距离 ≥ --ks-page-pad-x**。

   ⚠ **为什么容器是外面那个 .ks-page**（而不是让页面根自己当容器）：
     CSS 里容器**不能**用自己的宽度查自己（cqw 也只看**就近祖先**容器）⇒ 页面根自己当容器的话，
     它自己的 padding 永远读不到宽档值（只有后代读得到）。
     .ks-page 只承担 container-type（**零内边距、零外边距**）⇒ **不是"盒子套盒子"**：
     可用宽 = 页面根宽 − 2×留边，一分不多（第二节那条边界的兑现）。
   ⚠ **为什么按容器宽切档而不是 @media**：宿主右侧栏宽度是业主自己拖的，与视口宽**没有关系**
     （同一视口下 520 与 1300 都出现过）——同一条理由见 .ks-main 的 container-type 注释。
     阈值 660 与 .ks-main 的列档**同一个数**，两个档位因此永远对齐（不新立口径）。
   ⚠ 竖向留边同样两档；批量条的**竖向**是它自己的 position:sticky（贴滚动口下沿，故意的），
     不在这条判据里 —— 那条只能在真宿主页里看（离屏渲染看不见 sticky，见第五节已知失真）。
   ⚠ 本段是模板字符串里的一段 CSS：注释里**不许出现反引号**（会截断模板）。 */
.ks-page{container-type:inline-size;min-height:100%;box-sizing:border-box}
.ks-kb,.ks-ing,.ks-mat{
  padding-top:var(--ks-page-pad-y);padding-bottom:var(--ks-page-pad-y);
  padding-left:var(--ks-page-pad-x);padding-right:var(--ks-page-pad-x)}
/* 宽档：页面根宽 ≥ 660 ⇒ 换成 24（与 .ks-main 的列档同阈值、同一条容器）。
   ⚠ 这里只改**自定义属性**（在 .ks-kb 等元素上），padding 那条声明从元素自己的 computed
     变量取值 ⇒ 效果等价于"页面的 padding 变小/变大"，但容器查询**没有**去查自己。 */
@container (min-width:660px){
  .ks-page .ks-kb,.ks-page .ks-ing,.ks-page .ks-mat{
    --ks-page-pad-x:var(--ks-page-pad-x-wide);
    --ks-page-pad-y:var(--ks-page-pad-y-wide)}
}
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
