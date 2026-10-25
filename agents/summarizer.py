"""Agent 1: calls get_weather and returns a WeatherSummary as JSON.

run_summarizer() never raises. Every failure is recorded in the result
dict under "error" so the runner can save it as a result.
"""
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from agents.schemas import WeatherSummary
from tools.weather_tool import TOOL_SPEC, get_weather

PROMPTS = Path(__file__).parent / "prompts"
USER_MESSAGE = "Summarize the current weather."
MAX_TOKENS = 2000
TIMEOUT_S = 60  # per request; a hung call becomes a recorded api_error

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def load_prompt(agent: str, version: str) -> str:
    """Read agents/prompts/<agent>_<version>.md, e.g. summarizer_v1.md."""
    return (PROMPTS / f"{agent}_{version}.md").read_text()


def make_client() -> OpenAI:
    load_dotenv()
    return OpenAI(
        base_url=os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
        api_key=os.getenv("NEBIUS_API_KEY"),
        timeout=TIMEOUT_S,
    )


def clean_text(text: str) -> str:
    """Drop <think> blocks and a surrounding code fence before parsing."""
    text = THINK_RE.sub("", text).strip()
    m = FENCE_RE.match(text)
    return m.group(1) if m else text


def parse_json(text: str, schema: type) -> tuple[dict | None, list[str], str | None]:
    """Return (parsed, dropped_fields, error) for model text against a schema."""
    try:
        data = json.loads(clean_text(text))
    except json.JSONDecodeError as e:
        return None, [], f"invalid_json: {e}"
    if not isinstance(data, dict):
        return None, [], f"schema_error: expected a JSON object, got {type(data).__name__}"
    dropped = sorted(k for k in data if k not in schema.model_fields)
    try:
        return schema.model_validate(data).model_dump(), dropped, None
    except ValidationError as e:
        return None, dropped, f"schema_error: {e}"


def _chat(client: OpenAI, model: str, messages: list, usage: dict) -> Any:
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=[TOOL_SPEC],
        tool_choice="auto",
        max_tokens=MAX_TOKENS,
        temperature=0,
    )
    if resp.usage:
        usage["prompt_tokens"] += resp.usage.prompt_tokens or 0
        usage["completion_tokens"] += resp.usage.completion_tokens or 0
        usage["total_tokens"] += resp.usage.total_tokens or 0
    return resp.choices[0]


def run_summarizer(model: str, client: OpenAI | None = None,
                   prompt_version: str = "v1") -> dict[str, Any]:
    client = client or make_client()
    result: dict[str, Any] = {
        "model": model,
        "prompt_version": prompt_version,
        "tool_called": False,
        "tool_args": None,
        "tool_output": None,
        "raw_text": None,
        "summary": None,
        "dropped_fields": [],
        "finish_reason": None,
        "error": None,
        "latency_s": None,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": load_prompt("summarizer", prompt_version)},
        {"role": "user", "content": USER_MESSAGE},
    ]
    start = time.time()
    try:
        choice = _chat(client, model, messages, result["usage"])
        msg = choice.message
        result["finish_reason"] = choice.finish_reason
        if choice.finish_reason == "length":
            result["raw_text"] = msg.content
            result["error"] = "truncated"
            return result
        if not msg.tool_calls:
            result["raw_text"] = msg.content
            result["error"] = "no_tool_call"
            return result

        result["tool_called"] = True
        result["tool_args"] = [c.function.arguments for c in msg.tool_calls]
        messages.append(msg.model_dump(exclude_none=True))
        outputs = []
        for call in msg.tool_calls:
            if call.function.name == TOOL_SPEC["function"]["name"]:
                output = get_weather()
            else:
                output = {"error": f"unknown tool {call.function.name}"}
            outputs.append(output)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(output),
            })
        result["tool_output"] = outputs[0] if len(outputs) == 1 else outputs

        choice = _chat(client, model, messages, result["usage"])
        msg = choice.message
        result["finish_reason"] = choice.finish_reason
        result["raw_text"] = msg.content
        if choice.finish_reason == "length":
            result["error"] = "truncated"
            return result
        if msg.tool_calls:
            result["error"] = "no_final_answer"
            return result

        summary, dropped, error = parse_json(msg.content or "", WeatherSummary)
        result["summary"] = summary
        result["dropped_fields"] = dropped
        result["error"] = error
    except Exception as e:  # API or network failure is a recorded result
        result["error"] = f"api_error: {type(e).__name__}: {e}"
    finally:
        result["latency_s"] = round(time.time() - start, 3)
    return result
