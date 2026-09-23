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

   ⚠ 为什么挂 :root 而不是我们某个面板的根类：
     我们的面板分布在宿主的多个插槽里（开始页入口卡 / 右侧栏各 tab / 知识库页…），
     **没有一个共同的祖先**是我们自己的。挂 :root 只是把 20 来个 --ks-* 自定义属性
     声明出来（带 ks- 前缀 = 我们自己的命名空间）：自定义属性**本身不产生任何样式**，
     宿主不读它们就完全无感；代价是宿主 DOM 会继承到这批变量（惰性）。
     若哪天要收窄作用域，把它们挪到我们各面板根类上即可（规则里用的 var(--ks-*) 不用改）。
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
     ⚠ 卡高（136）在 5a 定义后**长期没人用**（P0-2 点名的"死 token"）——2026-09-20 由
       .ks-kb-cards>*{min-height:var(--ks-card-h)} 消费过一次；**2026-09-21（第 3 步）卡片带整段删除**
       ⇒ 它又回到"没人消费"的状态（如实登记，别拿它当"有主的 token"）。要不要删这个 token
       由"卡片是否还会回来"决定，不属本批（本批只删页面里的死代码，不动尺度表的既有条目）。
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
     align-items:center 加上图标把它撑起来的，不是宿主给的档）。行尾「⋮」显式钉 24px。
     ⚠ 2026-09-21（第 3 步）：批量条 .ks-batch 已随"批量动作不在本批"撤掉，
       这个 token 的消费方只剩 .ks-item-more button（口径没变，名字没改）。 */
  --ks-btn-h-sm:24px;

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

/* ⚠⚠ **2026-09-21（第 6 步）真机读图发现并修**：窄档（.ks-page 496px）里这一行本来就挤
   —— 5k 的截图里「新建下级目录」「上传到这一层」已经被压成**两行**、面包屑被截成「你…」；
   本批又加了「在此范围内提问」+ 范围 chip 两个成员 ⇒ 实测**按钮被压成竖排**（一个一个字上下堆）、
   并且和面包屑**叠在一起**（读图看到的，不是猜的；ksPadCheck 判不出来 —— 它只看左右留边）。
   ⇒ 这一行**允许换行**（flex-wrap）+ 里面的按钮**不许断行**（nowrap）：内容是真的多，
      换行是**如实**的代价；压扁/叠字只会让字读不出来。 ⚠ 本段在模板字符串里，**不许出现反引号**。 */
.ks-kb-row{display:flex;align-items:center;gap:var(--ks-space-2);flex-wrap:wrap}
.ks-kb-row>button{white-space:nowrap}
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
/* ⚠ **2026-09-21（第 3 步）删除记录**：.ks-kb-foot（卡片页脚，卡片带的卡底分隔线）已随卡片带
   一起删除 —— 全仓 grep 已无消费者。
   ⚠ 另外这几条**在本批之前就没人消费**（登记，不属本批范围，故**不删**以免把 diff 扯到别的面上）：
     .ks-kb-btn / .ks-kb-btn-primary / .ks-kb-doc / .ks-kb-no / .ks-kb-nm
     —— 它们与"卡片带"无关，是更早的迭代留下的；要清就单开一批清（免得与本次改版的判据混在一起）。 */
.ks-kb-btn{border:var(--ks-sep) solid var(--dsw-alias-border-l4);border-radius:var(--ks-r-lg);padding:var(--ks-space-1) var(--ks-space-3);font-size:var(--ks-fs-sm);
  color:var(--dsw-alias-label-secondary);background:transparent;cursor:pointer}
.ks-kb-btn:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-kb-btn-primary{background:var(--dsw-alias-brand-primary);color:var(--dsw-alias-bg-base);
  border-color:transparent;font-weight:600}
/* ---------- 卡片（P0-3，2026-09-20）：从"描边幽灵"改成宿主 elevation 面 ----------
   之前只有 .5px 描边 + 与页面同色的白底 ⇒ 520 的图上"是不是卡片"要靠猜，同列高度还有
   212/115/85 三档。现在：内边距走 12px（网格值）、阴影走**宿主的 elevation 档**
   （不自己编 rgba —— 深浅色/换肤自动跟随）。
   ⚠ 官方硬规则：「Elevated surfaces … set border: 0 and take box-shadow: var(--dsw-elevation-*)。
      Never pair a --dsw-alias-border-* border with an lv/elevation shadow」⇒ 这里 **border:0**，
      发丝描边由阴影里的 --dsw-elevation-stroke 画（颜色重绑成 border-l2，与改前的描边同档）。
   ⚠ 2026-09-21（第 3 步）：业主定案"原来的**大卡片去掉**" ⇒ 卡片带（.ks-kbband / .ks-kb-cards
      / --ks-band-*）整段已删；.ks-kb-card 本身**保留**，它现在只被"文件详情"那一张卡消费。 */
.ks-kb-card{box-sizing:border-box;display:flex;flex-direction:column;
  border:0;border-radius:var(--ks-r-card);padding:var(--ks-space-3);
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l2);
  background:var(--dsw-alias-bg-base);box-shadow:var(--dsw-elevation-soft);
  transition:box-shadow var(--ks-dur-fast)}
.ks-kb-card:hover{--dsw-elevation-stroke-color:var(--dsw-alias-border-l4);
  box-shadow:var(--dsw-elevation-panel)}
/* 卡片网格：**同列卡等高**（align-items:stretch 是 grid 的默认值，这里写出来当"正面约束"）
   + 子项吃 --ks-card-h 这门高度档。
   ⚠ 用 min-height 而不是 height：内容多的卡仍能长高，不会被截断。
   ⚠ **2026-09-21（第 3 步）就地更正**：本条的消费者已从"卡片带"换成**能力页**
     （KsCapabilityPage.tsx 用 .ks-kb-cards + 内联 gridTemplateColumns 排它那 8 张卡）
     —— 卡片带（.ks-kbband）已随业主要求删除，但这个**网格基类留着、有人用**，
     不是死代码（删了能力页会塌成一列）。 */
.ks-kb-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:var(--ks-card-gap);
  align-items:stretch}
.ks-kb-cards>*{min-height:var(--ks-card-h)}
/* ---------- 面包屑 + 「返回上一层」 + 目录树（5h 起；2026-09-21 第 3 步改成真路径） ----------
   面包屑行：左边是返回按钮（**在最外层时 disabled**），中间是当前路径，右边是这一级的计数
   （最外层那一格如实写"你在最外层"）。
   ⚠ 路径用**后端给的目录名**（data.breadcrumb 逐条），不是本地推的 key。
   ⚠ 结构：外层 .ks-crumb-path 里是「条目 / 分隔符 / 条目 / …」——.ks-crumb-item（一级一个）
     + .ks-crumb-sep（斜杠，**与条目是兄弟**）；条目内部要么是可点的 .ks-crumb-go（button），
     要么是**当前级**的 .ks-crumb-here（span）。
     收敛口径：整条是 nowrap flex，条目 flex:0 1 auto（可缩）+ .ks-crumb 的 overflow:hidden
     ⇒ 窄窗（520）下尾巴被裁掉，不会把行撑破；条目自己还有 text-overflow:ellipsis。 */
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

