# run-gates.ps1 — 本仓库**唯一**的门禁入口（AGENTS.md 的"门禁"一节指向这里）
#
# 为什么要有这个脚本（官方 `docs/development.md:131` 的口径是"门禁即代码"）：
#   在此之前，"门禁只涨不跌"是**散文**——每轮靠人记得手敲 5–6 条命令、手抄数字
#   （`docs/DEVELOPMENT-HISTORY.md` 里那几处"五件套/六件套"就是活证据）。
#   人记得 ⇒ 早晚会漏。这个脚本把它变成**一条命令 + 退出码**。
#
# 用法：
#   pwsh -File scripts/run-gates.ps1 -Quick      # 改动面：tsc / mypy / verify:commands / smoke
#   pwsh -File scripts/run-gates.ps1 -Full       # 全量：再加 pytest / 引擎门禁 / 真宿主 e2e
#   pwsh -File scripts/run-gates.ps1 -Quick -UpdateBaseline   # 绿了之后把新基线写回
#
# ⚠ **环境前提（-Full 从此需要 DSH 检出）**：`-Full` 的最后两步是**真 DSH** 的门禁
#   （`plugin/scripts/verify-tools-real.mjs` 用检出里真 `@deepseek-ai/dsh-tools` 的
#   `ToolRuntime`；`plugin/scripts/e2e-install-compose.mjs` 用真 CLI 起一次真宿主 + 临时
#   `$DSH_HOME`）。检出路径 = `$env:KS_DSH_CHECKOUT`，缺省 `D:\AI\DSH\deepseek-harness`；
#   **找不到就是红、不是跳过**（与 :154-168 "命令不存在"那条同一立论）。这条前提与
#   "`-Full`/冒烟需要本机有 Edge"同级 —— 复核在提取树里跑 -Full 前先确认检出在。
#   两步都是**临时目录**作业（`$DSH_HOME` 只设给子进程），代码树零运行产物；e2e 会从子环境里
#   剥掉所有 `*_API_KEY`（只留 KS_FAKE_KEY=fake）并把模型路由指向 127.0.0.1 的假网关。
#
# 三条纪律（都在 AGENTS.md 里，这里实现它们）：
#   1. **一次只跑一个**：并发跑会制造假红（`smoke-chatmode` 实测两次 172/173 都发生在与全量
#      pytest 并发时）。这里用锁文件把它变成**当场报错**，而不是靠人记得。
#      ⚠ 2026-09-19 起**锁也盖住冒烟自己**（`plugin/scripts/smoke-all.mjs` 取同一个锁文件）：
#      那次假红的真正来源是**复核子代理绕过本脚本直接跑冒烟**，而当时锁拦不住它。
#      ⇒ 只盖住"推荐的那条路"等于没盖住。
#   2. **只涨不跌**：pytest 的 passed 数只许涨；掉了就红（基线在 `scripts/gates-baseline.json`）。
#   3. **退出码为准**：任何一步失败即非零退出，且失败步骤逐条列出。
[CmdletBinding()]
param(
  [switch]$Quick,
  [switch]$Full,
  [switch]$UpdateBaseline
)

$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $PSScriptRoot
$baselinePath = Join-Path $PSScriptRoot 'gates-baseline.json'
#: pytest 的机器可读结果（棘轮判据取 nodeid，不再依赖 `文件:行号` —— 行号会随编辑位移）。
#: ⚠ 文件名带 `$PID` ⇒ **每次跑都是新文件**，旧的一直堆在 TEMP（复核 2026-09-20 数出已积 8 个）。
#:   这里跑前把同类旧文件清掉：它们没有任何保留价值（判据只读本次这份），而堆积会让
#:   "哪份是这次的"变成需要猜的问题。
$junitPath = Join-Path ([System.IO.Path]::GetTempPath()) "ks-gates-junit-$PID.xml"
$junitOld = @(Get-ChildItem -Path ([System.IO.Path]::GetTempPath()) -Filter 'ks-gates-junit-*.xml' -File -ErrorAction SilentlyContinue
  | Where-Object { $_.FullName -ne $junitPath })
if ($junitOld.Count -gt 0) {
  $junitOld | Remove-Item -Force -ErrorAction SilentlyContinue
  Write-Host ("（清掉 {0} 份旧的 ks-gates-junit-*.xml）" -f $junitOld.Count) -ForegroundColor DarkGray
}

if (-not $Quick -and -not $Full) { $Quick = $true }   # 缺省 = 快档（避免误触全量）
if ($Quick -and $Full) { $Quick = $false }            # 同时给 ⇒ 按全量

# ── 锁：把"并发跑门禁"变成当场报错 ─────────────────────────────────────────────
$lockPath = Join-Path ([System.IO.Path]::GetTempPath()) 'ks-gates.lock'
#: 锁的**最长合理寿命**：门禁（全量）实测 ~7 分钟；超过这个时长还"活着"的锁按陈旧处理
#: （防的是 pid 被复用 / 长命进程恰好占了这个号 ⇒ 之后所有门禁被永久堵死，只能手删锁文件）。
#: 复核（2026-09-19）把"无时效校验"列为缺陷；这里给一个保守上限并**打印为什么清掉**。
$lockMaxAgeHours = 6
if (Test-Path $lockPath) {
  $prev = (Get-Content $lockPath -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json -ErrorAction SilentlyContinue)
  $alive = $false
  if ($prev -and $prev.pid) {
    $alive = $null -ne (Get-Process -Id $prev.pid -ErrorAction SilentlyContinue)
  }
  $tooOld = $false
  if ($prev -and $prev.startedAt) {
    try {
      $tooOld = ((Get-Date) - [datetime]::Parse($prev.startedAt)).TotalHours -gt $lockMaxAgeHours
    } catch { $tooOld = $false }
  }
  if ($alive -and $tooOld) {
    Write-Host ("（清掉一把**过期**的锁：pid=$($prev.pid) 仍活着，但起于 $($prev.startedAt)，" +
      "超过 $lockMaxAgeHours 小时 ⇒ 按陈旧处理；若确有门禁在跑，这行就是误判，请复核）") -ForegroundColor DarkGray
    $alive = $false
  }
  if ($alive) {
    Write-Host "⛔ 已经有一个门禁在跑（pid=$($prev.pid)，起于 $($prev.startedAt)）。" -ForegroundColor Red
    Write-Host "   并发跑门禁会制造**假红**（见 AGENTS.md 的门禁一节）⇒ 这次**不跑**，退出码 3。" -ForegroundColor Red
    Write-Host "   确认它其实已经死了：Remove-Item `$env:TEMP\ks-gates.lock" -ForegroundColor DarkGray
    exit 3
  }
  if (-not $tooOld) {
    # ⚠ 只在**真的因为 pid 不在**才打这句（复核 2026-09-19 抓到：清过期锁后又打"pid 已不在"，
    #   而那个 pid 明明活着 —— 日志自相矛盾）。
    Write-Host "（清掉一个失效的锁：pid=$($prev.pid) 已不在）" -ForegroundColor DarkGray
  }
  Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
}
# ⚠ 锁文件**必须无 BOM**：PS 5.1 的 `Set-Content -Encoding utf8` 会写 BOM，而 node 侧
#   （`gate-lock.mjs`）用 `JSON.parse` 读它 ⇒ 遇 BOM **抛错** ⇒ 它以为"没有锁"直接放行。
#   复核（2026-09-19）实测过这条：用 `powershell.exe` 跑本脚本时冒烟侧看不到锁。
#   两边都加固：这里写无 BOM，node 侧读时也剥 BOM。
$lockToken = [guid]::NewGuid().ToString('n')
$lockJson = @{ pid = $PID; startedAt = (Get-Date).ToString('s')
               mode = $(if ($Full) { 'full' } else { 'quick' }); token = $lockToken } | ConvertTo-Json -Compress
