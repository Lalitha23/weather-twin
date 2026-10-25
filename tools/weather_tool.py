"""The one weather tool both agents see: get_weather.

WEATHER_BACKEND=live|twin picks the backend. The output never says which
backend ran, so the agents cannot tell.
"""
import os
from typing import Any

import requests

TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "Get the current weather for Redmond, WA in metric units: "
            "temperature, rain chance over the next 6 hours, wind, "
            "conditions and time of day."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


def _backend() -> str:
    return os.getenv("WEATHER_BACKEND", "live").strip().lower()


def get_weather() -> dict[str, Any]:
    """Return the weather dict, or {"error": ...} if the source fails."""
    backend = _backend()
    try:
        if backend == "live":
            from tools.weather_live import get_weather_live
            return get_weather_live()
        if backend == "twin":
            try:
                from tools.weather_twin import get_weather_twin
            except ImportError:
                raise NotImplementedError("twin backend not built yet") from None
            return get_weather_twin()
    except requests.Timeout:
        return {"error": "timeout"}
    except requests.RequestException as e:
        return {"error": f"request failed: {type(e).__name__}"}
    except ValueError as e:
        return {"error": f"bad response: {e}"}
    raise ValueError(f"Unknown WEATHER_BACKEND={backend!r}, expected live or twin")