/* ---------- 知识库页（2026-09-21 第 3 步）：**目录树 | 当前这一级 | 详情** 三段式 ----------
   一列放不下就换行：右栏宽度是业主自己拖的，不许假设它有多宽。
   ⚠ 5h 删掉了第三段「目录轨」（.ks-rail）—— 那一版业主说"不要展示目录树"；
     **2026-09-21 第 3 步又把它请回来**（业主本轮定案：「**左边一列目录**，点一级进去看里面」）
     ⇒ 左列现在是 .ks-kb-tree（真目录树，按需展开）。两次改动的依据都是业主原话。 */
.ks-split{display:flex;gap:var(--ks-space-2);align-items:flex-start;flex-wrap:wrap;min-height:0}
/* 左列目录树（第 3 步新增）：
   · 固定窄列（168px）+ 不伸不缩 —— 右栏才是内容；窄档（520）下 168 + gap 8 + 主栏 min 260
     = 436 < 488（页面根宽 − 2×16 留边），**不会把主栏挤到第二行**（留边那条注释算过这笔账）。
   · 自己可滚动（目录多了内部滚，不把整页顶长）。
   ⚠ 它**不是**新的留边适用面之外的东西：.ks-kb-tree 已加进 UI-BASELINE 第二节的适用面
     与三处脚本副本（见那一节）。 */
.ks-kb-tree{flex:0 0 168px;min-width:168px;max-height:520px;overflow:auto;box-sizing:border-box;
  border:0;border-radius:var(--ks-r-card);padding:var(--ks-space-2);
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l2);
  background:var(--dsw-alias-bg-base);box-shadow:var(--dsw-elevation-soft)}
.ks-tree-head{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary);
  padding:0 var(--ks-space-1) var(--ks-space-2)}
.ks-tree-body{display:flex;flex-direction:column}
.ks-tree-node{display:flex;flex-direction:column}
/* 一行 = 箭头(16) + 名字(1fr) + 篇数；深度靠 padding-left 缩进（每级 8px）。 */
.ks-tree-row{display:flex;align-items:center;gap:var(--ks-space-1);box-sizing:border-box;
  min-height:var(--ks-row-h-narrow);padding:0 var(--ks-space-1);border-radius:var(--ks-r-md)}
.ks-tree-row[data-depth='1']{padding-left:var(--ks-space-3)}
.ks-tree-row[data-depth='2']{padding-left:var(--ks-space-5)}
.ks-tree-row[data-depth='3']{padding-left:var(--ks-space-8)}
/* 当前这一级高亮：走宿主 interactive 档（不新造色值），并给左侧一条 2px 标记条。 */
.ks-tree-row[data-on='true']{background:var(--dsw-alias-interactive-bg-active)}
.ks-tree-row[data-on='true'] .ks-tree-label{font-weight:600;color:var(--dsw-alias-label-primary)}
.ks-tree-caret{flex:none;display:inline-flex;align-items:center;justify-content:center;
  width:16px;height:16px;padding:0;border:0;background:transparent;cursor:pointer;
  color:var(--dsw-alias-label-tertiary)}
.ks-tree-caret-leaf{display:inline-block}
.ks-tree-name{flex:1;min-width:0;display:flex;align-items:center;gap:var(--ks-space-1);
  padding:0;border:0;background:transparent;font:inherit;text-align:left;cursor:pointer;
  color:var(--dsw-alias-label-secondary);border-radius:var(--ks-r-sm)}
.ks-tree-name:focus-visible,.ks-tree-caret:focus-visible{outline:var(--ks-stroke) solid var(--dsw-alias-border-l4);
  outline-offset:1px}
.ks-tree-label{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:var(--ks-fs-sm)}
.ks-tree-count{flex:none;font-size:var(--ks-fs-xs);color:var(--dsw-alias-label-tertiary)}
.ks-tree-hint{padding:0 var(--ks-space-2);font-size:var(--ks-fs-xs);color:var(--dsw-alias-label-tertiary)}
.ks-tree-err{color:var(--dsw-alias-state-error-primary)}
/* ⚠ P2 头条（2026-09-20）：.ks-main 是**容器查询的容器**（container-type:inline-size）
   —— 表格的列档（窄档 / 宽档）按**它自己的宽度**切，不是按视口切。
   为什么不能用 @media：宿主右栏的宽度是业主自己拖的，与视口宽**没有关系**
   （1300 视口下 .ks-main 只有 820px，而 520 视口下它是 496px，都在同一个视口区间里）。
   ⚠ **第 3 步起 min-width 与 flex-basis 都收到 260px**：左边多了 168px 的目录树，
     两列要在 520 档的 **464px** 可用宽（页面根 496 − 2×16 留边）里并排
     ⇒ 168 + 8 + 260 = 436 ≤ 464（留 28px 余量）。
   ⚠⚠ **flex-basis 必须与 min-width 同值（本批真 Chrome 实测踩到，levelCheck 当场红）**：
     flex-wrap:wrap 决定**换行**看的是 flex-basis，不是 min-width —— basis 写 320 时
     168 + 8 + 320 = 496 > 464 ⇒ 主栏被挤到**第二行**（量到的几何：左列右缘 196px > 右栏左缘 28px）。
     旧值 320 是"两列时代"（可用宽 496）的数，左列出现之后它必须一起收。
   ⚠ container-type:inline-size 只加"行内尺寸不依赖内容"的包含 ⇒ 它是 flex 项，宽度由 flex 行给。 */
.ks-main{flex:1 1 260px;min-width:260px;display:flex;flex-direction:column;gap:var(--ks-space-2);
  min-height:0;container-type:inline-size}
.ks-detail{flex:0 1 232px;min-width:200px;display:flex;flex-direction:column;gap:var(--ks-space-2)}
/* 文件分页条（第 3 步）：后端 limit/offset/has_more 的界面口。 */
.ks-pager{display:flex;align-items:center;justify-content:center;gap:var(--ks-space-2)}
.ks-pager-n{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary);white-space:nowrap}
.ks-pager-btn{height:var(--ks-btn-h-sm);min-height:var(--ks-btn-h-sm)}
/* 上传面板（第 3 步）：来源目录 + 导入按钮 + 如实的过程/结果说明。 */
.ks-upload{display:flex;flex-direction:column;gap:var(--ks-space-1);box-sizing:border-box;
  padding:var(--ks-space-2) var(--ks-space-3);border:0;border-radius:var(--ks-r-card);
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l2);
  background:var(--dsw-alias-bg-base);box-shadow:var(--dsw-elevation-soft)}
