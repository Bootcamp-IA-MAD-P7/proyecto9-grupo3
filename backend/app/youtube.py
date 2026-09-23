"""Official YouTube Data API integration for the public, read-only demo."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import httpx

from app.comments.scoring import Scorer

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


class YouTubeInputError(ValueError):
    pass


class YouTubeConfigurationError(RuntimeError):
    pass


class YouTubeUnavailable(RuntimeError):
    pass


def extract_video_id(value: str) -> str:
    """Accept only HTTPS YouTube URLs and return a validated video id."""
    try:
        parsed = urlparse(value.strip())
    except ValueError as error:
        raise YouTubeInputError("Introduce un enlace válido de YouTube.") from error
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise YouTubeInputError("Solo se permiten enlaces HTTPS de youtube.com o youtu.be.")
    video_id = ""
    if parsed.hostname == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif parsed.path in {"/watch", "/watch/"}:
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    else:
        parts = parsed.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] in {"shorts", "embed", "live"}:
            video_id = parts[1]
    if not VIDEO_ID.fullmatch(video_id) or parsed.fragment or (parsed.hostname == "youtu.be" and parsed.query):
        raise YouTubeInputError("No se pudo extraer un ID de vídeo de YouTube válido.")
    return video_id


class YouTubeService:
    def __init__(self, api_key: str | None, scorer: Scorer, max_results: int = 50):
        self.api_key = api_key
        self.scorer = scorer
        self.max_results = max_results

    async def fetch_comments(self, url: str) -> dict:
        video_id = extract_video_id(url)
        if not self.api_key:
            raise YouTubeConfigurationError("La API de YouTube no está configurada en el servidor.")
        params = {"part": "snippet", "videoId": video_id, "maxResults": self.max_results,
                  "textFormat": "plainText", "key": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://www.googleapis.com/youtube/v3/commentThreads", params=params)
        except httpx.HTTPError as error:
            raise YouTubeUnavailable("No se pudo consultar YouTube en este momento.") from error
        if response.status_code != 200:
            reason = ""
            try:
                reason = response.json().get("error", {}).get("errors", [{}])[0].get("reason", "")
            except (ValueError, IndexError, AttributeError):
                pass
            if reason in {"commentsDisabled", "videoNotFound"}:
                raise YouTubeUnavailable("Los comentarios están desactivados o el vídeo no está disponible.")
            if reason in {"quotaExceeded", "dailyLimitExceeded"}:
                raise YouTubeUnavailable("Se alcanzó el límite de cuota de YouTube. Inténtalo más tarde.")
            raise YouTubeUnavailable("YouTube no pudo devolver los comentarios solicitados.")
        payload = response.json()
        items = []
        for item in payload.get("items", []):
            snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            text = str(snippet.get("textDisplay") or snippet.get("textOriginal") or "").strip()
            if not text:
                continue
            score = self.scorer.score_comment(text)
            items.append({
                "comment_id": item.get("id", "")[:128], "video_id": video_id, "text": text,
                "author": str(snippet.get("authorDisplayName", "Cuenta de YouTube"))[:200],
                "published_at": snippet.get("publishedAt"), "likes": int(snippet.get("likeCount", 0) or 0),
                "risk_score": score.risk_score, "uncertainty": score.uncertainty,
                "model_version": score.model_version, "score_source": score.score_source,
                "status": "PENDING",
            })
        return {"video_id": video_id, "fetched_at": datetime.now(timezone.utc), "items": items}
