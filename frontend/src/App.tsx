import { useEffect, useMemo, useState } from 'react';
import { CommentDetailPanel } from './components/CommentDetailPanel';
import { QueueItemCard } from './components/QueueItemCard';
import { StatusMessage } from './components/StatusMessage';
import { mockComments } from './data/mockComments';
import type { CommentDetail, CommentStatus, ReviewDecision } from './types/moderation';
import './styles.css';

const decisionMessages: Record<ReviewDecision, string> = {
  NEEDS_REVIEW: 'Caso marcado para revisión continua.',
  CONFIRMED_TOXIC: 'Revisión registrada como confirmado tóxico.',
  NOT_TOXIC: 'Revisión registrada como no tóxico.',
};

function nextStatus(decision: ReviewDecision): CommentStatus {
  return decision === 'NEEDS_REVIEW' ? 'IN_REVIEW' : 'REVIEWED';
}

export default function App() {
  const [comments, setComments] = useState<CommentDetail[]>(mockComments);
  const [loadState, setLoadState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [selectedId, setSelectedId] = useState<string | undefined>(mockComments[0]?.comment_id);
  const [feedback, setFeedback] = useState<string>();
  const selectedComment = comments.find((comment) => comment.comment_id === selectedId);
  const pendingCount = useMemo(() => comments.filter((comment) => comment.status === 'PENDING').length, [comments]);
  const orderedComments = useMemo(() => [...comments].sort((a, b) => b.risk_score - a.risk_score), [comments]);

  useEffect(() => {
    const timer = window.setTimeout(() => setLoadState('ready'), 250);
    return () => window.clearTimeout(timer);
  }, []);

  function handleReview(decision: ReviewDecision) {
    if (!selectedId) return;
    setComments((current) => current.map((comment) => comment.comment_id === selectedId ? { ...comment, status: nextStatus(decision) } : comment));
    setFeedback(decisionMessages[decision]);
  }

  function retryLoading() {
    setLoadState('loading');
    window.setTimeout(() => setLoadState('ready'), 250);
  }

  return (
    <div className="app-shell">
      <header className="topbar"><a className="brand" href="/" aria-label="Review Desk, inicio"><span className="brand-mark">R</span><span>Review Desk</span></a><span className="environment-label">Herramienta interna · Demo local</span></header>
      <main className="workspace">
        <div className="page-heading"><div><span className="eyebrow">Moderación asistida</span><h1>Cola de revisión</h1><p className="intro">Trabaja primero los casos con mayor señal de riesgo. La puntuación orienta tu atención; tú tomas la decisión final.</p></div><div className="pending-count"><strong>{pendingCount}</strong><span>pendientes</span></div></div>
        <div className="notice"><span aria-hidden="true">i</span><p><strong>Control humano:</strong> el riesgo estimado no es una verdad ni una acción automática. La incertidumbre señala cuándo conviene mirar con más contexto.</p></div>
        {feedback && <div className="feedback" role="status" aria-live="polite"><span aria-hidden="true">✓</span>{feedback}</div>}
        <div className="workspace-grid">
          <section className="queue-panel" aria-labelledby="queue-title"><div className="section-heading"><div><h2 id="queue-title">Comentarios priorizados</h2><p>{orderedComments.length} casos · ordenados por riesgo estimado</p></div><span className="sort-label">Mayor riesgo primero</span></div><div className="queue-list">{loadState === 'loading' && <StatusMessage title="Cargando cola">Estamos preparando los casos para revisión.</StatusMessage>}{loadState === 'error' && <><StatusMessage title="No se pudo cargar la cola" tone="error">Comprueba la conexión y vuelve a intentarlo.</StatusMessage><button className="retry-button" type="button" onClick={retryLoading}>Reintentar</button></>}{loadState === 'ready' && (orderedComments.length ? orderedComments.map((comment) => <QueueItemCard key={comment.comment_id} item={comment} selected={comment.comment_id === selectedId} onSelect={() => { setSelectedId(comment.comment_id); setFeedback(undefined); }} />) : <StatusMessage title="No hay comentarios pendientes">La cola está vacía por ahora.</StatusMessage>)}</div></section>
          <section aria-label="Detalle del comentario"><CommentDetailPanel comment={selectedComment} onReview={handleReview} /></section>
        </div>
      </main>
      <footer className="footer">Risk score = señal de priorización · Sin decisiones automáticas contra comentarios</footer>
    </div>
  );
}