.ks-upload-row{display:flex;align-items:center;gap:var(--ks-space-2);min-width:0}
.ks-upload-label{flex:none;font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
.ks-upload-dir{flex:1;min-width:0}
.ks-upload-go{flex:none}
.ks-upload-note{font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-tertiary)}
.ks-upload-msg{font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-secondary)}
.ks-upload-msg-bad{color:var(--dsw-alias-state-error-primary)}
/* 读不到库时的错误条（第 3 步）：给出**引擎原话** + 一个重试按钮，不静默留白。 */
.ks-kb-err{display:flex;align-items:center;gap:var(--ks-space-2);flex-wrap:wrap;
  padding:var(--ks-space-2) var(--ks-space-3);border-radius:var(--ks-r-card);
  background:var(--dsw-alias-interactive-bg-hover-danger)}
/* ---------- 列表容器 + **真表格**（P1-2 建容器；P2 头条 2026-09-20 把它变成真表格） ----------
   改前：「.ks-item」 是 「.ks-main」 的**直接子元素**（DOM 里 4 个裸行），页面上量不到任何一条
   竖边 ⇒ 列表像散落的行而不是一个列表。P1-2 把「.ks-lhead」 与所有 「.ks-item」 包进这一层。
   P2 头条：表头从"全选 + 目录名 + 计数"改成**真列头行**（文件名 / 效力 / 生效日期 / 标签），
   每一行按同一份列定义排 —— 列宽的**唯一所有者**就是这里的 --ks-cols：

     ⚠⚠ **列模板只许有一处定义**（这是 P2 头条的验收口径）：表头与行都只写
        grid-template-columns:var(--ks-cols)，谁也不许再写一套列宽。
        渲染级证据在 ui-render-shot.mjs 的 #cols（真 Chrome 里量 header 与 row 的
        computed grid-template-columns，两者必须逐字相同）。
     列宽都落在 4px 网格上（32 / 72 / 80 / 96 / 36），未引入任何非网格值。
     窄档（宿主侧栏 520 ⇒ .ks-main 更窄）：勾选 | 名称(2 行) | 效力 | ⋮ 四列。
     宽档（≥660px）：再加**生效日期**与**处理状态**两列（六列）。
     ⚠ 窄档是"隐藏两列"，不是"删 DOM"：DOM 结构两个档**完全一样** ⇒ 渲染级冒烟
       （jsdom 不做布局、也不认 @container）量到的 cell 结构恒为 6 列，与真机一致。
     ⚠ **第 5 步加了勾选列**（--ks-col-fpick，两个档位都在）：批量挪/复制/从这一层拿掉
       是业主点名的能力，窄档也不许把它藏起来（藏了就没法批量）。
     ⚠ 为什么窄档舍掉的是这两列：窄列里塞 5 列会把**名称**挤到 200px 以内，而行里最需要
       宽度的就是名称；效力是 20px 的徽章、信息密度最高，留下。
     ⚠ **2026-09-21（第 3 步）第 4 列从「标签」换成「处理状态」**：标签在本批**没有落库的接口**
       （doc_meta.domain_tags 是原始 JSON 串，而 /kb/.../items 不下发解析后的列表）⇒ 留着那一列
       只能是空壳或假数据；而"所有文件都要显示处理状态"是方案 §一里业主明说的 ⇒ 第 4 列改成
       --ks-col-stage（值来自后端 stage，本批如实显示，第 4 步做完整）。 */
.ks-list{--ks-col-fpick:32px;--ks-col-status:72px;--ks-col-date:80px;--ks-col-stage:96px;--ks-col-more:36px;
  --ks-cols:var(--ks-col-fpick) minmax(0,1fr) var(--ks-col-status) var(--ks-col-more);
  border:0;border-radius:var(--ks-r-card);overflow:hidden;
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l2);
  background:var(--dsw-alias-bg-base);box-shadow:var(--dsw-elevation-soft)}
/* 窄档把这两列**藏起来**（DOM 还在，只是不占格）—— 与 --ks-cols 的三列模板配套。
   ⚠ 选择器写成 .ks-list .ks-cell.ks-col-*（0,3,0）：它必须压过下面
     「.ks-lhead .ks-cell{display:flex}」与「.ks-item .ks-col-stage」这两条 (0,2,0)；
     而它自己又要被**后面**那条 @container 覆盖 —— 所以它必须写在 @container **之前**
     （同权重时后者胜；第一版把顺序写反，实测宽档下两列仍然是 display:none）。 */
.ks-list .ks-cell.ks-col-date,.ks-list .ks-cell.ks-col-stage{display:none}
/* 宽档：6 列（勾选 | 名称 | 效力 | 生效日期 | 处理状态 | ⋮）。容器查询挂在 .ks-main 上（见上）。
   ⚠ 必须放在上面那条 display:none **之后**（同权重、靠源码顺序覆盖）。
   ⚠ 第 5 步给文件层加了**勾选列**（--ks-col-fpick，两个档位都在：批量处置是这一批的头等事，
     窄档也不许丢掉它）⇒ 窄档 4 列 / 宽档 6 列，两档都用同一条 --ks-cols 变量。 */
