/**
 * ValidityBadge —— 法规效力徽章（「点开即核验」任务 2，前端件）。
 *
 * 调用契约（后端端点 GET /api/v1/laws/verify?bbbs=<bbbs> 由集成者添加；
 * 本组件为纯展示件，不发请求——由调用方取数后传入）：
 *
 *   响应体（src/core/knowledge/law_source/verify.py 透传）：
 *   {
 *     "status":       "effective | superseded | withdrawn | upcoming |
 *                      unmarked | not_found | unverified",
 *     "status_text":  "现行有效 | 已修改 | 已废止 | 尚未生效 |
 *                      官方未标注效力状态 | 官方库未收录 | 未核验",
 *     "evidence_url": "https://flk.npc.gov.cn/detail?id=<bbbs>",
 *     "checked_at":   "2026-08-24T10:30:00+08:00",   // 缓存命中时为当初核验时间
 *     "cached":       false,
 *     "retryable":    true                           // 仅 unverified 为 true
 *   }
 *
 * 颜色语义（研究报告 §2 徽章表）：
 *   绿 = effective 现行有效 · 红 = withdrawn 已废止 · 黄 = superseded 已修改
 *   蓝 = upcoming 尚未生效 · 灰 = unmarked / not_found / unverified（未标注·查无·未核验）
 *
 * 行为：
 *   - 点击徽章本体 → 打开 evidenceUrl（无链接时渲染为不可点的标签）；
 *   - unverified / not_found 且传入 onRetry 时显示「↻ 重试」小按钮
 *     （retryable prop 可强制开/关）。
 */
export type ValidityStatus =
  | 'effective'
  | 'superseded'
  | 'withdrawn'
  | 'upcoming'
  | 'unmarked'
  | 'not_found'
  | 'unverified';

interface ValidityBadgeProps {
  /** 效力状态枚举（与后端 verify_law 返回一致；未知值按灰色兜底） */
  status: ValidityStatus;
  /** 中文文案（后端 status_text；缺省时用内置映射兜底） */
  statusText?: string;
  /** 官方证据页链接（flk detail 页）；有则点击徽章打开 */
  evidenceUrl?: string;
  /** 重试回调（unverified/not_found 时显示重试按钮） */
  onRetry?: () => void;
  /** 核验时间 ISO 串，有则进 tooltip（核验纪律：永远展示 retrieval date） */
  checkedAt?: string;
  /** 强制控制重试按钮显隐；缺省仅 unverified / not_found 显示 */
  retryable?: boolean;
}

/** 兜底文案（与 verify.py STATUS_TEXT 对齐；正常路径以后端下发为准） */
const FALLBACK_TEXT: Record<ValidityStatus, string> = {
  effective: '现行有效',
  superseded: '已修改',
  withdrawn: '已废止',
  upcoming: '尚未生效',
  unmarked: '官方未标注效力状态',
  not_found: '官方库未收录',
  unverified: '未核验',
};

const BADGE_CLASS: Record<ValidityStatus, string> = {
  effective: 'validity-badge-effective',
  superseded: 'validity-badge-superseded',
  withdrawn: 'validity-badge-withdrawn',
  upcoming: 'validity-badge-upcoming',
  unmarked: 'validity-badge-gray',
  not_found: 'validity-badge-gray',
  unverified: 'validity-badge-gray',
};

const BADGE_ICON: Record<ValidityStatus, string> = {
  effective: '✓',
  superseded: '⟳',
  withdrawn: '✕',
  upcoming: '◷',
  unmarked: '?',
  not_found: '∅',
  unverified: '…',
};

export default function ValidityBadge({
  status,
  statusText,
  evidenceUrl,
  onRetry,
  checkedAt,
  retryable,
}: ValidityBadgeProps) {
  const known = status in FALLBACK_TEXT ? status : 'unverified';
  const text = statusText?.trim() || FALLBACK_TEXT[known];
  const showRetry =
    !!onRetry && (retryable ?? (known === 'unverified' || known === 'not_found'));
  const tipParts = [text];
  if (checkedAt) tipParts.push(`核验于 ${checkedAt}`);
  if (evidenceUrl) tipParts.push('点击查看官方原文');
  const tip = tipParts.join(' · ');

  const openEvidence = () => {
    if (evidenceUrl) window.open(evidenceUrl, '_blank', 'noopener,noreferrer');
  };

  // 有证据链接 → 整个徽章是可点按钮；否则降级为纯标签（灰态可能无链接可给）
  const inner = (
    <>
      <span className="validity-badge-icon" aria-hidden>{BADGE_ICON[known]}</span>
      <span className="validity-badge-text">{text}</span>
      {showRetry && (
        <button
          type="button"
          className="validity-badge-retry"
          title="重新核验"
          aria-label="重新核验效力状态"
          onClick={(e) => { e.stopPropagation(); onRetry?.(); }}
        >↻</button>
      )}
    </>
  );

  if (evidenceUrl) {
    return (
      <button
        type="button"
        className={`validity-badge clickable ${BADGE_CLASS[known]}`}
        title={tip}
        aria-label={`法规效力：${text}`}
        onClick={openEvidence}
      >{inner}</button>
    );
  }
  return (
    <span className={`validity-badge ${BADGE_CLASS[known]}`} title={tip}
      aria-label={`法规效力：${text}`}>{inner}</span>
  );
}
