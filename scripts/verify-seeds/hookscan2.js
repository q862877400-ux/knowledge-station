/* B6 verify — STRENGTHENED hooks-after-return scanner (replaces the unsound one for judging).
   Differences vs %TEMP%\ks-hookscan.js:
     1) resolves `import { useMemo as um } from 'react'` aliases
     2) treats a call to a LOCAL function whose body (any depth) contains a hook as a hook site
        (transitively, 3 passes) -> catches `helperThatHidesAHook()`
     3) walks the tree RECURSIVELY over every .tsx (the old one read exactly one directory)
   Over-approximates on purpose (more teeth); a hit is a candidate, the runtime switch test decides. */
const fs = require('fs');
const path = require('path');
const ts = require('D:/AI/work space/zcode/node_modules/typescript');

const ROOT = process.argv[2];
const HOOK_NAMES = new Set(['useState', 'useMemo', 'useEffect', 'useCallback', 'useRef', 'useReducer',
  'useContext', 'useLayoutEffect', 'useImperativeHandle', 'useDebugValue', 'useTransition',
  'useDeferredValue', 'useId', 'useSyncExternalStore', 'useInsertionEffect', 'useOptimistic',
  'useActionState', 'useFormStatus', 'use']);

const files = [];
(function walkDir(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    if (e.name === 'node_modules' || e.name === '.git' || e.name === 'dist') continue;
    const p = path.join(d, e.name);
    if (e.isDirectory()) walkDir(p);
    else if (e.name.endsWith('.tsx')) files.push(p);
  }
})(ROOT);
files.sort();

const isFnLike = (n) => ts.isFunctionDeclaration(n) || ts.isFunctionExpression(n) || ts.isArrowFunction(n)
  || ts.isMethodDeclaration(n) || ts.isGetAccessor(n) || ts.isSetAccessor(n);

const calleeName = (n) => {
  if (!ts.isCallExpression(n)) return '';
  const c = n.expression;
  if (ts.isIdentifier(c)) return c.text;
  if (ts.isPropertyAccessExpression(c) && ts.isIdentifier(c.name)) return c.name.text;
  return '';
};

let findings = 0;
for (const full of files) {
  const rel = path.relative(ROOT, full);
  const sf = ts.createSourceFile(full, fs.readFileSync(full, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

  // (1) react hook aliases
  const aliases = new Set();
  ts.forEachChild(sf, (n) => {
    if (ts.isImportDeclaration(n) && ts.isStringLiteral(n.moduleSpecifier) && n.moduleSpecifier.text === 'react') {
      const b = n.importClause && n.importClause.namedBindings;
      if (b && ts.isNamedImports(b)) {
        for (const el of b.elements) {
          const orig = el.propertyName ? el.propertyName.text : el.name.text;
          if (HOOK_NAMES.has(orig)) aliases.add(el.name.text);
        }
      }
    }
  });
  const isHookName = (nm) => HOOK_NAMES.has(nm) || aliases.has(nm);

  // (1b) file-level IDENTIFIER aliases: `const um = useMemo`, `const { useMemo: um } = React`
  //      (fixpoint, so `const a = useMemo; const b = a` also resolves) — the old scanner's blind spot.
  for (let pass = 0; pass < 4; pass += 1) {
    let added = false;
    const v = (n) => {
      if (ts.isVariableDeclaration(n)) {
        if (ts.isIdentifier(n.name) && n.initializer && ts.isIdentifier(n.initializer) && isHookName(n.initializer.text)) {
          if (!aliases.has(n.name.text)) { aliases.add(n.name.text); added = true; }
        }
        if (ts.isObjectBindingPattern(n.name)) {
          for (const el of n.name.elements) {
            if (el.propertyName && ts.isIdentifier(el.propertyName) && el.name && ts.isIdentifier(el.name) && isHookName(el.propertyName.text)) {
              if (!aliases.has(el.name.text)) { aliases.add(el.name.text); added = true; }
            }
          }
        }
      }
      ts.forEachChild(n, v);
    };
    ts.forEachChild(sf, v);
    if (!added) break;
  }

  // (2) local functions that contain a hook anywhere in their body
  const localFns = [];
  const collect = (n) => {
    if (isFnLike(n) && n.body) {
      const name = (n.name && ts.isIdentifier(n.name)) ? n.name.text
        : (n.parent && ts.isVariableDeclaration(n.parent) && ts.isIdentifier(n.parent.name)) ? n.parent.name.text : '';
      if (name) localFns.push({ name, body: n.body });
    }
    ts.forEachChild(n, collect);
  };
  ts.forEachChild(sf, collect);
  const hooky = new Set();
  for (let pass = 0; pass < 3; pass += 1) {
    for (const f of localFns) {
      if (hooky.has(f.name)) continue;
      let found = false;
      const v = (n) => {
        if (found) return;
        const nm = calleeName(n);
        if (nm && (isHookName(nm) || hooky.has(nm))) found = true;
        ts.forEachChild(n, v);
      };
      ts.forEachChild(f.body, v);
      if (found) hooky.add(f.name);
    }
  }

  // (3) hooks-after-first-top-level-return, per fn-like
  const analyze = (fn) => {
    if (!fn.body || !ts.isBlock(fn.body)) return;
    const returns = [], hooks = [];
    const visit = (n) => {
      if (n !== fn && isFnLike(n)) return;          // do not descend into nested functions
      if (ts.isReturnStatement(n)) returns.push(n);
      const nm = calleeName(n);
      if (nm && (isHookName(nm) || hooky.has(nm))) hooks.push({ n, nm });
      ts.forEachChild(n, visit);
    };
    ts.forEachChild(fn.body, visit);
    if (returns.length === 0 || hooks.length === 0) return;
    const firstRet = Math.min(...returns.map((r) => r.getStart(sf)));
    const late = hooks.filter((h) => h.n.getStart(sf) > firstRet).map((h) => h.nm);
    if (late.length === 0) return;
    const fnName = (fn.name && ts.isIdentifier(fn.name)) ? fn.name.text
      : (fn.parent && ts.isVariableDeclaration(fn.parent) && ts.isIdentifier(fn.parent.name)) ? fn.parent.name.text : '<anon>';
    const l = (p) => sf.getLineAndCharacterOfPosition(p).line + 1;
    console.log(`SUSPECT ${rel}  fn=${fnName}  firstReturn=L${l(firstRet)}  hooksAfter=${late.map((x, i) => x + '@' + l(hooks.filter((h) => h.n.getStart(sf) > firstRet)[i].n.getStart(sf))).join(',')}`);
    findings += 1;
  };
  const top = (n) => { if (isFnLike(n)) analyze(n); ts.forEachChild(n, top); };
  ts.forEachChild(sf, top);
}
console.log(findings === 0 ? 'NO-SUSPECT' : `TOTAL-SUSPECTS ${findings}`);