@container (min-width:660px){
  .ks-list{--ks-cols:var(--ks-col-fpick) minmax(0,1fr) var(--ks-col-status) var(--ks-col-date) var(--ks-col-stage) var(--ks-col-more)}
  .ks-list .ks-cell.ks-col-date,.ks-list .ks-cell.ks-col-stage{display:flex}
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
   ⚠ 为什么要有 --ks-col-dcount / --ks-col-dmore 这两个中间变量：与文件层 --ks-col-more
     等**同一种写法**（列宽进变量、模板只引用变量）。值都在 4px 网格上（64/28/32）。
   ⚠ **第 5 步的两处改动**：① 加勾选列（--ks-col-dpick，两个档位都在）；
     ② 末列从"一个只展示的进入箭头"（16px 的 --ks-col-dgo）换成**行尾 ⋮ 菜单**
     （28px 的 --ks-col-dmore：改名 / 新建下级 / 挪 / 复制 / 删）—— 目录行因此**不再是 button**
     （行内要有勾选框与 ⋮ 两个真控件；button 里嵌 input 是非法 HTML），
     "进入这一级"改成名字那一格里的 .ks-dir-open 真 button（键盘可达、整行也仍可点）。
   ⚠ **别把 .ks-list-dirs 写成 .ks-dirs**：.ks-dirs 只是容器的旧名字（三处外部锚点按名引用它，
     见上面那一段注释），**几何归 .ks-list-dirs**。两者在 JSX 里同时挂在同一个 div 上。
   ⚠ 本段注释里**一个反引号都没有**（整段 CSS 在模板字符串里；反引号会截断它 ——
     本批实测踩到过一次：被截断后 .ks-list-dirs 的规则整段没进产物，列对齐自检当场红）。 */
.ks-list-dirs{--ks-col-dpick:32px;--ks-col-dcount:64px;--ks-col-dmore:28px;
  --ks-cols:var(--ks-col-dpick) minmax(0,1fr) var(--ks-col-dcount) var(--ks-col-dmore);
  display:block;background:transparent;box-shadow:none;
  --dsw-elevation-stroke-color:transparent}
/* 目录行（第 5 步起是 **div**：行内要有勾选框与 ⋮ 两个真控件）。
   ⚠ 要打回"一行列表项"的样子：底色/描边清零（默认外观一律不许冒出来）。
   ⚠ 行高与文件行**同一个 token**（--ks-row-h-list，52px）—— "和文件列表一样的视图"最硬的一条：
     两层行高逐像素一致（真 Chrome 实测：目录行 52 = 文件行 52）。
   ⚠⚠ **2026-09-21 就地更正**（本段原写"第一列也是**两行**：目录名 + 整条路径，手法同文件层的
     名字 + 标准号：都用 .ks-item-sub + grid-area:2/2"）：那个第二行**已删** —— 它印的是内部 key
     （根目录那级 key 等于 name ⇒ 图上名字重复两遍；往里一级变成内部路径「法律/宪法与行政法」）。
     目录行现在是**单行**（图标 + 名称）；嵌套 grid 那一列还在，但只用于"图标列 + 名字"这一行。
     判据同 KsKnowledgePage.tsx 的 DIR_COLUMNS 注释（"目录行只有名字"那一条）。
   ⚠ 这里**不写** border / padding（padding 由共享的 .ks-item 给，两条同权重、靠源码顺序叠加）。
   ⚠⚠ **width:100% 仍然必须**（第 3 步真 Chrome 实测到的坑）：div 行作为块级盒自动铺满容器宽；
     当年换成 button 之后它是 shrink-to-fit（行宽只有 346px、minmax(0,1fr) 那一列跟着塌到
     206.328px ⇒ 表头 1152px / 行 206.328px）。现在虽然回到 div，但**这条留着**：
     它同时兜住"哪天有人再把它改成别的 display"这一类回归（文件层 div 行没有这条也照样满宽）。 */
.ks-list-dirs .ks-item{width:100%;font:inherit;text-align:left;color:var(--dsw-alias-label-primary);
  background:transparent;border:0;cursor:pointer;text-decoration:none}
.ks-list-dirs .ks-item:hover{background:var(--dsw-alias-interactive-bg-hover)}
/* 焦点环用 **inset** box-shadow（不是 outline）：容器是 overflow:hidden，外扩的环会被裁掉。
   ⚠ 第 5 步起焦点环挂在**行内那个真 button**（.ks-dir-open）上（行本身是 div，不可聚焦）。 */
.ks-list-dirs .ks-item:focus-within{outline:none;
  box-shadow:inset 0 0 0 var(--ks-stroke) var(--dsw-alias-border-l4)}
/* 目录名那一格（**只在行里**）：里面是"进入这一级"的真 button（.ks-dir-open），
   它自己才是嵌套 grid（16px 图标列 + 名字 + 16px 进入箭头）。
    ⚠⚠ 选择器**必须限定在 .ks-item 行内**：表头那一格的类名也是 .ks-col-dname，把嵌套 grid
      用到表头上会把 16px 当成第一列 ⇒ 表头的「目录」被挤进 16px、**只剩「目」**
      （本批真 Chrome 实测：spClientW=16 / spScrollW=24，图上只显示一个字；文件层那条规则
       写的是 .ks-item .ks-col-name，天生没这个问题。**修法就是本行的 .ks-item 限定**）。 */
.ks-list-dirs .ks-item .ks-cell.ks-col-dname{display:flex;align-items:center;min-width:0}
.ks-list-dirs .ks-item .ks-dir-open{display:grid;grid-template-columns:16px minmax(0,1fr) 16px;
  column-gap:var(--ks-space-2);align-items:center;width:100%;min-width:0;
  font:inherit;text-align:left;color:inherit;background:transparent;border:0;cursor:pointer;padding:0}
/* 目录名（名字那一格，**只在行里**）：font-weight:600 —— 原来卡片上的名字就是这个字重（搬家不换样式）。
   ⚠ 这里把旧规则里的 flex:1 **去掉了**：新容器是 grid 单元格，flex 在它上面是死声明
     （留着会让人以为宽度归它管，而宽度归 --ks-cols）。 */
.ks-list-dirs .ks-item .ks-dir-name{grid-area:1/2;min-width:0;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;font-size:var(--ks-fs-base);font-weight:600}
/* 篇数列 + 行尾菜单列：与文件层的 .ks-col-status / .ks-col-more 同一档（居中 / 靠右）。
   ⚠ .ks-kb-badge 是 flex:none 的胶囊（卡片上原来是它），放进 grid 单元格里没问题。 */
.ks-list-dirs .ks-cell.ks-col-dcount{display:flex;align-items:center;gap:var(--ks-space-2);min-width:0}
.ks-list-dirs .ks-cell.ks-col-dmore{display:flex;align-items:center;justify-content:flex-end}
.ks-dir-go{grid-area:1/3;display:inline-flex;align-items:center;justify-content:flex-end;
  color:var(--dsw-alias-label-tertiary)}
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
/* ══════════ 「待分类」层（KB-FOLDER-PLAN 第 4 步，2026-09-21） ══════════
   与目录层同一种做法：**复用** .ks-list/.ks-lhead/.ks-item 这一套机制，只给它一条
   **自己的** --ks-cols（勾选 / 文件名 / 状态 / 建议去向 / ⋮ = 5 轨）。
   业主点名的四样：**文件名 / 状态 / 建议去向 / ⋮**（勾选列是控件、无列头）。

   ⚠ 窄档藏的是**建议去向**，**不是状态**：业主"每篇状态如实显示"是硬要求
     （见 ui-render-shot.mjs 的 inboxCheck：真浏览器里量 display，两个方向都钉住）；
     建议去向在窄栏里塞不下时可以从 ⋮ 菜单里拿到同一件事（"按建议归位（路径）"）。
   窄/宽两档的切换点与文件层**同一个数**（660，容器是 .ks-main）。
   ⚠ 状态列取 **108px**（不是 132）：窄档主栏只有 288px、去掉行内边距只剩 264px，
     132px 会把「文件名」挤到 ~50px（真机实测：名字只剩「排队中的…」）。状态在窄档必须
     看得见 ⇒ 从两边省：状态列收 24px，失效原因/识别率允许换行（.ks-stage 是 flex-wrap:wrap）。
   ⚠ 这段注释里**一个反引号都没有**（整段在模板字符串里，反引号会截断它）。 */
.ks-list-inbox{--ks-col-pick:22px;--ks-col-istage:108px;--ks-col-imore:36px;
  --ks-cols:var(--ks-col-pick) minmax(0,1fr) var(--ks-col-istage) var(--ks-col-imore)}
.ks-list .ks-cell.ks-col-idest{display:none}
@container (min-width:660px){
  .ks-list-inbox{--ks-cols:var(--ks-col-pick) minmax(0,1fr) var(--ks-col-istage) minmax(0,1fr) var(--ks-col-imore)}
  .ks-list .ks-cell.ks-col-idest{display:flex}
}
.ks-list-inbox .ks-item{width:100%;box-sizing:border-box;padding:0 var(--ks-space-3);
  border-top:0.5px solid var(--dsw-alias-border-l2)}
.ks-list-inbox .ks-item:first-of-type{border-top:0}
.ks-item .ks-col-pick{display:flex;align-items:center;justify-content:center}
/* 第 5 步：目录层与文件层的勾选列（与「待分类」层的 .ks-col-pick 同一套内边距/居中口径；
   类名各自独立 —— 三层各有一条自己的 --ks-cols，行都挂在 .ks-item 上，重用类名会串味）。 */
.ks-item .ks-col-fpick,.ks-item .ks-col-dpick{display:flex;align-items:center;justify-content:center}
.ks-lhead .ks-cell.ks-col-fpick,.ks-lhead .ks-cell.ks-col-dpick{display:flex;justify-content:center}
.ks-item .ks-col-istage{display:flex;align-items:center;overflow:hidden}
.ks-item .ks-col-idest{align-items:center;overflow:hidden;min-width:0}

/* 渠道层（2026-09-22，业主定案「和知识库管理用一套 UI」）：**复用 .ks-list/.ks-lhead/
   .ks-item 机制**（目录层甚至直接用 .ks-list-dirs——列同为 名称/条数/›），这里只做
   渠道文件层自己的一件事：一条**自己的** --ks-cols（渠道 / 标签 / 能不能用 / 上次好用 /
   问题 / 操作 = 6 轨）。列宽唯一所有者仍是 --ks-cols，谁也不许再写第二套。 */
.ks-list-chans{--ks-cols:minmax(0,1.6fr) 84px 96px minmax(0,1fr) 200px}
/* 批E4（业主 2026-09-23）：页面顶条「文件夹凸出标签」四入口。选中那张=被抽出来的舌：
   上浮 2px、渐变底、投影、下缘与内容区连通；其余标签压在条上（审美案按业主授权自定）。 */
.ks-tabfolder-strip{display:flex;gap:4px;align-items:flex-end;padding:6px var(--ks-page-pad-x) 0;
  border-bottom:var(--ks-stroke) solid var(--dsw-alias-border-l2)}
.ks-tabfolder{border:var(--ks-stroke) solid var(--dsw-alias-border-l2);border-bottom:none;
  border-radius:var(--ks-radius) var(--ks-radius) 0 0;padding:4px 16px;cursor:pointer;
  font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary);background:transparent;
  min-height:30px;transition:transform .12s ease}
