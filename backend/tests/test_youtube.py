from app.youtube import YouTubeInputError, extract_video_id


def test_extract_video_id_accepts_allowed_https_formats():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_rejects_arbitrary_or_unsafe_urls():
    for value in (
        "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=too-short",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ#fragment",
    ):
        try:
            extract_video_id(value)
        except YouTubeInputError:
            pass
        else:
            raise AssertionError(f"URL should have been rejected: {value}")
