"""Agent 2: turns Agent 1's validated summary into Advice. No tools.

run_advisor() never raises. It only sees the summary dict, never the raw
weather. If Agent 1 failed, it skips the call and records upstream_failed.
"""
import json
import time
from typing import Any

from openai import OpenAI

from agents.schemas import Advice
from agents.summarizer import MAX_TOKENS, load_prompt, make_client, parse_json


def run_advisor(model: str, summary: dict | None, client: OpenAI | None = None,
                prompt_version: str = "v1") -> dict[str, Any]:
    result: dict[str, Any] = {
        "model": model,
        "prompt_version": prompt_version,
        "input": None,
        "raw_text": None,
        "advice": None,
        "dropped_fields": [],
        "finish_reason": None,
        "error": None,
        "latency_s": None,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
    if summary is None:
        result["error"] = "upstream_failed"
        return result

    client = client or make_client()
    result["input"] = json.dumps(summary)
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": load_prompt("advisor", prompt_version)},
                {"role": "user", "content": result["input"]},
            ],
            max_tokens=MAX_TOKENS,
            temperature=0,
        )
        if resp.usage:
            result["usage"] = {
                "prompt_tokens": resp.usage.prompt_tokens or 0,
                "completion_tokens": resp.usage.completion_tokens or 0,
                "total_tokens": resp.usage.total_tokens or 0,
            }
        choice = resp.choices[0]
        result["finish_reason"] = choice.finish_reason
        result["raw_text"] = choice.message.content
        if choice.finish_reason == "length":
            result["error"] = "truncated"
            return result

        advice, dropped, error = parse_json(choice.message.content or "", Advice)
        result["advice"] = advice
        result["dropped_fields"] = dropped
        result["error"] = error
    except Exception as e:  # API or network failure is a recorded result
        result["error"] = f"api_error: {type(e).__name__}: {e}"
    finally:
        result["latency_s"] = round(time.time() - start, 3)
    return result
