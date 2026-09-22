import type { CommentDetail, ReviewDecision } from '../types/moderation';

interface CommentDetailPanelProps {
  comment: CommentDetail | undefined;
  onReview: (decision: ReviewDecision) => void;
}

const decisionLabels: Record<ReviewDecision, string> = {
  NEEDS_REVIEW: 'Marcar en revisión',
  CONFIRMED_TOXIC: 'Confirmar como tóxico',
  NOT_TOXIC: 'Marcar como no tóxico',
};

export function CommentDetailPanel({ comment, onReview }: CommentDetailPanelProps) {
  if (!comment) {
    return <div className="detail-panel detail-panel--empty"><span className="detail-panel__icon">→</span><h2>Selecciona un comentario</h2><p>El detalle autorizado aparecerá aquí para que puedas tomar una decisión informada.</p></div>;
  }

  return (
    <article className="detail-panel" aria-labelledby="detail-title">
      <div className="detail-panel__header"><div><span className="eyebrow">Detalle autorizado</span><h2 id="detail-title">{comment.comment_id}</h2></div><span className={`status status--${comment.status.toLowerCase()}`}>{comment.status.replace('_', ' ')}</span></div>
      <div className="comment-text"><span className="eyebrow">Texto del comentario</span><p>{comment.text}</p></div>
      <dl className="detail-metrics"><div><dt>Riesgo estimado</dt><dd>{Math.round(comment.risk_score * 100)}%</dd></div><div><dt>Incertidumbre</dt><dd>{Math.round(comment.uncertainty * 100)}%</dd></div><div><dt>Modelo</dt><dd>{comment.model_version}</dd></div></dl>
      <div className="human-note"><strong>Tu decisión importa</strong><p>Estas señales ayudan a priorizar. No determinan si un comentario es tóxico.</p></div>
      <div className="review-actions"><span className="eyebrow">Registrar revisión humana</span><div className="action-grid">{(Object.keys(decisionLabels) as ReviewDecision[]).map((decision) => <button key={decision} className={`action-button action-button--${decision.toLowerCase()}`} type="button" onClick={() => onReview(decision)} disabled={comment.status === 'REVIEWED'}>{decisionLabels[decision]}</button>)}</div></div>
    </article>
  );
}
