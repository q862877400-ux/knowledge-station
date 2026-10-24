/* 用仓库根部已有的 `typescript` 做**真 AST** 抽前端符号（替掉正则近似）。
 *
 * 为什么要替换：`06-content.py` 的 `web_content` 用正则抽 `export function/const/class`
 * —— 那只是**近似**：多行声明、`export { a, b }`、`export default`、类型别名都会漏。
 * 仓库根已有 `typescript@5.9.3`，用它建 AST 就精确了，且**不新增任何依赖**。
 *
 * 输出：docs/survey/data/web_ast.json
 *   { generated_by, typescript_version, counts, files: [{file, lines, exports:[{name,kind,line,exported}], ...}] }
 *
 * 只记录，不判断。
 */
const fs = require('node:fs')
const path = require('node:path')
const ts = require('typescript')

const ROOT = path.resolve(__dirname, '..', '..')
const DATA = path.join(ROOT, 'docs', 'survey', 'data')

function collectFiles(dir) {
  const out = []
  if (!fs.existsSync(dir)) return out
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) {
      if (e.name === 'node_modules' || e.name === '.git') continue
      out.push(...collectFiles(p))
    } else if (/\.(ts|tsx|js|jsx|mjs|cjs)$/.test(e.name)) {
      out.push(p)
    }
  }
  return out
}

function hasModifier(node, kind) {
  const mods = ts.canHaveModifiers(node) ? ts.getModifiers(node) : undefined
  return Boolean(mods && mods.some((m) => m.kind === kind))
}

function scanFile(abs) {
  const rel = path.relative(ROOT, abs).replace(/\\/g, '/')
  const text = fs.readFileSync(abs, 'utf8')
  const isTs = /\.tsx?$/.test(abs)
  const sf = ts.createSourceFile(
    abs,
    text,
    ts.ScriptTarget.Latest,
    /* setParentNodes */ false,
    isTs ? (abs.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS)
      : ts.ScriptKind.JS,
  )
  const exports = []
  const imports = []

  function lineOf(node) {
    return sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1
  }

  function addExport(node, name, kind, exported, viaDefault) {
    exports.push({
      name,
      kind,
      line: lineOf(node),
      exported,
      default: Boolean(viaDefault),
    })
  }

  for (const stmt of sf.statements) {
    // import ...
    if (ts.isImportDeclaration(stmt)) {
      const m = stmt.moduleSpecifier
      imports.push({
        from: ts.isStringLiteral(m) ? m.text : '?',
        line: lineOf(stmt),
      })
      continue
    }

    const exp = hasModifier(stmt, ts.SyntaxKind.ExportKeyword)
    const dflt = hasModifier(stmt, ts.SyntaxKind.DefaultKeyword)

    if (ts.isFunctionDeclaration(stmt)) {
      addExport(stmt, stmt.name ? stmt.name.text : '(anonymous)', 'function', exp, dflt)
    } else if (ts.isClassDeclaration(stmt)) {
      addExport(stmt, stmt.name ? stmt.name.text : '(anonymous)', 'class', exp, dflt)
    } else if (ts.isInterfaceDeclaration(stmt)) {
      addExport(stmt, stmt.name.text, 'interface', exp, false)
    } else if (ts.isTypeAliasDeclaration(stmt)) {
      addExport(stmt, stmt.name.text, 'type', exp, false)
    } else if (ts.isEnumDeclaration(stmt)) {
      addExport(stmt, stmt.name.text, 'enum', exp, false)
    } else if (ts.isVariableStatement(stmt)) {
      const isExp = hasModifier(stmt, ts.SyntaxKind.ExportKeyword)
      for (const d of stmt.declarationList.declarations) {
        if (ts.isIdentifier(d.name)) {
          addExport(d, d.name.text, 'const', isExp, false)
        }
      }
    } else if (ts.isExportDeclaration(stmt)) {
      // `export { a, b }` / `export * from '...'`
      if (stmt.exportClause && ts.isNamedExports(stmt.exportClause)) {
        for (const el of stmt.exportClause.elements) {
          addExport(el, el.name.text, 're-export', true, false)
        }
      } else if (stmt.moduleSpecifier) {
        addExport(stmt, '*', 're-export-all', true, false)
      }
    }
  }

  const lines = text.split('\n').length
  return {
    file: rel,
    lines,
    kind: isTs ? (abs.endsWith('.tsx') ? 'tsx' : 'ts') : 'js',
    exports,
    n_exports: exports.filter((e) => e.exported).length,
    n_declarations: exports.length,
    imports: imports.length,
  }
}

function main() {
  const roots = [
    path.join(ROOT, 'plugin', 'client'),
    path.join(ROOT, 'plugin', 'src'),
  ]
  const files = roots.flatMap(collectFiles).sort()
  const results = files.map(scanFile)

  // 一致性自查：TS 建 AST 失败会抛异常 ⇒ 能跑到这里说明全部解析成功
  const totalExports = results.reduce((a, r) => a + r.exports.filter((e) => e.exported).length, 0)
  const totalDecls = results.reduce((a, r) => a + r.n_declarations, 0)

  const payload = {
    generated_by: 'scripts/survey/09-web-ast.cjs（用仓库根部已有的 typescript）',
    typescript_version: ts.version,
    caliber:
      '用 **TypeScript 编译器 API**（`ts.createSourceFile`）建真 AST，' +
      '抽 `import` / `function` / `class` / `interface` / `type` / `enum` / ' +
      '`const` / `export {}` / `export *`。' +
      '**这是 AST 级，不是正则近似**；与 `data/web_content.json`（正则版）并存，' +
      '两份差异本身就是「正则漏了什么」的读数。',
    roots: ['plugin/client', 'plugin/src'],
    counts: {
      files: results.length,
      total_exports: totalExports,
      total_declarations: totalDecls,
      tsx_files: results.filter((r) => r.kind === 'tsx').length,
      ts_files: results.filter((r) => r.kind === 'ts').length,
      js_files: results.filter((r) => r.kind === 'js').length,
    },
    files: results,
  }
  fs.mkdirSync(DATA, { recursive: true })
  const out = path.join(DATA, 'web_ast.json')
  fs.writeFileSync(out, JSON.stringify(payload, null, 1), 'utf8')
  console.log(`  → ${path.relative(ROOT, out)}  (${Math.round(JSON.stringify(payload).length / 1024)} KB)`)
  console.log(
    `     ${results.length} 个文件 / 导出 ${totalExports} / 声明 ${totalDecls}` +
      `  (tsx ${payload.counts.tsx_files} / ts ${payload.counts.ts_files} / js ${payload.counts.js_files})`,
  )
}

main()