[System.IO.File]::WriteAllText($lockPath, $lockJson, (New-Object System.Text.UTF8Encoding($false)))
# ⚠ **再入凭据 = 锁文件里的 token**（不是"环境变量说有就有"）：子步骤（`npm run smoke` →
#   `scripts/smoke-all.mjs`）也会去取**同一个**锁，它是我们拉起来的 ⇒ 必须告诉它"别取"。
#   复核（2026-09-19）指出无条件信任 `KS_GATES_LOCK_HELD=1` 等于锁形同虚设；
#   我第一版改"校验 pid 是不是祖先"，**当场把真·再入也锁死了**（进程树是
#   `pwsh → npm.cmd → node`，`process.ppid` 只给一级，走到祖父就断）⇒ 改成一次性 token。
$prevLockHeld = $env:KS_GATES_LOCK_HELD
$prevLockToken = $env:KS_GATES_LOCK_TOKEN
$env:KS_GATES_LOCK_HELD = '1'
$env:KS_GATES_LOCK_TOKEN = $lockToken
# ⚠ **官方入口自己给冒烟隔离数据目录**（复核 2026-09-19 的建议②）：`KS_DATA_DIR` 决定
#   `ks-ingest.json`/`ks-inspection.json`/`ks-chatmode.json` 落哪。老树里的冒烟可能**还没有**
#   各自的隔离（实测：复核在 35f024a 树上跑门禁，把一条假任务写进了**真实** %APPDATA%，
#   真产品下次启动会去接管它）⇒ 在这里设一次，比"写进复核约定"可靠得多。
$prevDataDir = $env:KS_DATA_DIR
$env:KS_DATA_DIR = Join-Path ([System.IO.Path]::GetTempPath()) ("ks-gates-data-" + $PID)
# ⚠ **自己布的数据目录，跑完要自己收**（2026-09-24 顺手实测）：上面那行只设了**环境变量**，
#   从来没人删**目录** ⇒ 实测 `%TEMP%` 里积了 **166 个** `ks-gates-data-*`（合计 554 MB）——
#   与 `tests/conftest.py` 那 1833 个 `ks_test_*` 是**同一类泄漏**（那边已修，这边漏了）。
#   三条边界：① 只在**这一跑成功**时收；② 失败/被中断时**留着并打印路径**（那里面可能有失败现场
#   的状态文件，删了就没法排查）；③ 只收"跑之前**不存在**的那一份"（万一 pid 复用撞上别人的
#   目录，一个字都不许碰）。
$ownDataDir = $env:KS_DATA_DIR
$ownDataDirExisted = Test-Path $ownDataDir
$ownDataDirRemovable = $false
# ── 模型缓存目录（2026-09-21 修的那条**环境假红**）──────────────────────────────
# 为什么必须有：`tests/conftest.py` 是 **session 级 autouse**，它把 `KS_DATA_DIR` 换成全新的
#   `%TEMP%\ks_test_*` ⇒ `models_dir`（默认 `<data_dir>/models`）**每次都是空的** ⇒ 每一次
#   全量 pytest 都要重新下载 BGE（~91MB；实测某次会话目录被填到 748MB）。本机
#   `ALL_PROXY=http://127.0.0.1:7897` 那个代理半死不活（端口能连、不响应）⇒ 下载**挂死**；
#   即使下载能成，也可能赶不上 `test_retrieval.py::test_vec_channel` 那一刻（该用例在基线的
#   `environmental_skip_nodeids` 里）⇒ 向量通道不可用 ⇒ **依赖检索**的两条
#   （`test_compliance.py::test_behavior_review_face_collection`、
#   `test_phase4.py::test_obligation_list_and_checklist`）降级失败。
#   ⚠⚠ **2026-09-24 更正（审计 B5 时顺手实测；上面这两个例子现在都不存在了）**：
#     ① `tests/test_compliance.py` **整个文件**随 2026-09-22 的删单批（`683c6f6`）被删除；
#     ② `test_phase4.py::test_obligation_list_and_checklist` 也已不在（文件还在、那条没了）。
#     留在这里不改会**把下一个人引去查一条不存在的用例**。教训本身仍然成立（模型没下到 ⇒
#     **依赖检索的用例**会降级失败），过期的只是"举例"。
#     ⇒ 正是这一次核对才发现白名单里那条幽灵（名单只增不减），修法与判据见
#       `tests/test_gate_baseline_whitelist.py` 与下面棘轮段新增的那条判据。
#   复核 2026-09-21 定性：与被验区间无关的环境假红（区间 `git diff --stat -- src tests` 为空）。
# 处置：`KS_MODELS_DIR`（`src/core/config.py` 的 models_dir 覆盖）指到一个**常驻**目录 ⇒ 模型只落地
#   一次。实测：那三条用例 **0.96s 全过**（原先是 218.87s 下载 / 代理挂死）。
#   seed 只从**本机已缓存的模型**拷一次（读真实缓存 → 写门禁自己的目录，**不联网**）；
#   本机没缓存过就留空，首次仍会联网下载（与今天之前的行为一致）。
$prevModelsDir = $env:KS_MODELS_DIR
$modelsDir = Join-Path ([System.IO.Path]::GetTempPath()) 'ks-gates-models'
$realModels = if ($env:APPDATA) { Join-Path (Join-Path $env:APPDATA 'KnowledgeStation') 'models' } else { '' }
$cachedBge = if ($realModels) { Join-Path $realModels 'models--Qdrant--bge-small-zh-v1.5' } else { '' }
# ⚠⚠ **2026-10-09 修（人工轮第 18 轮）—— 判据从"目录存在"改成"模型真的在里面"。**
#   原来的 `if (-not (Test-Path $modelsDir))` 有个致命弱点：一次**被强杀/拷一半**的跑会留下
#   **空骨架目录**（实测：`ks-gates-models` 只有 **12 KB**、目录树在、**0 个 onnx**；真缓存 91 MB），
#   此后**永远不再 seed** ⇒ 每条要嵌入的用例都退到"联网下载失败 + 退避重试 9s+27s"，
#   把 `INGEST_BUDGET_S`(45s) 吃光 ⇒ 实测 `test_announce_ingest` 因此 `tried=1`（期望 2）
#   ⇒ **`-Full` 恒红，而且被误读成"公告组件的真缺陷"**（交接单第 17 轮就是这么记的）。
#   ⇒ 现在：**没有可用模型就（重）seed**；seed 前先清掉空骨架。幂等、无网也可。
function Test-BgeUsable([string]$dir) {
  if (-not $dir -or -not (Test-Path $dir)) { return $false }
  $hit = Get-ChildItem $dir -Recurse -File -Force -ErrorAction SilentlyContinue |
         Where-Object { $_.Name -like '*.onnx' } | Select-Object -First 1
  return [bool]$hit
}
$modelsNote = '已有（可用）'
if (-not (Test-BgeUsable $modelsDir)) {
  if (Test-BgeUsable $cachedBge) {
    if (Test-Path $modelsDir) { Remove-Item $modelsDir -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $modelsDir | Out-Null
    Copy-Item $cachedBge $modelsDir -Recurse -Force
    $modelsNote = '刚从本机缓存 seed（未联网）'
  } else {
    $modelsNote = '本机缓存也没有 ⇒ 要联网下载（代理不通时会挂）'
  }
}
$env:KS_MODELS_DIR = $modelsDir
# ⚠ **输出编码必须钉死**（复核 2026-09-19 抓到棘轮"忽绿忽红"的根因）：Windows 控制台默认 936(GBK)，
#   而 pwsh 用 `[Console]::OutputEncoding` 解码**子进程**的 stdout ⇒ python 的 UTF-8 中文
#   （pytest 的 skip 理由）会变成 U+FFFD 乱码。乱码本身不影响计数，但**它曾经被写进基线**，
#   于是"理由集"这条判据在不同 `PYTHONIOENCODING`/代码页下比对的是不同的字符串。
#   ⇒ 全程强制 UTF-8（并把它传给 python），结束时恢复。
$prevPyIo = $env:PYTHONIOENCODING
$prevConsoleEnc = [Console]::OutputEncoding
$env:PYTHONIOENCODING = 'utf-8'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
# ⚠⚠ **`PYTEST_ADDOPTS` 也必须钉死/清掉**（2026-09-24 独立复核在我这批里实测出来的 HIGH）：
#   本脚本的棘轮与"白名单幽灵"判据，全都建立在"`-Full` 这一跑**收集到了整套用例**"之上。
#   而 `PYTEST_ADDOPTS` 能从**环境**里缩掉收集面（`-k` / `--deselect` / `--ignore` / `-m` /
#   改收集的 `-p`）。复核的真实反例（用本脚本同一套 argv，只加这一个环境变量）：
#     `$env:PYTEST_ADDOPTS='-k test_gate_baseline_whitelist'`
#     ⇒ pytest 输出 `1 failed, 1 passed, 2339 deselected`、junit 只剩 2 条
#     ⇒ `(\d+) error` 不匹配 ⇒ `[int]$null -eq 0` ⇒ **剔除门为真**
#     ⇒ `-UpdateBaseline` 把 6 条环境白名单**全剔掉，其中 5 条是合法的**（golden_set / pipeline /
#        reranker / retrieval / update_channels 被当幽灵删了）—— 而写基线那段**不受
#       `$baselineDrop` 约束**，所以**红的跑也会改写基线**，只剩一行黄字提示。
#   ⇒ 处置：像 `PYTHONIOENCODING`/`KS_DATA_DIR` 一样，**这一跑由脚本自己拥有**它 ——
#     设过就**响亮告警**并**清掉**，结束时恢复调用方原来的值（绝不静默）。
#   为什么不用"剔除前要求 `$totalRan -ge $baseTotal`"当护栏：**真删了用例**时总账本来就会掉，
#   而"用例被删 ⇒ 该剔"正是这条修法要处理的场景 ⇒ 那个条件下会把该剔的也拦住。
$prevAddopts = $env:PYTEST_ADDOPTS
if (-not [string]::IsNullOrWhiteSpace($prevAddopts)) {
  Write-Host ("⚠ 检测到 PYTEST_ADDOPTS=[{0}] ⇒ 本跑**清掉**它（它能把收集面缩掉，会让棘轮与白名单判据失准；" -f $prevAddopts) -ForegroundColor Yellow
  Write-Host "   复核 2026-09-24 实测：只加这个环境变量就能让 -UpdateBaseline 把合法白名单条目当幽灵剔掉。跑完恢复原值。）" -ForegroundColor Yellow
}
Remove-Item Env:\PYTEST_ADDOPTS -ErrorAction SilentlyContinue
$prevPyPlugins = $env:PYTEST_PLUGINS
if (-not [string]::IsNullOrWhiteSpace($prevPyPlugins)) {
  Write-Host ("⚠ 检测到 PYTEST_PLUGINS=[{0}] ⇒ 本跑**清掉**它（插件能改收集/改写结果，同样让判据失准；跑完恢复）" -f $prevPyPlugins) -ForegroundColor Yellow
}
Remove-Item Env:\PYTEST_PLUGINS -ErrorAction SilentlyContinue

$steps = @()
function Add-Step([string]$name, [string]$exe, [string[]]$argv, [string]$workdir) {
  $script:steps += [pscustomobject]@{ name = $name; exe = $exe; argv = $argv; workdir = $workdir; ok = $false; note = '' }
}

$py = Join-Path $repo '.venv\Scripts\python.exe'
$plugin = Join-Path $repo 'plugin'

# ── 自检开关（**只在验证"失败路径"本身时用**）：把门禁换成一个必定失败的假步骤，
#    用来确认"失败行 + 完整日志路径"真的会打出来。默认关。
if ($env:KS_GATES_SELFTEST -eq '1') {
  # 用真解释器而不是 `cmd /c "… ; exit 7"`：cmd 不认 `;` 作分隔符，
  # 第一版自检因此"通过"了（自检工具自己不可信，等于没自检）。
  Add-Step 'selftest（必失败）' $py @('-c', "print('FAIL  selftest-assertion'); import sys; sys.exit(7)") $repo
} elseif ($env:KS_GATES_SELFTEST -eq '2') {
  # 假绿自检（复核 2026-09-19 抓到的那条）：命令**不存在**时必须判失败并照常打汇总，
  # 而不是"弹出 try、静默退出 0"。提取树里没有 `.venv` 时踩的就是这条路。
  Add-Step 'selftest（命令不存在）' 'ks-no-such-command-xyz' @('--nope') $repo
} elseif ($env:KS_GATES_SELFTEST -eq '3') {
  # pssa-guard 的**自身**回归测试（2026-09-28 复核建议②）：判据不能零测试。
  # 跑 T1 原样件(0+版本号) / T2 未用变量(1+定位) / T3 语法错误(≠0，作 fail-open 回归锁)。
  # ⚠ 只在自检档跑、**不进正式档**——它专门测门禁本身，每次门禁都自测会拖慢且无意义。
  Add-Step 'pssa-guard-selftest（门禁自测）' 'pwsh' @('-NoProfile', '-File', (Join-Path $repo 'scripts\pssa-guard-selftest.ps1')) $repo
} else {
# 快档：按"最快能发现破坏"的顺序（tsc → mypy → 命令契约 → 全链 smoke）
Add-Step 'tsc（客户端类型）'      'npx' @('tsc', '--noEmit', '-p', 'plugin/client') $repo
Add-Step 'mypy（引擎类型）'        $py  @('-m', 'mypy') $repo
Add-Step 'verify:commands'        'npm' @('run', 'verify:commands') $plugin
# 命令层空验证的机械检测（2026-09-28 引入）。治这条：本文件 8 处 $totalForRatchet 被逐字改回
# $totalRan 时，22 条相关测试全绿零红——因为**本脚本自身没有单测**，全仓对它的引用全是注释。
# PSScriptAnalyzer 的 PSUseDeclaredVarsMoreThanAssignments 对原始件零误报、对该变异一次命中
# （本机实测；复现命令见 docs/research/TECH-PATH-2026-09-28.md §6）。
# ⚠ 只扫 scripts/ 下 .ps1、只判那一条规则（其余误报源见 scripts/pssa-guard.ps1 头注）；
#   未装 PSScriptAnalyzer 时**判失败、不跳过**（本仓纪律：SKIP ≠ 通过）。
Add-Step 'pssa-guard（命令层）'   'pwsh' @('-NoProfile', '-File', (Join-Path $repo 'scripts\pssa-guard.ps1')) $repo
Add-Step 'smoke（全链）'           'npm' @('run', 'smoke') $plugin
if ($Full) {
  Add-Step 'pytest（引擎用例）'     $py  @('-m', 'pytest', '-q', '-rs', '--durations=10', "--junitxml=$junitPath") $repo
  Add-Step '引擎门禁（uvicorn）'     $py  @('scripts/verify-engine-uvicorn.py') $repo
  # 真 DSH 的两条（放最后：最慢、最可能因环境红）。都需要检出 —— 见文件头的"环境前提"。
  # ⚠ 走 `node`（不是 npm script）：这两条**只**属于 -Full，不进 plugin/scripts/smoke-all.mjs
  #   （冒烟链要保持零外部依赖）。
  Add-Step 'verify-tools-real（真 ToolRuntime）' 'node' @('plugin/scripts/verify-tools-real.mjs') $repo
  Add-Step '真宿主 e2e（临时 profile）' 'node' @('plugin/scripts/e2e-install-compose.mjs') $repo
}
}

$results = @()
$pytestPassed = $null
$pytestSkipped = $null
# ⚠ 失败/错误也必须数（2026-09-21 复核抓到）：原先只抓 `passed`/`skipped`，于是
#   `2 failed + 2139 passed + 5 skipped = 2146 = 基线` 会被读成"总账 2144 < 2146"，
#   把"2 条失败"**误报成**"少收集了 2 条" —— 判据方向反了（失败 ≠ 少跑）。
$pytestFailed = $null
$pytestErrors = $null
# ⚠ v4（2026-09-24 审计 B5）：pytest 那一步的**全表** nodeid（不止 skip 的那些）。
#   白名单"幽灵条目"判据靠它：白名单里的节点必须这一跑**真的被收集到**。
#   为什么必须有：`-UpdateBaseline` 原来把旧白名单**逐字抄回** ⇒ 名单**只增不减**，
#   用例被删/改名之后名字还在 ⇒ 将来**同名**的用例以非环境原因跳过时，门禁会当
#   "已知的环境跳过"放过去（永久放水）。实测到的第一条幽灵：
#   `tests.test_compliance::test_behavior_review_face_collection`（整个文件已被 683c6f6 删除）。
$allNodeIds = @()
#: "这条白名单节点还在不在"的判据（在 pytest 那一步按 junit 建好，棘轮与 -UpdateBaseline 共用）。
$envIdAlive = $null
$hardError = $null

try {
  foreach ($s in $steps) {
    Write-Host ""
    Write-Host ("── {0} ─────────────────────────────────" -f $s.name) -ForegroundColor Cyan
    # ⛔ **"命令不存在"必须判失败，不能变成绿**（2026-09-19 复核抓到的假绿）：
    #   原来直接 `& $s.exe @(…)`；命令不存在时它是**非终止错误**，不会写入 `$LASTEXITCODE`
    #   ⇒ `$code` 拿到的是**上一步残留的退出码**（常常是 0）⇒ 这一步被判"通过"。
    #   受害面恰好是最要紧的地方：**提取树里没有 `.venv`**（复核与冻结验证都在那里跑），
    #   `mypy` 那步的 `python.exe` 找不到 ⇒ 门禁恒绿。
    #   ⇒ 三步一起：① `Get-Command` 预检；② 每次调用前把 `$LASTEXITCODE` 显式清空；
    #     ③ 调用后仍为 `$null` ⇒ 判失败（"没跑"≠"通过"）。
    $code = $null
    $out = @()
    $exePath = $null
    $skipReasonsOfStep = @()
    try { $exePath = (Get-Command $s.exe -ErrorAction Stop).Source } catch { $exePath = $null }
    if (-not $exePath) {
      $out = @("⛔ 找不到命令 '$($s.exe)' ⇒ 这一步**根本没跑**（判失败，不是跳过）",
               "   检查 PATH / venv 是否存在（提取树里通常没有 .venv）")
      $code = 127
    } else {
      Push-Location $s.workdir
      try {
        $global:LASTEXITCODE = $null
        $stepSw = [Diagnostics.Stopwatch]::StartNew()
        $out = & $exePath @($s.argv) 2>&1
        $stepSw.Stop()
        $code = $LASTEXITCODE
      } finally { Pop-Location }
      if ($null -eq $code) { $code = 126 }   # 没设退出码 ⇒ 也判失败
      # ⚠ **耗时异常必须当场喊出来**（2026-09-21 实测踩到）：那次 `pytest` 跑了 **4871 秒**，
      #   其中 **4762 秒**全在 `tests/test_golden_gate.py::test_golden_gate_baseline_present`
      #   （同一个文件**单跑只要 8.1 秒** ⇒ 顺序/状态依赖的性能病，机制未查明）。
      #   当时**没有任何提示**：只看到门禁"跑了很久"。⇒ 任何一步超过阈值就打印告警，
      #   并提醒去看 `--durations`（pytest 那步已带上 `--durations=10`）。
      $stepSeconds = [math]::Round($stepSw.Elapsed.TotalSeconds, 1)
      $slowBudget = if ($s.name -like 'pytest*') { 600 } else { 240 }
      if ($stepSeconds -gt $slowBudget) {
        Write-Host ("   ⚠ 这一步耗时 {0}s（超过本步预算 {1}s）⇒ 性能异常，不是「正常的慢」；" -f $stepSeconds, $slowBudget) -ForegroundColor Yellow
        Write-Host "     查该步完整输出里的 --durations 段（pytest 那步带 --durations=10），并留意环境（模型缓存/代理）。" -ForegroundColor Yellow
      }
    }
    $text = ($out | Out-String)

    # 让输出仍然可见（但只留尾部，避免刷屏）
    $tail = ($out | Select-Object -Last 6)
    $tail | ForEach-Object { Write-Host ("   " + $_) }

    # ⛔ **失败时必须给出可诊断的证据**（2026-09-19 补）：
    #   全量跑里 `smoke-chatmode` 红过一次 172/173，而当时只留了尾部 6 行 ⇒ **哪条断言红的
    #   就此丢失**，只能靠单独重跑猜。假红的根因分析恰恰需要那条断言的原文。
    #   ⇒ 失败步骤：① 把 FAIL/error 行**当场**打出来（不必再翻日志）；② 完整输出落一个文件并报路径。
    if ($code -ne 0) {
      $failLines = @($out | Where-Object { $_ -match '^\s*(FAIL|FAILED|ERROR)\b' } | Select-Object -First 12)
      if ($failLines.Count -gt 0) {
        Write-Host "   ── 失败行 ──" -ForegroundColor Red
        $failLines | ForEach-Object { Write-Host ("   " + $_) -ForegroundColor Red }
      }
      $logDir = Join-Path ([System.IO.Path]::GetTempPath()) 'ks-gates-logs'
      New-Item -ItemType Directory -Force -Path $logDir | Out-Null
      $logPath = Join-Path $logDir ("{0}-{1}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'),
        ($s.name -replace '[^\w\-]', '_'))
      $text | Set-Content -Path $logPath -Encoding utf8
      Write-Host ("   ⛔ 该步完整输出：{0}" -f $logPath) -ForegroundColor Red
    }

    # pytest 的"只涨不跌"要读数字与 **skip 的 nodeid**（棘轮判据，见下面那段）。
    if ($s.name -like 'pytest*') {
      $m = [regex]::Match($text, '(\d+) passed')
      if ($m.Success) { $pytestPassed = [int]$m.Groups[1].Value }
      $m2 = [regex]::Match($text, '(\d+) skipped')
      if ($m2.Success) { $pytestSkipped = [int]$m2.Groups[1].Value }
      # 失败/错误：**必须数**，否则"有失败"会被棘轮读成"少跑了"（见上面声明处的说明）。
      $m3 = [regex]::Match($text, '(\d+) failed')
      if ($m3.Success) { $pytestFailed = [int]$m3.Groups[1].Value }
      $m4 = [regex]::Match($text, '(\d+) error')
      if ($m4.Success) { $pytestErrors = [int]$m4.Groups[1].Value }
      $pytestText = $text
      # ⚠ **判据的键 = pytest 的 nodeid**（`tests.test_x::test_y`），**不是** `文件:行号`（复核 v2 打回）：
      #   行号会随"在文件顶部加一行注释"位移 ⇒ 零回归也判红（复核实测：加一行注释，站点从 :72 变 :73，
      #   当场 ⛔）。用 `--junitxml` 拿机器可读结果。
      # ⚠ **更正（复核 v3 打回，2026-09-20）**：这里原写"nodeid 与编码、行号、绝对/相对路径**全都无关**"，
      #   那句话**超出了证据**：① **收集期跳过**（`pytest.skip(..., allow_module_level=True)` 之类）时
      #   junit 的 `classname=""`、只有模块名 ⇒ 实际键是 `::<模块名>`，与普通用例的 nodeid 不同形；
      #   ② `classname` 由 **rootdir 相对路径**派生 ⇒ 只在**固定调用方式**（cwd/rootdir 不变）下才稳定。
      #   能站住的只是：**行号位移不再影响判据**（那正是 v2 的问题）。
      $skipNodeIds = @()
      $allNodeIds = @()
      $junitError = $null
      if (Test-Path $junitPath) {
        try {
          [xml]$jx = Get-Content $junitPath -Raw
          # ⚠ 全表先拿：junit 的 `//testcase` 涵盖 passed / skipped / failed 三种 ⇒
          #   "在表里"≈"这一跑真的被收集到"（`-Full` 是整套跑）。幽灵判据靠它。
          $allNodeIds = @($jx.SelectNodes('//testcase') |
            ForEach-Object { "$($_.classname)::$($_.name)" } | Sort-Object -Unique)
          $skipNodeIds = @($jx.SelectNodes('//testcase') |
            Where-Object { $_.SelectSingleNode('skipped') -ne $null } |
            ForEach-Object { "$($_.classname)::$($_.name)" } | Sort-Object -Unique)
        } catch { $junitError = "junitxml 解析失败：$junitPath（$($_.Exception.Message)）" }
      } else {
        $junitError = "没找到 junitxml：$junitPath"
      }
      # ⚠⚠ **2026-10-09（人工轮第 18 轮）补：汇总行拿不到时，从 junit 兜底。**
      #   为什么需要：pytest 的汇总行（"N passed"）可能**被外来输出冲掉** ——
      #   本机实测：收尾清 tmp 时往 stdout 注入了一条
      #   `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED] {"count":55,...}`（沙箱的删除守卫），
      #   把汇总行挤没了 ⇒ `$pytestPassed` 为 $null ⇒ 棘轮报"拿不到 passed 数字" ⇒ **整套判红**，
      #   而 junit **就在那里、数字齐全**（实测 `tests=2697 failures=2 skipped=3`）。
      #   ⇒ 汇总行缺失时用 junit 反推：`passed = tests − failures − errors − skipped`。
      #   ⚠ **这不是放宽**：junit 是 pytest 自己写的机器可读结果，比 stdout 正则**更权威**；
      #     而且**只在日志正则失败时**才走这条路（日志能解析时仍以日志为准，行为一字不变）。
      if ($null -eq $pytestPassed -and $null -eq $junitError -and $allNodeIds.Count -gt 0) {
        try {
          $sumTests = 0; $sumFail = 0; $sumErr = 0; $sumSkip = 0
          foreach ($sn in $jx.SelectNodes('//testsuite')) {
            $sumTests += [int]$sn.GetAttribute('tests')
            $sumFail += [int]$sn.GetAttribute('failures')
            $sumErr += [int]$sn.GetAttribute('errors')
            $sumSkip += [int]$sn.GetAttribute('skipped')
          }
          if ($sumTests -gt 0) {
            $pytestPassed = $sumTests - $sumFail - $sumErr - $sumSkip
            $pytestFailed = $sumFail
            $pytestErrors = $sumErr
            $pytestSkipped = $sumSkip
            Write-Host ("   ℹ 汇总行拿不到（stdout 被冲掉）⇒ 从 junit 兜底：passed={0} failed={1} errors={2} skipped={3}" -f `
              $pytestPassed, $pytestFailed, $pytestErrors, $pytestSkipped) -ForegroundColor Yellow
          }
        } catch { $junitError = "junit 计数兜底失败：$($_.Exception.Message)" }
      }
      # ⚠ **解析不到 ⇒ 报错，不许静默丢弃**（复核 v2 指出的第二个洞）：若汇总说 skipped=N，
      #   而 junit 里只认出 M≠N 条，那判据就不可信 —— 判红并说清差在哪，别"当没事发生"。
      if ($null -eq $junitError -and $skipNodeIds.Count -ne [int]$pytestSkipped) {
        $junitError = "junit 里认出 skipped=$($skipNodeIds.Count) 条，汇总说 skipped=$pytestSkipped 条 ⇒ 判据不可信"
      }
      # ⚠ v4（2026-09-24 审计 B5）：白名单节点的"还在不在"判据（棘轮与 -UpdateBaseline 共用）。
      #   两种都算"在"：① 这一跑收集到了它；② **收集期跳过**的模块也在名单里时，junit 的键是
      #   `::<模块>`（`classname=""`）⇒ 按模块名兜住，否则一条**合法**的收集期跳过会被误判成幽灵。
      #   ⚠ **就地更正（2026-09-24 独立复核实测）**：上面这条注释原文只说了"收集期跳过"会产出
      #   `::<模块>` —— **收集错误（import 崩）同样产出 `classname=""`**。两者都要靠"按模块兜住"
      #   才不至于误伤；而副作用是：**这个模块里的任何名字都会被判"在"** ⇒ 该模块内真出现幽灵时
      #   剔不掉（复核判 MED；它对"防误伤"是必要的，且今天不可达 —— 唯一一处模块级 importorskip
      #   在 `test_retrieval.py:307` 的函数体内）。**登记为残余**，不在这条分支上继续加码。
      $collectedModules = @($allNodeIds | Where-Object { $_ -like '::*' } |
        ForEach-Object { $_.Substring(2) } | Sort-Object -Unique)
      $envIdAlive = {
        param([string]$id)
        if ($allNodeIds -contains $id) { return $true }
        $mod = ($id -split '::')[0]
        if ($mod -ne '' -and ($collectedModules -contains $mod)) { return $true }
        return $false
      }
      $skipReasonsOfStep = @($skipNodeIds)
    }
    $ok = ($code -eq 0)
    $results += [pscustomobject]@{ name = $s.name; ok = $ok; code = $code
      skipReasons = $(if ($s.name -like 'pytest*') { $skipReasonsOfStep } else { @() })
      note = $(if ($s.name -like 'pytest*' -and $null -ne $pytestPassed) { "passed=$pytestPassed skipped=$pytestSkipped failed=$([int]$pytestFailed) errors=$([int]$pytestErrors)" } else { "exit=$code" }) }
    Write-Host ("   ⇒ {0}" -f $(if ($ok) { '✅ 通过' } else { "⛔ 失败（exit=$code）" })) -ForegroundColor $(if ($ok) { 'Green' } else { 'Red' })
  }
} catch {
  # 兜底：任何**逃出**上面循环的终止错误（例如某个步骤把控制流弹出去）都必须留痕，
  # 否则汇总段根本不执行、脚本以 0 退出 —— 那就是"门禁假绿"的另一种形态。
  $hardError = $_
  Write-Host ("⛔ 门禁执行中断：{0}" -f $hardError.Exception.Message) -ForegroundColor Red
}

try {
  # ── 只涨不跌（读基线比对） ────────────────────────────────────────────────
  # ⚠ 棘轮被复核打回过两次，这里是**第三版**，把每条判据的**作用**说清（别再冒领功劳）：
  #     ① **总账**（`passed+skipped ≥ 基线总账`）只兜**删用例 / 少收集**；
  #        ⚠ 它**兜不住** `passed → skipped` 的翻转（那种翻转下总账恒等不变）——v2 曾把这条写成
  #        "总账兜翻转"，数学上就是错的（复核 v3 打回，已更正）。
  #     ② **skip nodeid 规则**才是兜"某个用例开始被 skip"的那条（白名单外的新 nodeid ⇒ 红）。
  #     ③ **junit 解析失败 / 与汇总数字不符** ⇒ 直接红（判据不可信时不许当绿）。
  $baselineDrop = $false
  $why = @()
  $skipNodeIds = @($results | Where-Object { $_.name -like 'pytest*' } |
    ForEach-Object { $_.skipReasons } | Where-Object { $_ } | Sort-Object -Unique)
  $totalRan = $null
  # ⚠ 总账必须把 **failed / errors 算进去**（2026-09-21 复核打回）：原先只加 passed+skipped，
  #   于是"2 failed + 2139 passed + 5 skipped = 2146=基线"被读成"总账 2144 < 2146" ⇒
  #   **把失败误报成少收集**（判据方向反了）。数字自洽后，失败由该步退出码兜住，原因也说得清。
  if ($null -ne $pytestPassed) {
    $totalRan = $pytestPassed + ([int]$pytestSkipped) + ([int]$pytestFailed) + ([int]$pytestErrors)
  }

  # ── 棘轮**口径**：只统计**受版本控制**的用例（2026-09-26 复核 MED-1 的"定时炸弹"）──────
  # 为什么：实测总数里可能含**未跟踪文件**的用例 —— 本仓实测 `tests/test_jev_cn_baseline.py`
  #   不被 git 跟踪、却贡献 5 条。两层恶性后果：
  #     ① 记进基线 ⇒ 那份文件一被删（git clean / 提取树天然没有 / 别人清理），总账掉 5、
  #        **棘轮假红**，而且红在一个**不归本仓控制**的文件上；
  #     ② 反过来，**手工把基线调低**去躲这个假红（我 2026-09-25 就是这么干的）⇒
  #        紧接着新增用例就造出**余量** ⇒ **余量内的用例可以被静默删掉而棘轮不红**
  #        （复核量化：余量 0 → 6，那 6 条正是"保护提问证据不被销毁"的测试）。
  # ⇒ 修法：口径搬进代码 —— **比较与记账两侧都扣掉未跟踪的**，于是"有它"与"没它"
  #    得到**同一个数**，余量回到 0，删任何一条都红。助手：`scripts/gates-tracked-total.py`
  #    （它自己有判据，含反向：不扣减时那两个数必须不同）。
  # ⚠ **方向要说对**（2026-09-26 复核打回——我原来这里写反了）：`totalForRatchet = totalRan − 未跟踪数`
  #   ⇒ **少扣只会放宽**（结果 ≥ 真值）⇒ **不可能假红**；能假红的只有**多扣**。
  #   所以"算式没跑成"的真正危害不是"误判用例被删"，而是**静默放宽**，
  #   外加**记账时把实测总数写回基线 ⇒ 把已拆的定时炸弹原样装回去**。
  # ⚠ 自检开关（与 `KS_GATES_SELFTEST` 同一约定）：把助手换成别的路径，用来**实测错误路径**。
  $trackedExcluded = 0
  $caliberOk = $false
  $caliberWhy = ""
  if ($null -ne $pytestPassed -and $allNodeIds.Count -gt 0 -and (Test-Path $junitPath)) {
    if ($allNodeIds.Count -ne $totalRan) {
      $caliberWhy = "junit 条目 $($allNodeIds.Count) ≠ 总账 $totalRan（节点表不全）"
    } else {
      $caliberScript = if ($env:KS_GATES_SELFTEST_CALIBER) { $env:KS_GATES_SELFTEST_CALIBER }
                       else { Join-Path $repo 'scripts\gates-tracked-total.py' }
      $raw = $null
      try { $raw = & $py $caliberScript --junit $junitPath --repo $repo 2>$null } catch { $raw = $null }
      $caliber = $null
      if ($raw) { try { $caliber = $raw | ConvertFrom-Json } catch { $caliber = $null } }
      # ⚠⚠ **必须逐字段验**（复核 MED-1 实测）：助手崩溃时 stdout 为空 ⇒ `ConvertFrom-Json`
      #   得 `$null` **而不抛** ⇒ 原来那个 `catch` 对**最可能的失败形态是死代码**，
      #   而且还会打出与事实相反的"没有未跟踪文件里的用例"。这里显式验字段，不留这种空间。
      if ($null -eq $caliber -or $null -eq $caliber.untracked -or $null -eq $caliber.collected -or
          $null -eq $caliber.unmapped) {
        $caliberWhy = "口径助手没有给出可用结果（stdout 空或字段缺失）"
      } elseif ([int]$caliber.untracked -ge $totalRan) {
        # ⚠ **多扣守卫**（2026-09-26 复核 L-4）：上面注释说"能假红的只有**多扣**"——
        #   那就必须把多扣挡住，否则那句只是话。扣减数 ≥ 总账显然不合理（会算出负的真值 ⇒ 假红）。
        $caliberWhy = "扣减数 $([int]$caliber.untracked) ≥ 总账 $totalRan（多扣 ⇒ 会假红，拒用）"
      } elseif ([int]$caliber.unmapped -gt 0) {
        # ⚠ `unmapped>0` = **有节点认不出文件** ⇒ 口径**算不全**，不许说成"没有未跟踪用例"。
        #   （复核 MED-2 实测：带点目录如 `tests/v1.2/` 会让盲拆点分名失败，
        #    untracked 用例可**逃过**扣减、凭空造余量。本仓今日未占坑。）
        #   宁愿整跑退回旧口径，也不许口径**看起来生效**而实际漏扣。
        $caliberWhy = "$([int]$caliber.unmapped) 个节点认不出文件（口径算不全）"
      } else {
        $trackedExcluded = [int]$caliber.untracked
        $caliberOk = $true
        if ($trackedExcluded -gt 0) {
          Write-Host ("   棘轮口径：扣掉**未跟踪文件**里的 {0} 条用例 ⇒ 计 {1}（实测总数 {2}）" -f `
            $trackedExcluded, ($totalRan - $trackedExcluded), $totalRan) -ForegroundColor DarkGray
          $caliber.untracked_files.PSObject.Properties | ForEach-Object {
            Write-Host ("      − {0}：{1} 条" -f $_.Name, $_.Value) -ForegroundColor DarkGray
          }
        } else {
          Write-Host "   棘轮口径：没有未跟踪文件里的用例（计 $totalRan）" -ForegroundColor DarkGray
        }
      }
    }
  } else {
    $caliberWhy = "拿不到节点表或没有 junit"
  }
  if (-not $caliberOk) {
    Write-Host ("   ⚠ 棘轮口径**这一跑没生效**：{0}" -f $caliberWhy) -ForegroundColor Yellow
    Write-Host ("       ⇒ 按**实测总数** {0} 判（更宽松、**不会假红**）；⚠ **本跑不许记基线**（见下）" -f $totalRan) -ForegroundColor Yellow
  }
  #: 棘轮**判据用的**总账（口径生效时 = 实测总数 − 未跟踪用例数）
  $totalForRatchet = if ($caliberOk) { $totalRan - $trackedExcluded } else { $totalRan }
  if ($null -ne $pytestPassed) {
    if (Test-Path $baselinePath) {
      $base = Get-Content $baselinePath -Raw | ConvertFrom-Json
      $baseTotal = [int]$base.pytest_total
      if ($baseTotal -le 0) { $baseTotal = [int]$base.pytest_passed + [int]$base.pytest_skipped }
      if ($totalForRatchet -lt $baseTotal) {
        $why += ("总账 {0} < 基线 {1}（passed {2} + skipped {3} + failed {4} + errors {5}；口径：{6}）" -f `
          $totalForRatchet, $baseTotal, $pytestPassed, $pytestSkipped, [int]$pytestFailed,
          [int]$pytestErrors, $(if ($caliberOk) { "只算受版本控制的用例，已扣 $trackedExcluded 条未跟踪" } else { "实测总数（**口径未生效**：$caliberWhy）" }))
      }
      # 环境类 skip 白名单（基线里声明）：它们**随环境出现/消失是正常的**，不当回归。
      # 白名单**外**的**新** nodeid ⇒ 红（有人新加了一条跳过，或某个依赖坏了让用例开始 skip）。
      $envIds = @($base.environmental_skip_nodeids)
      $knownIds = @($base.skip_nodeids)
      $newIds = @($skipNodeIds | Where-Object { $knownIds -notcontains $_ -and $envIds -notcontains $_ })
      if ($newIds.Count -gt 0) {
        $why += ("出现基线里没有的 skip nodeid（且不在环境白名单）：{0}" -f ($newIds -join ' / '))
      }
      # ⚠ **v4（2026-09-24 审计 B5）：白名单"只增不减"的反面判据。**
      #   环境白名单里每一条都必须**这一跑真的被收集到** —— 名字还在、用例已被删/改名 ⇒
      #   **幽灵条目**，而幽灵正是"永久放水"的载体：将来**同名**的用例以非环境原因跳过时，
      #   上面那条 `$newIds` 判据会把它当"已知的环境跳过"放过去（判据自己把洞盖上了）。
      #   拿不到节点表（junit 缺失/解析失败）时**不许判**（那种情况已由 `$junitError` 判红），
      #   否则会把"表没拿到"误报成"白名单里全是幽灵"。
      if ($null -eq $envIdAlive -or $allNodeIds.Count -eq 0) {
        Write-Host "   ⚠ 没拿到 junit 节点表 ⇒ 白名单幽灵判据**这一跑没判**（不是通过；已由 junit 那条判红）" -ForegroundColor Yellow
      } else {
        $ghostIds = @($envIds | Where-Object { -not (& $envIdAlive $_) })
        if ($ghostIds.Count -gt 0) {
          $why += ("环境白名单里有这一跑**根本没收集到**的节点（幽灵条目 ⇒ 只会放水）：{0}" -f ($ghostIds -join ' / '))
        }
      }
      if ($null -ne $junitError) { $why += $junitError }
      if ($why.Count -gt 0) {
        Write-Host ""
        Write-Host ("⛔ **只涨不跌被破**：" + ($why -join '；')) -ForegroundColor Red
        $baselineDrop = $true
      } else {
        $msg = "   pytest 总账 $totalForRatchet ≥ 基线 $baseTotal（passed $pytestPassed / skipped $pytestSkipped / failed $([int]$pytestFailed) / errors $([int]$pytestErrors)），"
        $msg += "skip nodeid 全在基线或环境白名单内"
        Write-Host $msg -ForegroundColor Green
        if ($totalForRatchet -gt $baseTotal) {
          Write-Host ("   （比基线多 $($totalForRatchet - $baseTotal) 条 ⇒ 新增用例后请 -UpdateBaseline 记一次）") -ForegroundColor DarkGray
        }
      }
    } else {
      # ⚠ **没有基线文件 ⇒ 判红，不许静默放行**：删掉（或忘了提交）`gates-baseline.json` 就等于
      #   把"只涨不跌"整条关掉、而且**没有任何提示**。第一次跑用 `-UpdateBaseline` 记一次即可。
      if ($UpdateBaseline) {
        Write-Host "   （还没有基线文件 ⇒ 这次 -UpdateBaseline 会记一份）" -ForegroundColor DarkGray
      } else {
        $why += "没有基线文件（棘轮无从判定）"
        Write-Host "⛔ 没有基线文件 ⇒ 棘轮无从判定（不许静默放行）；用 -UpdateBaseline 记一次" -ForegroundColor Red
        $baselineDrop = $true
      }
    }
    if ($UpdateBaseline) {
      # ⚠ 键名与既有文件保持一致（`pytest_*` 前缀）——文档里曾写成 `{passed,skipped,total}`，
      #   与真实文件不符（复核 2026-09-19 抓到）。
      # ⚠ v3：键改成 **nodeid**（不再用 `文件:行号`，行号会随编辑位移导致假红）。
      # ⚠ **v4（2026-09-24 审计 B5）：环境白名单要"剔除已消失的节点"** ——
      #   原实现把旧白名单**逐字抄回**，于是名单**只增不减**：用例被删/改名之后名字还在，
      #   将来同名的用例以非环境原因跳过时，门禁会当"已知的环境跳过"放过去（永久放水）。
      #   剔除的两个前提（缺一不可）：① 这一跑真拿到了节点表；② **没有收集错误**
      #   （`$pytestErrors -eq 0` —— 注意**不是** `$pytestFailed`：用例"断言失败"不影响
      #   "它被收集到了"这个事实，而且幽灵条目本身会让 `test_gate_baseline_whitelist.py`
      #   失败 ⇒ 用 failed 当门槛会变成"幽灵让剔除永远不触发"的死循环，等于没修。
      #   收集错误（import 崩了）才会让一批用例集体"看起来消失"，那种情况必须不剔。
      #   ⚠⚠ **就地更正（2026-09-24 独立复核实测）—— 我上面这句归因是错的**：
      #     · "收集错误 ⇒ 不剔"这个**结论**对，但**承重墙不是** `errors==0`，而是
      #       `$pytestPassed -eq $null`（pytest 收集错误会**中断会话**、输出里没有 `N passed`
      #       ⇒ 这个 `if ($UpdateBaseline)` 所在的整块棘轮**根本不执行**）。
      #     · `errors==0` 真正承重的只有"**运行期** error 且 passed>0"（fixture 崩那种；
      #       复核实测 `1 failed, 2 passed, 1 error` ⇒ 门=假 ⇒ 不剔）。
      #     · 而**缩掉收集面**这种事，`errors` 是 0、passed 也有 ⇒ 门为真 —— 复核用它真跑出
      #       一条 HIGH：`PYTEST_ADDOPTS='-k …'` ⇒ junit 只剩 2 条 ⇒ 6 条白名单**全被剔掉**
      #       （5 条合法）。⇒ 真正的护栏是脚本开头**把 `PYTEST_ADDOPTS`/`PYTEST_PLUGINS` 清掉**
      #       （见文件上半部那段），不是这个 `errors==0`。
      #     · 另：这道门**不看 `$junitError`** —— junit 解析成功但 skip 计数与汇总不符时
      #       （上面已判"判据不可信"）剔除照样会跑。**登记为残余**（未造现场）。
      $envKept = @()
      if ($null -ne $base -and $base.environmental_skip_nodeids) {
        $envKept = @($base.environmental_skip_nodeids)
      }
      if ($envKept.Count -gt 0) {
        if ($null -ne $envIdAlive -and $allNodeIds.Count -gt 0 -and [int]$pytestErrors -eq 0) {
          $envDropped = @($envKept | Where-Object { -not (& $envIdAlive $_) })
          if ($envDropped.Count -gt 0) {
            $envKept = @($envKept | Where-Object { & $envIdAlive $_ })
            Write-Host ("   ✅ 白名单剔除 {0} 条**这一跑没收集到**的节点（「只增不减」这个洞就是这么来的）：" -f $envDropped.Count) -ForegroundColor Yellow
            $envDropped | ForEach-Object { Write-Host ("      − " + $_) -ForegroundColor Yellow }
          }
        } else {
          Write-Host ("   ⚠ 这一跑有**收集错误**（errors={0}）或没拿到节点表 ⇒ 白名单**不剔除**（收集不全时凭它剔会误删；宁可先不剔）" -f [int]$pytestErrors) -ForegroundColor DarkGray
        }
      }
      # ⚠ **记账也用棘轮口径**（2026-09-26，修复核 MED-1 的"定时炸弹"）：
      #   原先这里写 `$totalRan`（实测总数）⇒ 未跟踪文件的用例被钉进基线 ⇒
      #   ① 那份文件一被删就假红；② 我手工调低去躲它 ⇒ 造出"可静默删用例"的余量。
      #   现在两侧同口径 ⇒ "有它/没它"同一个数、余量回到 0。
      # `pytest_passed` 按 `总账 − skipped − failed − errors` **推出**，让文件自洽
      #   （它是信息性字段；判据只用 `pytest_total`）。
      # ⚠⚠ **口径没生效时不许把实测总数写进基线**（2026-09-26 复核 MED-1 的要害）：
      #   写进去 = 把"未跟踪文件的用例"钉进棘轮 ⇒ ① 那文件一被删就假红；
      #   ② **把已拆的定时炸弹原样装回去**（复核实测：非 git 树/助手崩溃时正是这条路）。
      #   ⇒ 此时**整组"总数相关"字段一律沿用旧值**（total / passed / skipped /
      #     untracked_excluded / caliber_applied —— 只留新值会让文件**自相矛盾**：
      #     我第一版就写成"total=2527（旧）但 excluded=0（新）"，读的人会以为 2527 含全部用例）。
      #     白名单与 skip 名单、updatedAt 照常更新；连可沿用的旧值都没有 ⇒ **本次不写盘**。
      $totalToRecord = $totalForRatchet
      $prevExcluded = $trackedExcluded
      $prevApplied = $caliberOk
      #: 沿用旧的 passed/skipped（口径没生效时整组都要用旧值 —— 复核 L-1 实测：
      #:   我第一版只沿用了 total/excluded/applied，passed/skipped 却是这一跑新算的，
      #:   于是文件出现"9999 配 9995"这种组合，而我的注释却写着"整组沿用" —— **文字与代码不符**）。
      $prevPassed = [int]$totalForRatchet - [int]$pytestSkipped - [int]$pytestFailed - [int]$pytestErrors
      $prevSkipped = $pytestSkipped
      if (-not $caliberOk) {
        $prev = $null
        if (Test-Path $baselinePath) {
          try { $prev = Get-Content $baselinePath -Raw | ConvertFrom-Json } catch { $prev = $null }
        }
        if ($null -eq $prev -or [int]$prev.pytest_total -le 0) {
          # ⚠ **复核 L-3：这里原写"棘轮仍按'没有基线'判红"，那句是假的** ——
          #   下面比较会把 `pytest_total ≤ 0` 兜底成 `passed+skipped` ⇒ 实际判**绿**、
          #   而且每跑都印一次假话。现在**真的判红**（口径没生效 + 无可沿用的旧值
          #   ⇒ 无从判定，按本脚本"'没跑'≠'通过'"的教条）。
          $why += "口径没生效，且基线里没有可沿用的总账 ⇒ 棘轮无从判定"
          $baselineDrop = $true
          Write-Host "⛔ 口径没生效，且没有可沿用的旧总账 ⇒ **本次不写基线**，且**棘轮判红**（'没跑'≠'通过'）" -ForegroundColor Red
          $totalToRecord = -1
        } else {
          Write-Host ("⛔ 口径没生效 ⇒ 基线**总账相关字段整体沿用旧值**（total {0} / passed {1} / skipped {2} / 另扣 {3} / 口径生效 {4}），**不写**实测总数 {5}（否则定时炸弹复活）" -f `
            [int]$prev.pytest_total, [int]$prev.pytest_passed, [int]$prev.pytest_skipped, [int]$prev.untracked_excluded, $prev.caliber_applied, $totalRan) -ForegroundColor Red
          $totalToRecord = [int]$prev.pytest_total
          $prevExcluded = [int]$prev.untracked_excluded
          $prevApplied = [bool]$prev.caliber_applied
          $prevPassed = [int]$prev.pytest_passed
          $prevSkipped = [int]$prev.pytest_skipped
        }
      }
      if ($totalToRecord -ge 0) {
        @{ pytest_passed = $prevPassed
           pytest_skipped = $prevSkipped; pytest_total = $totalToRecord
           untracked_excluded = $prevExcluded
           caliber_applied = $prevApplied
           skip_nodeids = $skipNodeIds
           environmental_skip_nodeids = $envKept
           runLive = [bool]$env:RUN_LIVE
           updatedAt = (Get-Date).ToString('s') } | ConvertTo-Json -Depth 4 |
          Set-Content -Path $baselinePath -Encoding utf8
        # ⚠ 这里必须印 `$prevPassed/$prevSkipped`（**实际写进文件的那两个值**），
        #   不许现算 —— 现算会和文件打架：实测把基线 `passed` 做旧成 1111 后，
        #   文件里是 1111、而这行印 2525（同一类"文字与代码不符"，复核 L-1 的兄弟）。
        Write-Host ("   基线已更新：总账=" + $totalToRecord + "（passed=" + $prevPassed + " skipped=" + $prevSkipped + "，另扣未跟踪 " + $prevExcluded + " 条；口径生效=" + $prevApplied + "；skip nodeid " + $skipNodeIds.Count + " 个，环境白名单 " + $envKept.Count + " 个）") -ForegroundColor Yellow
      }
    }
  } elseif ($Full) {
    # ⛔ **不许在"没跑出数字"时静默放行**（复核 v3 的对抗性反例 M3，2026-09-20 修）：
    #   上面整块棘轮（总账 / skip nodeid / junit 一致性）原来都被 `if ($null -ne $pytestPassed)`
    #   罩住 ⇒ 一旦 pytest 输出里**没有 `N passed`**，三条判据**一条都不执行**，而汇总仍打
    #   "✅ 棘轮（只涨不跌）"、明细行写 "pytest 没跑出数字" ⇒ **判据全关却报绿**。
    #   复核实跑的反例（M3_EXIT=0）：`PYTEST_ADDOPTS='-p allskip_plugin'`（插件给每个 item 加 skip）
    #   ⇒ pytest **exit 0**、输出只有 `2180 skipped`、junit 2180 条 skipped 且**条数相符**
    #   ⇒ 2175 条白名单外的新 skip nodeid **一个都没判**，门禁报"6/6 步通过 · ✅ 棘轮"。
    #   ⇒ 现在：拿不到 `N passed` 就**判红**（"没跑出数字"≠"通过"，与"命令不存在"同一立论）。
    $why += "pytest 输出里没有 'N passed'（只有 skipped、或输出被改写）⇒ 总账与 skip 判据都无从判定"
    $tailLines = @($pytestText -split "`r?`n" | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 3)
    Write-Host "⛔ pytest 没跑出 passed 数字 ⇒ 棘轮无从判定（不许静默放行）" -ForegroundColor Red
    if ($tailLines.Count -gt 0) {
      Write-Host ("   该步输出尾部：" + ($tailLines -join ' / ')) -ForegroundColor DarkGray
    }
    $baselineDrop = $true
  }

  $failed = @($results | Where-Object { -not $_.ok })
  $ratchetBad = ($baselineDrop -or $null -ne $hardError)
  Write-Host ""
  Write-Host "==============================================================="
  # ⚠ 汇总行必须把**棘轮**也算进去（2026-09-19 复核抓到："6/6 步通过" 与 exit 1 同时出现，
  #   读起来是绿的）。棘轮与环境有关（`RUN_LIVE=1` 会多跑一条联网用例），所以它单独一行。
  Write-Host (" 门禁汇总（{0} 档）：{1}/{2} 步通过{3}" -f $(if ($Full) { '全量' } else { '快档' }),
    ($results.Count - $failed.Count), $results.Count,
    $(if ($ratchetBad) { ' · ⛔ 棘轮/执行未过 ⇒ **整体失败**' }
      elseif ($Full) { ' · ✅ 棘轮（只涨不跌）' }
      else { '（快档不含 pytest 棘轮，棘轮只在 -Full 判）' }))
  $results | ForEach-Object { Write-Host ("   {0} {1,-26} {2}" -f $(if ($_.ok) { '✅' } else { '⛔' }), $_.name, $_.note) }
  if ($Full) {
    Write-Host ("   {0} {1,-26} {2}" -f $(if ($ratchetBad) { '⛔' } else { '✅' }), '棘轮（pytest 只涨不跌）',
      $(if ($null -eq $pytestPassed) { "没跑出 passed 数字 ⇒ 判红：$($why -join '；')" }
        elseif ($baselineDrop) { "被破：$($why -join '；')" }
        else { "passed=$pytestPassed skipped=$pytestSkipped failed=$([int]$pytestFailed) errors=$([int]$pytestErrors) ≥ 基线" }))
    Write-Host ("      环境：RUN_LIVE=[{0}]（=1 时多跑 1 条联网用例 ⇒ 基线按**默认环境**记）" -f $env:RUN_LIVE)
    # 模型缓存也进记录：它是"同一份代码、不同结果"的一个真实来源（2026-09-21 那次假红就出在这里）。
    Write-Host ("      模型缓存：KS_MODELS_DIR=[{0}]（{1}）" -f $env:KS_MODELS_DIR, $modelsNote)
  }
  Write-Host "==============================================================="
  # ⚠ **绿灯也要留证据**（复核 2026-09-20 打回）：上面这些日志文件**只在失败时**才落
  #   （:186 起那段），于是"某次 -Quick 4/4 / 冒烟 26 套全过"这种**绿的宣称根本不可验**——
  #   既不能证实也不能证伪，只能信我复述。⇒ 现在无论红绿，都往一个**固定文件**写一份
  #   汇总（每次覆盖，不堆积）：`$TEMP\ks-gates-last.txt`。要查"上一跑到底什么结果"就读它。
  $lastPath = Join-Path ([System.IO.Path]::GetTempPath()) 'ks-gates-last.txt'
  $lastLines = @()
  $lastLines += ("{0} 门禁（{1} 档）· {2}/{3} 步通过 · exit={4}" -f (Get-Date).ToString('s'),
    $(if ($Full) { '全量' } else { '快档' }), ($results.Count - $failed.Count), $results.Count,
    $(if ($failed.Count -gt 0 -or $ratchetBad) { 1 } else { 0 }))
  $lastLines += ("  运行环境：RUN_LIVE=[{0}] · KS_DATA_DIR=[{1}] · KS_MODELS_DIR=[{2}]（{3}）· cwd={4}" -f `
    $env:RUN_LIVE, $env:KS_DATA_DIR, $env:KS_MODELS_DIR, $modelsNote, $repo)
  foreach ($r in $results) { $lastLines += ("  {0} {1,-26} {2}" -f $(if ($r.ok) { 'PASS' } else { 'FAIL' }), $r.name, $r.note) }
  if ($Full) {
    $lastLines += ("  {0} 棘轮：{1}" -f $(if ($ratchetBad) { 'FAIL' } else { 'PASS' }),
      $(if ($null -eq $pytestPassed) { "没跑出 passed 数字（$($why -join '；')）" }
        elseif ($baselineDrop) { "被破：$($why -join '；')" }
        else { "passed=$pytestPassed skipped=$pytestSkipped failed=$([int]$pytestFailed) errors=$([int]$pytestErrors)" }))
  }
  if ($null -ne $hardError) { $lastLines += ("  ⛔ 执行中断：" + $hardError.Exception.Message) }
  $lastLines | Set-Content -Path $lastPath -Encoding utf8
  Write-Host (" 本跑汇总已落：{0}" -f $lastPath) -ForegroundColor DarkGray
  if ($failed.Count -gt 0 -or $ratchetBad) {
    if ($failed.Count -gt 0) { Write-Host (" 失败步骤：" + (($failed | ForEach-Object { $_.name }) -join '、')) -ForegroundColor Red }
    if ($null -ne $hardError) { Write-Host " ⛔ 执行中断（见上方日志）" -ForegroundColor Red }
    exit 1
  }
  # ⚠ 只有**走到这里**（没失败、棘轮也没被破）才算"这一跑成功" ⇒ 才允许收数据目录。
  #   用显式标志而不是"看 $failed 是否为空"：中断/异常逃出去时那些变量可能是 $null，
  #   而 `-not $null` 为真 ⇒ 会把失败现场当成功删掉。显式标志不会被误判成真。
  $ownDataDirRemovable = $true
  exit 0
} finally {
  Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
  # ⚠ **恢复**而不是删除：删除会把调用方原本的值（若有）抹掉，
  #    而"再入开关"靠它 —— 见 gate-lock.mjs 里的祖先校验。
  if ($null -ne $prevLockHeld) { $env:KS_GATES_LOCK_HELD = $prevLockHeld }
  else { Remove-Item Env:\KS_GATES_LOCK_HELD -ErrorAction SilentlyContinue }
  if ($null -ne $prevLockToken) { $env:KS_GATES_LOCK_TOKEN = $prevLockToken }
  else { Remove-Item Env:\KS_GATES_LOCK_TOKEN -ErrorAction SilentlyContinue }
  if ($null -ne $prevDataDir) { $env:KS_DATA_DIR = $prevDataDir }
  else { Remove-Item Env:\KS_DATA_DIR -ErrorAction SilentlyContinue }
  # 自己布的数据目录自己收（见上面 `$ownDataDir` 那段的三条边界）。
  if (-not $ownDataDirExisted -and $ownDataDir) {
    if ($ownDataDirRemovable) {
      Remove-Item $ownDataDir -Recurse -Force -ErrorAction SilentlyContinue
    } elseif (Test-Path $ownDataDir) {
      Write-Host (" （这一跑没成功 ⇒ 本次的数据目录留着供排查：{0}）" -f $ownDataDir) -ForegroundColor DarkGray
    }
  }
  # 模型缓存目录同样**恢复**（它是我们为这一次跑布的，不该泄漏给调用方）。
  if ($null -ne $prevModelsDir) { $env:KS_MODELS_DIR = $prevModelsDir }
  else { Remove-Item Env:\KS_MODELS_DIR -ErrorAction SilentlyContinue }
  if ($null -ne $prevPyIo) { $env:PYTHONIOENCODING = $prevPyIo }
  else { Remove-Item Env:\PYTHONIOENCODING -ErrorAction SilentlyContinue }
  # `PYTEST_ADDOPTS` / `PYTEST_PLUGINS` 同样**恢复**（我们这一跑清掉了它们）。
  if ($null -ne $prevAddopts) { $env:PYTEST_ADDOPTS = $prevAddopts }
  else { Remove-Item Env:\PYTEST_ADDOPTS -ErrorAction SilentlyContinue }
  if ($null -ne $prevPyPlugins) { $env:PYTEST_PLUGINS = $prevPyPlugins }
  else { Remove-Item Env:\PYTEST_PLUGINS -ErrorAction SilentlyContinue }
  if ($null -ne $prevConsoleEnc) { try { [Console]::OutputEncoding = $prevConsoleEnc } catch { } }
}
