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

export interface CommentDetail extends QueueItem { text: string; }
export interface PublicComment extends CommentDetail { author: string; published_at: string | null; likes: number; }
export interface PublicYouTubeQueue { video_id: string; fetched_at: string; items: PublicComment[]; }
export type ReviewDecision = 'NEEDS_REVIEW' | 'CONFIRMED_TOXIC' | 'NOT_TOXIC';
export interface ReviewRequest { decision: ReviewDecision; notes?: string; }
export interface ReviewResponse { comment_id: string; status: 'REVIEWED' | 'IN_REVIEW'; decision: ReviewDecision; reviewed_by: string; reviewed_at: string; }
