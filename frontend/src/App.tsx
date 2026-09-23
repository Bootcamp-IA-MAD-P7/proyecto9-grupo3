import { useCallback, useEffect, useMemo, useState } from 'react';
import { ApiError, currentUser, loadCommentDetail, loadQueue, login, logout, submitReview } from './api/client';
import { CommentDetailPanel } from './components/CommentDetailPanel';
import { DemoPage } from './components/DemoPage';
import { LandingPage } from './components/LandingPage';
import { LegalPage } from './components/LegalPage';
import { LoginForm } from './components/LoginForm';
import { QueueItemCard } from './components/QueueItemCard';
import { StatusMessage } from './components/StatusMessage';
import { LanguageToggle, useLanguage } from './i18n';
import { ThemeToggle } from './theme';
import { SiteFooter } from './components/SiteFooter';
import type { CommentDetail, PublicUser, QueueItem, ReviewDecision, ReviewResponse } from './types/moderation';
import './styles.css';

interface Session { token: string; user: PublicUser; }
interface DetailError { status: number; message: string; }

export default function App() {
  if (window.location.pathname === '/demo') return <DemoPage />;
  if (window.location.pathname === '/legal') return <LegalPage />;
  if (window.location.pathname !== '/moderator' && window.location.pathname !== '/login') return <LandingPage />;
  return <PrivateApp />;
}

