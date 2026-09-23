import type { QueueItem } from '../types/moderation';

interface QueueItemCardProps { item: QueueItem; selected: boolean; onSelect: () => void; language: 'es' | 'en'; }
const copy = { es: { PENDING: 'Pendiente', IN_REVIEW: 'En revisión', REVIEWED: 'Revisado', video: 'Vídeo', source: 'Fuente', model: 'modelo', simulated: 'simulada', risk: 'Riesgo estimado', uncertainty: 'Incertidumbre' }, en: { PENDING: 'Pending', IN_REVIEW: 'In review', REVIEWED: 'Reviewed', video: 'Video', source: 'Source', model: 'model', simulated: 'synthetic', risk: 'Estimated risk', uncertainty: 'Uncertainty' } } as const;
const percentage = (value: number) => `${Math.round(value * 100)}%`;

export function QueueItemCard({ item, selected, onSelect, language }: QueueItemCardProps) {
  const t = copy[language];
  return <button className={`queue-item ${selected ? 'queue-item--selected' : ''}`} type="button" onClick={onSelect} aria-pressed={selected}><span className="queue-item__topline"><span className="queue-item__id">{item.comment_id}</span><span className={`status status--${item.status.toLowerCase()}`}>{t[item.status]}</span></span><span className="queue-item__meta">{t.video} {item.video_id} · {t.source} {item.score_source === 'MODEL' ? t.model : t.simulated}</span><span className="metric-row"><span><small>{t.risk}</small><strong className="risk-value">{percentage(item.risk_score)}</strong></span><span><small>{t.uncertainty}</small><strong>{percentage(item.uncertainty)}</strong></span></span></button>;
}