.ks-tabfolder:hover{color:var(--dsw-alias-label-primary);transform:translateY(-1px)}
.ks-tabfolder-on{color:var(--dsw-alias-label-primary);font-weight:600;transform:translateY(-2px);
  background:var(--dsw-alias-border-l2);margin-bottom:-1px;padding-bottom:6px;min-height:32px}
.ks-list-chans .ks-item{width:100%;box-sizing:border-box}
.ks-item .ks-col-chan{display:grid;grid-template-columns:minmax(0,1fr);min-width:0}
.ks-item .ks-chan-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ks-item .ks-chan-open{flex:none;margin-left:var(--ks-space-2)}
.ks-item .ks-col-tags{display:flex;flex-wrap:wrap;gap:4px;align-items:center;min-width:0;overflow:hidden}
/* （.ks-tag-chip 死样式已删：标签列/改备注随 NOT-DOING #17 撤出用户面，2026-09-22） */
.ks-item .ks-col-cstate,.ks-item .ks-col-cdate{display:flex;align-items:center;min-width:0}
.ks-item .ks-col-cdate{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary)}
.ks-item .ks-col-cissue{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ks-item .ks-col-cact{display:flex;align-items:center;justify-content:flex-end;gap:4px;
  flex-wrap:wrap;white-space:nowrap}
/* 勾选框：宿主的 Checkbox 把 label 渲染成可见 span ⇒ 这里把它做成 **sr-only**
   （视觉上不重复显示第二遍文件名，但可访问名还在 —— 直接 display:none 会把它从
   无障碍树里摘掉，那是另一种偷懒）。 */
.ks-pick{display:flex;align-items:center;justify-content:center}
.ks-pick-cb>span{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
/* 状态：档位徽章 + 失败原因 + 识别率（有才显示）+ "不在目录里"（正文为零那一批）。
   ⚠ 徽章颜色按**档位**给（排队中=中性 / 识别中=信息 / 待确认=警示 / 识别失败=错误）。 */
.ks-stage{display:flex;align-items:center;gap:var(--ks-space-1);min-width:0;flex-wrap:wrap}
.ks-stage-tag{flex:none;padding:0 var(--ks-space-2);border-radius:var(--ks-r-pill);corner-shape:round;border-width:0.5px;border-style:solid;
  font-size:var(--ks-fs-xs);border-color:var(--dsw-alias-border-l3);
  background:var(--dsw-alias-markdown-tag);color:var(--dsw-alias-label-secondary)}
.ks-stage-queued{background:var(--dsw-alias-markdown-tag);color:var(--dsw-alias-label-secondary)}
.ks-stage-recognizing{background:var(--dsw-alias-interactive-bg-hover);color:var(--dsw-alias-label-primary)}
.ks-stage-confirming{background:var(--dsw-alias-state-warn-secondary);color:var(--dsw-alias-state-warn-primary);
  border-color:var(--dsw-alias-state-warn-primary)}
.ks-stage-failed{background:var(--dsw-alias-interactive-bg-hover-danger);color:var(--dsw-alias-state-error-primary);
  border-color:var(--dsw-alias-state-error-primary)}
.ks-stage-why,.ks-stage-conf,.ks-stage-hidden{font-size:var(--ks-fs-xs);overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}
.ks-stage-why{color:var(--dsw-alias-state-error-primary)}
.ks-stage-conf{color:var(--dsw-alias-label-tertiary)}
.ks-stage-hidden{color:var(--dsw-alias-state-warn-primary)}
/* 建议去向：路径 + （可选）"＋新建 XXX" */
.ks-dest{display:flex;flex-direction:column;min-width:0;font-size:var(--ks-fs-sm)}
.ks-dest-path{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--dsw-alias-label-secondary)}
.ks-dest-new{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--dsw-alias-label-tertiary);
  font-size:var(--ks-fs-xs)}
