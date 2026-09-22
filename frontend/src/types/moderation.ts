export type CommentStatus = 'PENDING' | 'IN_REVIEW' | 'REVIEWED';
export type ScoreSource = 'SIMULATED' | 'MODEL';
export type UserRole = 'MODERATOR' | 'SUPERVISOR';

export interface PublicUser { id: string; username: string; display_name: string; role: UserRole; }
export interface LoginResponse { access_token: string; token_type: 'bearer'; expires_in: number; user: PublicUser; }

export interface QueueItem {
  comment_id: string;
  video_id: string;
  risk_score: number;
  uncertainty: number;
  model_version: string;
  score_source: ScoreSource;
  status: CommentStatus;
}

export interface QueuePage { items: QueueItem[]; page: number; page_size: number; total: number; has_next: boolean; }
