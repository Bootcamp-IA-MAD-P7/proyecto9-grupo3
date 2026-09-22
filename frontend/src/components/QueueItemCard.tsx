import type { QueueItem } from '../types/moderation';

interface QueueItemCardProps {
  item: QueueItem;
  selected: boolean;
  onSelect: () => void;
}

const statusLabels = { PENDING: 'Pendiente', IN_REVIEW: 'En revisión', REVIEWED: 'Revisado' };

function percentage(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function QueueItemCard({ item, selected, onSelect }: QueueItemCardProps) {
  return (
    <button className={`queue-item ${selected ? 'queue-item--selected' : ''}`} type="button" onClick={onSelect} aria-pressed={selected}>
      <span className="queue-item__topline">
        <span className="queue-item__id">{item.comment_id}</span>
        <span className={`status status--${item.status.toLowerCase()}`}>{statusLabels[item.status]}</span>
      </span>
      <span className="queue-item__meta">Vídeo {item.video_id} · Entrada {new Date(item.received_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}</span>
      <span className="metric-row">
        <span><small>Riesgo estimado</small><strong className="risk-value">{percentage(item.risk_score)}</strong></span>
        <span><small>Incertidumbre</small><strong>{percentage(item.uncertainty)}</strong></span>
      </span>
    </button>
  );
}
