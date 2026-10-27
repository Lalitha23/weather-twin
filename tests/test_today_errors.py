"""The Today Details line: error type and short message, never a key or a trace."""
from app.today import error_detail, safe_detail

KEY = "nb-live-9f8e7d6c5b4a39281706f5e4d3c2b1a0ffeeddcc"


def test_detail_keeps_type_and_message():
    d = error_detail("Agent 1", "api_error: RateLimitError: Error code: 429 - too many requests")
    assert d == "Agent 1 · RateLimitError: Error code: 429 - too many requests"


def test_detail_never_shows_the_api_key(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", KEY)
    d = error_detail("Agent 1", f"api_error: AuthenticationError: Incorrect API key provided: {KEY}")
    assert KEY not in d and "[redacted]" in d and d.startswith("Agent 1 · AuthenticationError")


def test_detail_redacts_key_like_strings_even_when_not_in_env(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    d = safe_detail("AuthenticationError: bad key sk-abc123def456 and Bearer xyz.secret")
    assert "sk-abc123def456" not in d and "xyz.secret" not in d


def test_detail_is_one_short_line_without_a_trace():
    trace = "ValueError: boom\nTraceback (most recent call last):\n  File \"x.py\", line 1"
    d = safe_detail(trace)
    assert d == "ValueError: boom"
    assert len(safe_detail("x" * 10 + " " + "word " * 200)) <= 240


def test_detail_pulls_the_message_out_of_an_api_error_body():
    raw = ("api_error: AuthenticationError: Error code: 401 - {'error': {'type': 'invalid_request_error', "
           "'message': \"Couldn't authenticate. Reason: Unable authenticate\", 'param': None, "
           "'code': 'unauthenticated'}, 'detail': 'Invalid request. Please check your key.'}")
    assert error_detail("Agent 1", raw) == \
        "Agent 1 · AuthenticationError (401): Couldn't authenticate. Reason: Unable authenticate"


def test_detail_without_a_body_is_unchanged():
    assert error_detail("Weather tool", "timeout") == "Weather tool · timeout"
    assert error_detail("Agent 2", "invalid_json: Expecting value") == "Agent 2 · invalid_json: Expecting value"
