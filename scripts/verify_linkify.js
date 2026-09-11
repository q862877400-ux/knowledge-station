// verify_linkify.js — 引用链接化(linkify)防回归校验
// 背景:旧正则条款号字符类 [0-9A-Za-z.]+ 贪婪,会把相邻引用的标准前缀吞进条款号,
//       如 [引用:GB 30871-2022-6.6][引用:GB 30871-2022-6.9] 剥括号后粘连成
//       "GB 30871-2022-6.6GB 30871-2022-6.9",整段 "6.6GB" 被当条款号 →
//       data-resolve 查无此条款 → 蓝色下划线但点击/悬停全部失效。
// 修复:条款号主分支收紧为纯数字点分 (?:[0-9]+(?:\.[0-9]+)*),前瞻 (?![0-9.])
//       使粘连处天然截断、显示文本零改动。
// 用法:node scripts/verify_linkify.js  (全部 PASS 即退出码 0)
const stdNos = ['GB 30871-2022', 'AQ 3028-2008', 'GB/T 3608-2008'];
const evidences = [
  { clause_revision_id: 'c1', standard_no: 'GB 30871-2022', clause_number: '6.6' },
  { clause_revision_id: 'c2', standard_no: 'GB 30871-2022', clause_number: '6.9' },
  { clause_revision_id: 'c3', standard_no: 'GB 30871-2022', clause_number: '10.1.10' },
  { clause_revision_id: 'c4', standard_no: 'GB/T 3608-2008', clause_number: '5.2.1' },
];

// 与 src/renderer/App.tsx linkify 保持同步(改动时两边一起改)
function linkify(text) {
  let out = text.replace(/🔗/g, '').replace(/\[引用:([^\]]+)\]/g, '$1');
  const esc = (s) => s.replace(/\./g, '\\.');
  for (const std of [...stdNos].sort((a, b) => b.length - a.length)) {
    const re = new RegExp(esc(std) + '[-–]\\s*((?:[0-9]+(?:\\.[0-9]+)*)|表[0-9]+|附录[0-9A-Za-z]*)(?![0-9.])', 'g');
    out = out.replace(re, (m, num) => {
      const key = std + '-' + num;
      const ev = evidences.find((e) => e.standard_no + '-' + e.clause_number === key);
      return ev
        ? '<span class="cite-link" data-cid="' + ev.clause_revision_id + '">' + m + '</span>'
        : '<span class="cite-link" data-resolve="' + std + '|' + num + '">' + m + '</span>';
    });
  }
  return out;
}

const cases = [
  // [粘连引用] 旧 bug 复现:两个 [引用:] 徽标连排剥括号后无分隔
  { in: '[引用:GB 30871-2022-6.6][引用:GB 30871-2022-6.9] 应设监护',
    expect: '<span class="cite-link" data-cid="c1">GB 30871-2022-6.6</span>'
          + '<span class="cite-link" data-cid="c2">GB 30871-2022-6.9</span> 应设监护' },
  // 无 [引用:] 包裹的连排(模型直接输出)
  { in: '依据 GB 30871-2022-6.6GB 30871-2022-6.9 规定',
    expect: '依据 <span class="cite-link" data-cid="c1">GB 30871-2022-6.6</span>'
          + '<span class="cite-link" data-cid="c2">GB 30871-2022-6.9</span> 规定' },
  // 跨标准连排
  { in: 'GB/T 3608-2008-5.2.1GB 30871-2022-6.6 跨标准连排',
    expect: '<span class="cite-link" data-cid="c4">GB/T 3608-2008-5.2.1</span>'
          + '<span class="cite-link" data-cid="c1">GB 30871-2022-6.6</span> 跨标准连排' },
  // 正常分隔不受影响
  { in: 'GB 30871-2022-6.6 与 GB 30871-2022-6.9 均适用',
    expect: '<span class="cite-link" data-cid="c1">GB 30871-2022-6.6</span> 与 '
          + '<span class="cite-link" data-cid="c2">GB 30871-2022-6.9</span> 均适用' },
  // 多标准混排 + 未命中证据走 resolve
  { in: '按 GB 30871-2022-6.6、AQ 3028-2008-5.1.2 执行',
    expect: '按 <span class="cite-link" data-cid="c1">GB 30871-2022-6.6</span>、'
          + '<span class="cite-link" data-resolve="AQ 3028-2008|5.1.2">AQ 3028-2008-5.1.2</span> 执行' },
  // 表/附录引用保留
  { in: 'GB 30871-2022-表1 规定', expect: '<span class="cite-link" data-resolve="GB 30871-2022|表1">GB 30871-2022-表1</span> 规定' },
  { in: '附录A 见 GB 30871-2022-附录A',
    expect: '附录A 见 <span class="cite-link" data-resolve="GB 30871-2022|附录A">GB 30871-2022-附录A</span>' },
  // 多级条款
  { in: 'GB 30871-2022-6.6 与 GB 30871-2022-10.1.10 多级条款',
    expect: '<span class="cite-link" data-cid="c1">GB 30871-2022-6.6</span> 与 '
          + '<span class="cite-link" data-cid="c3">GB 30871-2022-10.1.10</span> 多级条款' },
  // 段落尾引用
  { in: '正常段落 GB 30871-2022-6.6 结尾',
    expect: '正常段落 <span class="cite-link" data-cid="c1">GB 30871-2022-6.6</span> 结尾' },
];

let fail = 0;
for (const c of cases) {
  const got = linkify(c.in);
  if (got === c.expect) {
    console.log('PASS:', c.in);
  } else {
    fail++;
    console.log('FAIL:', c.in);
    console.log('  expect:', c.expect);
    console.log('  got   :', got);
  }
}
console.log(fail === 0 ? '\nALL PASS (' + cases.length + ')' : `\n${fail}/${cases.length} FAILED`);
process.exit(fail === 0 ? 0 : 1);
