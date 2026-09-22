import type { LoginResponse, PublicUser, QueuePage } from '../types/moderation';

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) { super(message); this.name = 'ApiError'; }
}
function apiUrl(): string {
  const value = import.meta.env.VITE_API_URL?.trim();
  if (!value) throw new ApiError(0, 'Falta configurar VITE_API_URL. Define la URL de la API y vuelve a cargar la aplicación.');
  return value.replace(/\/$/, '');
}
async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers); headers.set('Accept', 'application/json');
  if (options.body) headers.set('Content-Type', 'application/json'); if (token) headers.set('Authorization', `Bearer ${token}`);
  let response: Response;
  try { response = await fetch(`${apiUrl()}${path}`, { ...options, headers }); } catch { throw new ApiError(0, 'No se pudo conectar con la API. Comprueba la conexión e inténtalo de nuevo.'); }
  if (!response.ok) { let message = `La API respondió con un error (${response.status}).`; try { const body = await response.json() as { detail?: string }; if (body.detail) message = body.detail; } catch { /* HTTP error without JSON body. */ } throw new ApiError(response.status, message); }
  if (response.status === 204) return undefined as T; return response.json() as Promise<T>;
}
export const login = (username: string, password: string) => request<LoginResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
export const currentUser = (token: string) => request<PublicUser>('/auth/me', {}, token);
export const logout = (token: string) => request<void>('/auth/logout', { method: 'POST' }, token);
export const loadQueue = (token: string) => request<QueuePage>('/comments?status=PENDING&page=1&page_size=20', {}, token);
