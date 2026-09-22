export type CommentStatus = 'PENDING' | 'IN_REVIEW' | 'REVIEWED';
export type ReviewDecision = 'NEEDS_REVIEW' | 'CONFIRMED_TOXIC' | 'NOT_TOXIC';
export type ScoreSource = 'SIMULATED' | 'MODEL';

export interface QueueItem {
  comment_id: string;
  video_id: string;
  risk_score: number;
  uncertainty: number;
  model_version: string;
  score_source: ScoreSource;
  status: CommentStatus;
  received_at: string;
}

export interface CommentDetail extends QueueItem {
  text: string;
}
