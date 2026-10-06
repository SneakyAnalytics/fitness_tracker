"""The coach's tool loop, exercised with a fake Anthropic client (no network)."""
import json
from types import SimpleNamespace

from src.utils.ai_chat_session import AIChatSession
from src.utils.ai_coach_config import AIModel


class FakeStream:
    def __init__(self, text, final):
        self._text, self._final = text, final

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        yield from self._text

    def get_final_message(self):
        return self._final


def usage():
    return SimpleNamespace(input_tokens=100, output_tokens=20, cache_creation_input_tokens=0,
                           cache_read_input_tokens=0)


class FakeMessages:
    def __init__(self):
        self.calls = []

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            tool = SimpleNamespace(type="tool_use", id="tu_1", name="get_goals", input={})
            final = SimpleNamespace(stop_reason="tool_use", usage=usage(),
                                    content=[SimpleNamespace(type="text", text="Let me check."), tool])
            return FakeStream(["Let me check."], final)
        final = SimpleNamespace(stop_reason="end_turn", usage=usage(),
                                content=[SimpleNamespace(type="text", text="You have no active goals.")])
        return FakeStream(["You have no ", "active goals."], final)


class FakeCoach:
    def __init__(self):
        self.model = AIModel.CLAUDE_OPUS
        self.client = SimpleNamespace(messages=FakeMessages())
        self.usages = []

    def _record_usage(self, u):
        self.usages.append(u)

    def messages_api(self):
        return self.client.messages, {}


def test_tool_call_is_executed_and_only_coach_text_is_kept():
    coach = FakeCoach()
    session = AIChatSession("2026-09-28")
    session._coach = coach
    session._db = SimpleNamespace(db_path=None)
    session._system_prompt = "SYSTEM"

    streamed = "".join(session._converse("unused fallback prompt"))

    calls = coach.client.messages.calls
    assert len(calls) == 2
    # System prompt is cached; tools offered; no temperature for Opus 5.
    assert calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert any(t["name"] == "search_prior_conversations" for t in calls[0]["tools"])
    assert "temperature" not in calls[0]
    # The tool result went back in a single user message after the assistant's tool_use.
    second = calls[1]["messages"]
    assert second[-2]["role"] == "assistant"
    result = second[-1]["content"][0]
    assert result["type"] == "tool_result" and result["tool_use_id"] == "tu_1"
    assert "goals" in json.loads(result["content"])
    # Status line is shown while streaming but not stored as the coach's words.
    assert "🔎" in streamed
    assert session._last_turn_text == "Let me check.\n\nYou have no active goals."
    assert len(coach.usages) == 2


def test_history_is_sent_as_real_messages():
    session = AIChatSession("2026-09-28", messages=[
        {"role": "assistant", "content": "How did the week feel?"},
        {"role": "user", "content": "Tired legs Thursday."},
    ])
    msgs = session._api_messages()
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert msgs[-1]["content"] == "Tired legs Thursday."