/* 左列那一行（「待分类」不在 folder 表里，但样式与别的行一致 —— 只多一个中性按钮态） */
.ks-tree-name-inbox{font-weight:600}
.ks-tree-count-inbox{color:var(--dsw-alias-label-secondary)}
/* 一次动作的结果/失败**原话**（成功与失败都显示在这里，不美化） */
.ks-ib-msg{padding:var(--ks-space-2) var(--ks-space-3);border-radius:var(--ks-r-md);
  background:var(--dsw-alias-bg-layer-3);font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary)}
/* ── 「补全分类号」（2026-09-22 自愈机制）────────────────────────────────────
   进度条 + **失败清单**。纪律：数字**逐类分开**（补到 / 查无 / 查询失败 / 读不出来），
   不许合并成一句"部分失败"—— 业主口径是"界面把原因说清"。
   ⚠ 可以折行（窄档 .ks-main 只有 288px）：信息是真的多，压扁它只会让字读不出来。 */
.ks-ccs-btn{white-space:nowrap}
.ks-ccs-bar{display:flex;flex-direction:column;gap:var(--ks-space-1);
  padding:var(--ks-space-2) var(--ks-space-3);border-radius:var(--ks-r-md);
  border:0.5px solid var(--dsw-alias-border-l2);background:var(--dsw-alias-bg-base);
  font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary);min-width:0}
.ks-ccs-bar[data-ccs-running="1"]{border-color:var(--dsw-alias-brand-primary)}
.ks-ccs-line{overflow-wrap:anywhere}
.ks-ccs-fails{font-size:var(--ks-fs-sm)}
.ks-ccs-fails>summary{cursor:pointer;color:var(--dsw-alias-label-secondary)}
.ks-ccs-fail-list{margin:var(--ks-space-1) 0 0;padding-left:1.2em;max-height:14em;overflow:auto}
.ks-ccs-fail-list>li{min-width:0;overflow-wrap:anywhere}
.ks-ccs-fail-no{font-family:var(--ks-font-mono,monospace);margin-right:var(--ks-space-2)}
.ks-ccs-fail-why{color:var(--dsw-alias-label-tertiary)}
/* 批量条（第 4 步**做回真的**：每条都对应真接口）。悬浮在列表上方、居中限宽。
   ⚠ 它是页面留边的适用面之一（docs/UI-BASELINE.md 第二节）⇒ 不许贴边。
   ⚠⚠ **必须允许折行**（flex-wrap:wrap）：窄档（520 ⇒ .ks-main 只有 288px）里
   五个按钮 + 计数在一行里放不下，而按钮是 white-space:nowrap（不许把"重来一次"压成
   竖排）⇒ 不给折行时条子会**横着溢出右缘**（ui-render-shot 实测：.ks-batch 右缘贴边 -8px）。
   窄档折成两行是**如实**的代价：条子内容是真的多，压扁它只会让字读不出来。
   留痕：第 3 步删掉的那条"批量条不许被挤成两行"的像素断言**没有**恢复 ——
   它当时判的是**假**批量条的 40px 单行预算，而现在这一条是**多行**的悬浮工具条，
   恢复旧阈值等于拿一个不成立的预算去卡真东西；改由留边判据（PAD_REQUIRED 里的 .ks-batch）
   保证它不贴边。 */
.ks-batch{position:sticky;bottom:var(--ks-space-2);z-index:2;display:flex;align-items:center;
  flex-wrap:wrap;justify-content:center;
  gap:var(--ks-space-2);width:fit-content;max-width:100%;box-sizing:border-box;
  margin:0 auto;padding:var(--ks-space-2) var(--ks-space-3);
  border:0;border-radius:var(--ks-r-card);background:var(--dsw-alias-bg-layer-3);
  --dsw-elevation-stroke-color:var(--dsw-alias-border-l2);box-shadow:var(--dsw-elevation-soft)}
.ks-batch-n{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary);white-space:nowrap}
.ks-batch-btn{height:var(--ks-btn-h-sm);white-space:nowrap}
.ks-batch .ks-danger{color:var(--dsw-alias-state-error-primary)}
/* 动作面板（目录选择器 / 删除二次确认） */
.ks-act{display:flex;flex-direction:column;gap:var(--ks-space-2);padding:var(--ks-space-2) var(--ks-space-3);
  border:0.5px solid var(--dsw-alias-border-l2);border-radius:var(--ks-r-card);
  background:var(--dsw-alias-bg-base)}
