export type DemoCommentStatus = 'PENDING' | 'IN_REVIEW' | 'REVIEWED';
export type DemoFilter = 'PENDING' | 'REVIEWED';
export type DemoSort = 'RISK_DESC' | 'RISK_ASC';

export interface DemoComment {
  comment_id: string;
  text: string;
  author: string;
  published_at: string;
  likes: number;
  status: DemoCommentStatus;
  risk_score: number;
  uncertainty: number;
  model_version: string;
  score_source: 'SIMULATED';
}

export const DEMO_COMMENTS: readonly DemoComment[] = [
  { comment_id: 'demo-101', text: 'La explicación del minuto 4 me ayudó a entender el problema. Gracias por incluir el ejemplo.', author: 'Cuenta_demo_01', published_at: 'Hace 2 horas', likes: 42, status: 'PENDING', risk_score: 0.91, uncertainty: 0.16, model_version: 'demo-scorer-v2', score_source: 'SIMULATED' },
  { comment_id: 'demo-102', text: 'No estoy de acuerdo con la conclusión, pero la comparación de las dos ideas es interesante.', author: 'Cuenta_demo_02', published_at: 'Hace 5 horas', likes: 18, status: 'PENDING', risk_score: 0.68, uncertainty: 0.41, model_version: 'demo-scorer-v2', score_source: 'SIMULATED' },
  { comment_id: 'demo-103', text: 'Este dato parece necesitar una fuente. ¿Podrías dejar la referencia en la descripción?', author: 'Cuenta_demo_03', published_at: 'Ayer', likes: 7, status: 'PENDING', risk_score: 0.54, uncertainty: 0.28, model_version: 'demo-scorer-v2', score_source: 'SIMULATED' },
  { comment_id: 'demo-104', text: 'El ritmo de esta parte es rápido, aunque el resumen final lo deja bastante claro.', author: 'Cuenta_demo_04', published_at: 'Ayer', likes: 31, status: 'IN_REVIEW', risk_score: 0.47, uncertainty: 0.52, model_version: 'demo-scorer-v2', score_source: 'SIMULATED' },
  { comment_id: 'demo-105', text: 'Comentario ficticio con una frase ambigua que conviene revisar con el contexto completo.', author: 'Cuenta_demo_05', published_at: 'Hace 2 días', likes: 3, status: 'PENDING', risk_score: 0.39, uncertainty: 0.77, model_version: 'demo-scorer-v2', score_source: 'SIMULATED' },
  { comment_id: 'demo-106', text: 'Me quedo con la parte práctica. Sería útil ver otro caso parecido en un vídeo futuro.', author: 'Cuenta_demo_06', published_at: 'Hace 3 días', likes: 12, status: 'REVIEWED', risk_score: 0.29, uncertainty: 0.22, model_version: 'demo-scorer-v2', score_source: 'SIMULATED' },
  { comment_id: 'demo-107', text: 'La transcripción automática tiene un error en este punto; el audio original dice otra cosa.', author: 'Cuenta_demo_07', published_at: 'Hace 4 días', likes: 24, status: 'PENDING', risk_score: 0.22, uncertainty: 0.33, model_version: 'demo-scorer-v2', score_source: 'SIMULATED' },
  { comment_id: 'demo-108', text: 'Buen resumen, aunque faltó explicar por qué elegiste ese criterio.', author: 'Cuenta_demo_08', published_at: 'Hace 5 días', likes: 9, status: 'REVIEWED', risk_score: 0.14, uncertainty: 0.18, model_version: 'demo-scorer-v2', score_source: 'SIMULATED' },
  { comment_id: 'demo-109', text: 'Ejemplo sintético de comentario neutral para comprobar el orden de la cola.', author: 'Cuenta_demo_09', published_at: 'Hace 6 días', likes: 5, status: 'PENDING', risk_score: 0.08, uncertainty: 0.11, model_version: 'demo-scorer-v2', score_source: 'SIMULATED' },
  { comment_id: 'demo-110', text: 'La comparación final responde a la pregunta inicial de forma directa.', author: 'Cuenta_demo_10', published_at: 'Hace 1 semana', likes: 16, status: 'REVIEWED', risk_score: 0.04, uncertainty: 0.09, model_version: 'demo-scorer-v2', score_source: 'SIMULATED' },
];

export function filterAndSortComments(comments: readonly DemoComment[], filter: DemoFilter, sort: DemoSort): DemoComment[] {
  const visible = comments.filter((comment) => filter === 'REVIEWED' ? comment.status === 'REVIEWED' : comment.status !== 'REVIEWED');
  return [...visible].sort((a, b) => sort === 'RISK_DESC' ? b.risk_score - a.risk_score : a.risk_score - b.risk_score);
}

export function resetDemoComments(): DemoComment[] {
  return DEMO_COMMENTS.map((comment) => ({ ...comment }));
}
