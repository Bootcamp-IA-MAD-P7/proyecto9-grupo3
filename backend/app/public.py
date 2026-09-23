"""Read-only public endpoints used by the product demo."""

from collections import defaultdict
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from app.youtube import YouTubeConfigurationError, YouTubeInputError, YouTubeService, YouTubeUnavailable

router = APIRouter(prefix="/public", tags=["public demo"])
_requests: defaultdict[str, list[float]] = defaultdict(list)


def get_youtube_service(request: Request) -> YouTubeService:
    return request.app.state.youtube_service


@router.get("/youtube/comments", summary="Fetch public YouTube comments")
async def youtube_comments(
    request: Request,
    url: Annotated[str, Query(min_length=12, max_length=300)],
) -> dict:
    now = monotonic()
    client = request.client.host if request.client else "unknown"
    settings = request.app.state.settings
    recent = [timestamp for timestamp in _requests[client] if now - timestamp < settings.public_query_window_seconds]
    if len(recent) >= settings.public_query_limit:
        raise HTTPException(429, "Se alcanzó el límite temporal de consultas públicas.")
    _requests[client] = [*recent, now]
    try:
        return await get_youtube_service(request).fetch_comments(url)
    except YouTubeInputError as error:
        raise HTTPException(422, str(error)) from None
    except YouTubeConfigurationError as error:
        raise HTTPException(503, str(error)) from None
    except YouTubeUnavailable as error:
        raise HTTPException(502, str(error)) from None