.ks-act-del{border-color:var(--dsw-alias-state-error-primary)}
.ks-act-head{display:flex;align-items:center;gap:var(--ks-space-2);font-size:var(--ks-fs-base)}
.ks-act-hint{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
.ks-act-row{display:flex;align-items:center;gap:var(--ks-space-2);min-width:0;flex-wrap:wrap}
/* ⚠ 第 5 步（2026-09-21）真机实测补的两条：
   ① 动作面板在**窄档**（.ks-main 只有 264px）放三个按钮时，光有 flex 会把它们**挤扁** ——
      实测「取消」被压成竖排的「取 / 消」、「连里面的文件一起删」挤成三行还顶到面板右缘。
      ⇒ 允许换行（上一条的 flex-wrap）+ 按钮里的字**不许断行**（下面这条），
      按钮就按整块换行，不再被压扁。 */
.ks-act-row button{white-space:nowrap}
.ks-act-label{flex:0 0 auto;font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
.ks-act-name,.ks-act-search{flex:1;min-width:0}
.ks-act-list{max-height:220px;overflow:auto;display:flex;flex-direction:column;
  border:0.5px solid var(--dsw-alias-border-l2);border-radius:var(--ks-r-md)}
.ks-act-item{display:flex;align-items:center;gap:var(--ks-space-2);min-height:28px;padding:var(--ks-space-1) var(--ks-space-2);
  border:0;background:transparent;font:inherit;text-align:left;color:var(--dsw-alias-label-primary);cursor:pointer}
.ks-act-item[data-on="true"]{background:var(--dsw-alias-interactive-bg-hover)}
.ks-act-item:hover{background:var(--dsw-alias-interactive-bg-hover)}
.ks-act-item-name{flex:none;max-width:40%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ks-act-item-path{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:var(--ks-fs-xs);color:var(--dsw-alias-label-tertiary)}
.ks-act .ks-danger{color:var(--dsw-alias-state-error-primary)}
/* 删目录的**影响清单**（第 5 步）：每个目录一段，数字全部来自 delete-preview（只读）。 */
.ks-act-list-del{max-height:260px}
.ks-act-delrow{display:flex;flex-direction:column;gap:var(--ks-space-1);
  padding:var(--ks-space-2) var(--ks-space-3);border-top:var(--ks-stroke) solid var(--dsw-alias-border-l1)}
.ks-act-delrow:first-child{border-top:0}
/* 「逐篇看」（复活的 KsIngestPanel，第 5 步 §4①）挂在上传面板里的那一格：
   它自带 .ks-page 外壳（container-type），这里只负责**别让它溢出上传面板**。 */
.ks-upload-preview{display:block;min-width:0;margin-top:var(--ks-space-2);
  border-top:var(--ks-stroke) solid var(--dsw-alias-border-l2)}
.ks-upload-preview-open{flex:none}
.ks-upload-check{flex:none}
.ks-upload-hint{flex:1;min-width:0;font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary);
  overflow:hidden;text-overflow:ellipsis}
/* ═══════════════════ 第 6 步：按目录范围提问（范围 chip + 面板 + 答案） ═══════════════════
   业主口径：「每一级都能在此范围内提问，包括它下面所有层；多选几个目录 = 取并集」。
   范围 chip **常驻工具栏**（选中范围之后就一直看得见，不管面板开没开）：
   名字 + 引擎给的篇数 + 一个能清掉的 ✕。
   ⚠ 名字那一格**必须能收缩**（min-width:0 + 省略号）：窄档（.ks-main 只有 288px）里
     两个长目录名会把这一行顶出右缘，而页面留边判据（ui-render-shot 的 ksPadCheck）当场就红。 */
.ks-ask-open{flex:none;white-space:nowrap}
.ks-ask-chip{display:flex;align-items:center;gap:var(--ks-space-1);min-width:0;
  padding:0 var(--ks-space-2);height:var(--ks-btn-h-sm);box-sizing:border-box;
  border:var(--ks-sep) solid var(--dsw-alias-border-l2);border-radius:var(--ks-r-pill);
  background:var(--dsw-alias-bg-layer-3);font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary)}
.ks-ask-chip-tag{flex:none;color:var(--dsw-alias-label-tertiary)}
.ks-ask-chip-name{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ks-ask-chip-n{flex:none;white-space:nowrap;color:var(--dsw-alias-label-tertiary)}
.ks-ask-chip-x{flex:none;display:flex;align-items:center;justify-content:center;
  width:20px;height:20px;padding:0;border:0;border-radius:var(--ks-r-sm);
  background:transparent;color:inherit;cursor:pointer}
.ks-ask-chip-x:hover{background:var(--dsw-alias-interactive-bg-hover)}
/* 提问面板：问题一行（标签 + 输入 + 问一问），下面如实说边界；答案区在下面。 */
.ks-ask{display:flex;flex-direction:column;gap:var(--ks-space-2);
  padding:var(--ks-space-3);border:var(--ks-sep) solid var(--dsw-alias-border-l2);
  border-radius:var(--ks-r-card);background:var(--dsw-alias-bg-base)}
.ks-ask-head{display:flex;align-items:center;gap:var(--ks-space-2);flex-wrap:wrap;min-width:0}
.ks-ask-where{min-width:0;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:var(--ks-fs-base);font-weight:600;color:var(--dsw-alias-label-primary)}
.ks-ask-count{flex:none;font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
.ks-ask-close,.ks-ask-clear{flex:none;white-space:nowrap}
.ks-ask-row{display:flex;align-items:center;gap:var(--ks-space-2);min-width:0;flex-wrap:wrap}
.ks-ask-label{flex:none;font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
.ks-ask-q{flex:1;min-width:0}
.ks-ask-go{flex:none;white-space:nowrap}
.ks-ask-hint{font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-tertiary)}
.ks-ask-msg{font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-secondary)}
.ks-ask-msg-bad{color:var(--dsw-alias-state-error-primary)}
/* 答案区：**引擎回显的范围**在最上面（发起后也能看出这次到底在哪儿检索的）。 */
.ks-ask-res{display:flex;flex-direction:column;gap:var(--ks-space-2);min-width:0;
  padding-top:var(--ks-space-2);border-top:var(--ks-sep) solid var(--dsw-alias-border-l2)}
.ks-ask-echo{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary)}
.ks-ask-tier{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-tertiary)}
.ks-ask-h{display:block;font-size:var(--ks-fs-sm);font-weight:600;color:var(--dsw-alias-label-tertiary)}
.ks-ask-conc,.ks-ask-der{font-size:var(--ks-fs-base);line-height:1.6;color:var(--dsw-alias-label-primary)}
.ks-ask-empty{display:flex;flex-direction:column;gap:var(--ks-space-1);
  padding:var(--ks-space-2) var(--ks-space-3);border-radius:var(--ks-r-md);
  background:var(--dsw-alias-bg-layer-3);
  font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-secondary)}
.ks-ask-ev,.ks-ask-notes{display:flex;flex-direction:column;gap:var(--ks-space-1);min-width:0}
.ks-ask-evrow{display:flex;flex-direction:column;gap:var(--ks-space-1);min-width:0;
  padding:var(--ks-space-2) var(--ks-space-3);border-radius:var(--ks-r-md);
  background:var(--dsw-alias-bg-layer-3)}
.ks-ask-evno{font-size:var(--ks-fs-sm);font-weight:600;color:var(--dsw-alias-label-primary)}
.ks-ask-evtitle{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary)}
.ks-ask-evtext,.ks-ask-note{min-width:0;overflow-wrap:anywhere;
  font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-tertiary)}
/* ⚠⚠ **业主 2026-09-22**：「在此范围内提问」+ 范围 chip 搬进**这一行**（当前文件夹名那一条 bar，
   搜索框上面）—— 原话："按钮改到搜索栏上面显示文件夹名称的 bar 上，这样就很清楚是在这个文件夹内
   进行搜索"。这一行因此多两个成员 ⇒ **允许折行**（窄档不许把 chip 挤没、也不许压成竖排 ——
   第 6 步在工具栏上就踩过一次"按钮被压成竖排 + 与面包屑叠字"，见 .ks-kb-row 那段留痕），
   ⚠ 本段在模板字符串里，**不许出现反引号**（本仓已踩 20 次）。
   按钮里的字**不许断行**。 */
