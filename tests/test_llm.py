import pandas as pd
import pytest

from wearable_data_explorer import llm


@pytest.fixture
def df():
    """A tiny table. The steps values are distinctive, to check they never reach the prompt."""
    return pd.DataFrame(
        {
            "participant": ["1487", "2201"],
            "date": pd.to_datetime(["2021-07-06", "2022-04-21"]),
            "steps": [987654.0, 123456.0],
        }
    )


class FakeResponse:
    """Stands in for the response of requests.post."""

    def __init__(self, status_code):
        self.status_code = status_code
        self.text = "fake error text"

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": '{"metric": "steps"}'}]}}]}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise llm.requests.HTTPError(str(self.status_code), response=self)  # type: ignore[arg-type]


def fake_http(monkeypatch, status_codes) -> list[int]:
    """Make requests.post answer with the given status codes, one per call.

    Returns a list that gets one entry per call, so a test can count the calls.
    """
    codes = iter(status_codes)
    calls: list[int] = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return FakeResponse(next(codes))

    monkeypatch.setattr(llm.requests, "post", fake_post)
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)
    return calls


def test_prompt_lists_metrics_and_participants_but_no_data(df):
    prompt = llm.build_system_prompt(df)
    assert "sleep_hours" in prompt
    assert "1487" in prompt and "2201" in prompt
    assert "2021-07-06" in prompt and "2022-04-21" in prompt
    assert "987654" not in prompt  # the model never sees the data itself


def test_valid_reply_becomes_a_spec(monkeypatch, df):
    reply = '{"metric": "sleep_hours", "by": "weekday"}'
    monkeypatch.setattr(llm, "_call_gemini", lambda system, user, key, model: reply)
    spec = llm.question_to_spec("sleep by weekday", df, api_key="test-key")
    assert spec.metric == "sleep_hours"
    assert spec.by == "weekday"


def test_invalid_reply_is_retried_once(monkeypatch, df):
    replies = iter(['{"metric": "steps", "sql": "DROP TABLE x"}', '{"metric": "steps"}'])
    messages_sent = []

    def fake_call(system, user, key, model):
        messages_sent.append(user)
        return next(replies)

    monkeypatch.setattr(llm, "_call_gemini", fake_call)
    spec = llm.question_to_spec("steps", df, api_key="test-key")
    assert spec.metric == "steps"
    assert len(messages_sent) == 2
    assert "not a valid spec" in messages_sent[1]


def test_gives_up_after_two_invalid_replies(monkeypatch, df):
    monkeypatch.setattr(llm, "_call_gemini", lambda system, user, key, model: "not json")
    with pytest.raises(llm.LLMError):
        llm.question_to_spec("steps", df, api_key="test-key")


def test_missing_api_key_is_reported(monkeypatch, df):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(llm.LLMError, match="API key"):
        llm.question_to_spec("steps", df)


def test_temporary_server_error_is_retried(monkeypatch):
    calls = fake_http(monkeypatch, [503, 503, 200])
    text = llm._call_gemini("system", "question", "test-key", "some-model")
    assert text == '{"metric": "steps"}'
    assert len(calls) == 3


def test_other_errors_are_not_retried(monkeypatch):
    calls = fake_http(monkeypatch, [404])
    with pytest.raises(llm.LLMError, match="404"):
        llm._call_gemini("system", "question", "test-key", "some-model")
    assert len(calls) == 1