function PrivateApp() {
  const { language } = useLanguage();
  const english = language === 'en';
  const t = english ? { logout: 'Sign out', eyebrow: 'Human-assisted moderation', title: 'Review queue', intro: 'Work through the cases with the strongest risk signal first. The score guides attention; you make the final decision.', pending: 'pending', human: 'Human control:', humanText: 'Estimated risk is not truth or an automatic action. Uncertainty shows when more context may be useful.', queue: 'Prioritized comments', ordered: 'cases · ordered by estimated risk', sort: 'Highest risk first', loading: 'Loading queue', loadingText: 'We are checking the pending cases.', loadError: 'The queue could not be loaded', retry: 'Try again', unauthorized: 'Session not authorized', unauthorizedText: 'Your session is no longer valid. Sign in again.', empty: 'No pending comments', emptyText: 'The queue is empty for now.', detail: 'Details and review', footer: 'Risk = prioritization signal · No automatic actions against comments', back: 'Home', demo: 'Public demo', welcome: 'Welcome back' } : { logout: 'Cerrar sesión', eyebrow: 'Moderación asistida', title: 'Cola de revisión', intro: 'Trabaja primero los casos con mayor señal de riesgo. La puntuación orienta tu atención; tú tomas la decisión final.', pending: 'pendientes', human: 'Control humano:', humanText: 'El riesgo estimado no es una verdad ni una acción automática. La incertidumbre señala cuándo conviene mirar con más contexto.', queue: 'Comentarios priorizados', ordered: 'casos · ordenados por riesgo estimado', sort: 'Mayor riesgo primero', loading: 'Cargando cola', loadingText: 'Estamos consultando los casos pendientes.', loadError: 'No se pudo cargar la cola', retry: 'Reintentar', unauthorized: 'Sesión no autorizada', unauthorizedText: 'Tu sesión ya no es válida. Inicia sesión de nuevo.', empty: 'No hay comentarios pendientes', emptyText: 'La cola está vacía por ahora.', detail: 'Detalle y revisión del caso', footer: 'Riesgo = señal de priorización · Sin decisiones automáticas contra comentarios', back: 'Inicio', demo: 'Demo pública', welcome: 'Bienvenida de nuevo' };
  const [session, setSession] = useState<Session>();
  const [loginState, setLoginState] = useState<'idle' | 'loading'>('idle');
  const [loginError, setLoginError] = useState<string>();
  const [comments, setComments] = useState<QueueItem[]>([]);
  const [loadState, setLoadState] = useState<'idle' | 'loading' | 'ready' | 'error' | 'unauthorized'>('idle');
  const [queueError, setQueueError] = useState<string>();
  const [selectedId, setSelectedId] = useState<string>();
  const [detail, setDetail] = useState<CommentDetail>();
  const [detailState, setDetailState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [detailError, setDetailError] = useState<DetailError>();
  const [feedback, setFeedback] = useState<string>();
  const pendingCount = useMemo(() => comments.filter((comment) => comment.status === 'PENDING').length, [comments]);
  const orderedComments = useMemo(() => [...comments].sort((a, b) => b.risk_score - a.risk_score), [comments]);
  const fetchDetail = useCallback(async (token: string, commentId: string) => { setDetailState('loading'); setDetailError(undefined); setDetail(undefined); setFeedback(undefined); try { setDetail(await loadCommentDetail(token, commentId)); setDetailState('ready'); } catch (error) { if (error instanceof ApiError && error.status === 401) { setSession(undefined); setLoadState('unauthorized'); } setDetailError({ status: error instanceof ApiError ? error.status : 0, message: error instanceof Error ? error.message : 'No se pudo cargar el detalle.' }); setDetailState('error'); } }, []);
  const fetchQueue = useCallback(async (token: string) => { setLoadState('loading'); setQueueError(undefined); try { const page = await loadQueue(token); setComments(page.items); setSelectedId(page.items[0]?.comment_id); setLoadState('ready'); if (page.items[0]) void fetchDetail(token, page.items[0].comment_id); } catch (error) { if (error instanceof ApiError && error.status === 401) { setSession(undefined); setComments([]); setLoadState('unauthorized'); return; } setQueueError(error instanceof Error ? error.message : 'No se pudo cargar la cola.'); setLoadState('error'); } }, [fetchDetail]);
  async function handleLogin(username: string, password: string) { setLoginState('loading'); setLoginError(undefined); try { const response = await login(username, password); setSession({ token: response.access_token, user: response.user }); setLoginState('idle'); await fetchQueue(response.access_token); } catch (error) { setLoginState('idle'); setLoginError(error instanceof Error ? error.message : 'No se pudo iniciar sesión.'); } }
  const handleLogout = useCallback(async () => { const token = session?.token; setSession(undefined); setComments([]); setSelectedId(undefined); setDetail(undefined); setLoadState('idle'); if (token) { try { await logout(token); } catch { /* Always clear the local session. */ } } }, [session?.token]);
  useEffect(() => { if (session) void currentUser(session.token).catch((error: unknown) => { if (error instanceof ApiError && error.status === 401) void handleLogout(); }); }, [session, handleLogout]);
  function selectComment(commentId: string) { setSelectedId(commentId); if (session) void fetchDetail(session.token, commentId); }
  async function handleReview(decision: ReviewDecision, notes?: string): Promise<ReviewResponse> { if (!session || !selectedId) throw new Error('No hay un comentario seleccionado.'); try { const result = await submitReview(session.token, selectedId, { decision, notes }); setDetail((current) => current ? { ...current, status: result.status } : current); setComments((current) => current.map((comment) => comment.comment_id === result.comment_id ? { ...comment, status: result.status } : comment)); setFeedback(`Revisión registrada para ${result.comment_id}.`); return result; } catch (error) { if (error instanceof ApiError && error.status === 401) await handleLogout(); throw error; } }
  if (!session) return <LoginForm loading={loginState === 'loading'} error={loginError} onSubmit={handleLogin} />;
  return <div className="app-shell demo-shell private-shell"><header className="topbar"><a className="brand" href="/" aria-label={t.back}><span className="brand-mark">R</span><span>Review Desk</span></a><div className="topbar-actions"><a className="logout-button" href="/">{t.back}</a><a className="logout-button" href="/demo">{t.demo}</a><span className="environment-label">{session.user.display_name}</span><ThemeToggle /><LanguageToggle /><button className="logout-button" type="button" onClick={() => void handleLogout()}>{t.logout}</button></div></header><main className="workspace"><div className="page-heading"><div><span className="eyebrow">{t.eyebrow}</span><h1>{t.title}</h1><p className="intro">{t.intro}</p></div><div className="pending-count"><strong>{pendingCount}</strong><span>{t.pending}</span></div></div><div className="notice"><span aria-hidden="true">i</span><p><strong>{t.human}</strong> {t.humanText}</p></div><p className="review-feedback" aria-live="polite">{feedback}</p><div className="workspace-grid"><section className="queue-panel" aria-labelledby="queue-title"><div className="section-heading"><div><h2 id="queue-title">{t.queue}</h2><p>{orderedComments.length} {t.ordered}</p></div><span className="sort-label">{t.sort}</span></div><div className="queue-list">{loadState === 'loading' && <StatusMessage title={t.loading}>{t.loadingText}</StatusMessage>}{loadState === 'error' && <><StatusMessage title={t.loadError} tone="error">{queueError}</StatusMessage><button className="retry-button" type="button" onClick={() => void fetchQueue(session.token)}>{t.retry}</button></>}{loadState === 'unauthorized' && <StatusMessage title={t.unauthorized}>{t.unauthorizedText}</StatusMessage>}{loadState === 'ready' && (orderedComments.length ? orderedComments.map((comment) => <QueueItemCard language={language} key={comment.comment_id} item={comment} selected={comment.comment_id === selectedId} onSelect={() => selectComment(comment.comment_id)} />) : <StatusMessage title={t.empty}>{t.emptyText}</StatusMessage>)}</div></section><section aria-label={t.detail}><CommentDetailPanel language={language} key={selectedId ?? 'empty'} detail={detail} loading={detailState === 'loading'} error={detailState === 'error' ? detailError : undefined} onRetry={() => selectedId && void fetchDetail(session.token, selectedId)} onReview={handleReview} /></section></div></main><SiteFooter /></div>;
}