.ks-list-cap{display:flex;align-items:center;gap:var(--ks-space-2);min-width:0;flex-wrap:wrap}
.ks-list-cap>button{white-space:nowrap}
/* ⚠⚠ **2026-09-22（读图发现）**：提问入口搬进这一行之后，窄档（主栏 288px）实测把
   **文件夹名挤成「知...」**（名字那一格是 flex:1，会被按钮压到只剩十几像素）——
   而这一行的全部意义就是"看清楚这是哪个文件夹"。⇒ 给名字一个**最小可读宽度**
   （6em ≈ 13px 字号下的 6 个中文字）：挤不下时**这一行换行**（按钮/计数落到下一行），
   而不是把名字截成一个字。宽档一行放得下 ⇒ 行为不变。 */
.ks-list-cap .ks-lhead-name{min-width:6em}
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
   ⚠ **"整行可点"做了（业主 2026-09-21 定：勾选框只管勾选；点名字或行内任意处 → 打开详情）**。
     分流规则与键盘路径的唯一所有者在 KsKnowledgePage.tsx 的 openRowDetail；
     hover 反馈沿用下面既有那条 .ks-item:hover（宿主 interactive-bg-hover token，**不新造颜色**）。
     **留痕（不许删）**：这里曾写「**"整行可点"没有做**」（清单 P1-1 里那条建议），
     2026-09-20 复核打回更正成「未做（不是做不了）」+ 三条候选 —— 本轮落了候选 ①
     （行 onClick + closest 分流）；候选 ③ 在核过宿主源码后**确认做不了**（label 必可见）。 */
.ks-item{padding:var(--ks-space-1) var(--ks-space-3);
  min-width:0;min-height:var(--ks-row-h-list);cursor:pointer}
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
   第 1 行 = 文件图标(16px) + 文件名
   第 2 行 = 标准号（真字段；法规没有号就按全站约定给破折号）
   ⚠ 为什么这一格用**嵌套 grid 两行**（不是 flex-wrap）：第 2 行必须落在**名字那一段**的正下方
     （左缘与名字对齐，与 .ks-item-sub 的 grid-area:2/2 是同一个手法）。
   ⚠ **2026-09-21（第 3 步）就地更正**：本段原来写"图标只能在**勾选框**之前：名字与勾选框是
     同一个元素（Checkbox 的可见 label），插不进它们中间" —— **勾选框已随"批量动作不在本批"撤掉**
     ⇒ 名字现在是我们自己的 .ks-item-name（可见文本就在这一层，title= 给全名）。
     留痕：那条"③ 做不了（Checkbox 的 label 必可见）"的结论**仍然成立**，
     但它现在**不再是**这一列的形状约束（约束它的人已经不存在了）。 */
.ks-item .ks-col-name{display:grid;grid-template-columns:16px minmax(0,1fr);
  column-gap:var(--ks-space-2);row-gap:0;align-items:center}
.ks-fileico{grid-area:1/1;grid-row:1/3;display:inline-flex;align-items:center;justify-content:center;
  width:16px;height:16px;color:var(--dsw-alias-label-tertiary)}
/* 第 1 行：文件名（我们自己的元素 —— 可省略号、title= 给全名）。 */
.ks-item .ks-item-name{grid-area:1/2;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  color:var(--dsw-alias-label-primary);font-size:var(--ks-fs-md);line-height:1.4}
/* 第 2 行（.ks-item-sub）：标准号（12px tertiary），落在**文件名那一段**的正下方。 */
.ks-item-sub{grid-area:2/2;display:flex;align-items:center;gap:var(--ks-space-2);
  min-width:0;flex-wrap:nowrap}
.ks-item-meta{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-tertiary)}
/* 效力列 / 生效日期列 / 处理状态列（宽档才显示后两列，见 .ks-list 的容器查询） */
.ks-item .ks-col-status{display:flex;align-items:center}
.ks-item .ks-col-date{font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary)}
/* 处理状态列（第 3 步新增；第 4 列从"标签"换成它）：纯文本 + nowrap，
   值来自后端 stage（中文标签是客户端镜像，见 KsKnowledgePage.tsx 的 STAGE_LABELS 注释）。
   ⚠ 这里**不写 display**：显示/隐藏由上面 .ks-list 的窄/宽档唯一决定（写了会与它抢）。 */
.ks-item .ks-col-stage{align-items:center;overflow:hidden;
  font-size:var(--ks-fs-sm);color:var(--dsw-alias-label-secondary);white-space:nowrap;
  text-overflow:ellipsis}
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
/* 详情字段：日期这一类 label/value 成对 */
.ks-fields{display:flex;flex-direction:column;gap:var(--ks-space-1)}
.ks-field{display:flex;gap:var(--ks-space-2);font-size:var(--ks-fs-sm);line-height:1.5}
.ks-field-k{flex:0 0 62px;color:var(--dsw-alias-label-tertiary)}
.ks-field-v{flex:1;min-width:0;color:var(--dsw-alias-label-primary);word-break:break-word}
.ks-field-v-mono{font-family:ui-monospace,Consolas,monospace}
/* ⚠⚠ **2026-09-21（第 3 步）就地删除记录（本仓规矩：删了什么必须留痕）**：
   下面这几组选择器**已随功能一起删掉**，不是"忘了写"：
     · .ks-tag（行内/详情里的标签 chip）、.ks-tagrow*、.ks-parse*、.ks-subtabs
       —— 标签视图 + 行内/批量「＋标签」的全部样式。**按下去只改内存、不落库**（方案 §六
       最后一条明令不许留），本批一处不留；标签要落地需要后端的标签接口，属后续批次。
     · .ks-filters / .ks-chip / .ks-chip-on —— 状态筛选胶囊。文件列表现在是**后端分页**，
       而 /kb/folders/{id}/items **没有状态筛选参数** ⇒ 前端只筛当前一页会静默撒谎
       （"筛出 0 篇"其实后面几页有）。诚实的版本要后端加参数（本批不许改后端）⇒ 不做。
     · .ks-batch / .ks-batch-btn / .ks-batch-n / .ks-batch .ks-danger —— 悬浮批量条。
       方案 §五第 3 步的"本批不做"点名了"**批量选择动作**"⇒ 勾选与批量条一并撤掉
       （留着要么是假动作，要么就得在这一批顺手做掉"批量删除真删库"这件不可逆的事）。
   判据（有牙）：plugin/scripts/smoke-kb-page-render.mjs 里那几条"这些假动作真的没了"的断言
   （.ks-batch / .ks-chip / .ks-tagrow / .ks-subtabs 计数恒 0 + 菜单里没有「＋标签」）；把任一处
   加回来都会当场红。 */
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
/* 空态一句话（无卡版；仍在别处用） */
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
   高度由能力卡自己的 grid 行 stretch 保证与同排卡齐平（改前那句"由 .ks-kb-cards>*
   {min-height:var(--ks-card-h)} 保证"已随卡片带删除，2026-09-21 就地更正：那张网格不存在了，
   能力页用的是 .ks-cap-cards 自己的 grid）。 */
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
