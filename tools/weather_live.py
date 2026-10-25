"""Live weather backend: Open-Meteo forecast API (no API key needed).

fetch_raw() returns the untouched Open-Meteo JSON.
parse() turns that JSON into the tool output. The twin backend reuses
parse() on recorded responses, so live and twin match field for field.
"""
from typing import Any

import requests

URL = "https://api.open-meteo.com/v1/forecast"
LATITUDE = 47.674  # Redmond, WA
LONGITUDE = -122.121
TIMEZONE = "America/Los_Angeles"
TIMEOUT_S = 10
RAIN_WINDOW_HOURS = 6

# WMO weather interpretation codes, as documented by Open-Meteo.
WEATHER_CODES: dict[int, str] = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "light freezing drizzle",
    57: "freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light showers",
    81: "showers",
    82: "heavy showers",
    85: "light snow showers",
    86: "snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}


def fetch_raw() -> dict[str, Any]:
    """Call Open-Meteo once and return the raw JSON. Raises requests errors."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "wind_speed_unit": "kmh",
        "current": "temperature_2m,wind_speed_10m,weather_code",
        "hourly": "precipitation_probability",
        # Two days so the 6 hour rain window still fits late in the evening.
        "forecast_days": 2,
    }
    resp = requests.get(URL, params=params, timeout=TIMEOUT_S)
    resp.raise_for_status()
    return resp.json()


def time_of_day(hour: int) -> str:
    if 5 <= hour <= 11:
        return "morning"
    if 12 <= hour <= 16:
        return "afternoon"
    if 17 <= hour <= 20:
        return "evening"
    return "night"


def conditions(code: Any) -> str | None:
    if code is None:
        return None
    return WEATHER_CODES.get(int(code), f"unknown (code {code})")


def max_rain_chance(raw: dict[str, Any], now: str | None) -> int | None:
    """Highest hourly precipitation probability over the next 6 hours.

    rain_chance_pct uses this window, not just the current hour, so an
    umbrella decision covers the trip out and back.
    """
    hourly = raw.get("hourly") or {}
    times = hourly.get("time") or []
    probs = hourly.get("precipitation_probability") or []
    if not now or not times or not probs:
        return None
    current_hour = now[:13] + ":00"  # "2026-10-25T09:15" -> "2026-10-25T09:00"
    if current_hour not in times:
        return None
    start = times.index(current_hour)
    window = [p for p in probs[start:start + RAIN_WINDOW_HOURS] if p is not None]
    return max(window) if window else None


def parse(raw: dict[str, Any]) -> dict[str, Any]:
    """Map Open-Meteo JSON to the tool output. Missing fields become None."""
    current = raw.get("current") or {}
    now = current.get("time")
    return {
        "temperature_c": current.get("temperature_2m"),
        "rain_chance_pct": max_rain_chance(raw, now),
        "wind_kph": current.get("wind_speed_10m"),
        "conditions": conditions(current.get("weather_code")),
        "time_of_day": time_of_day(int(now[11:13])) if now else None,
        "observed_at": now,
    }


def get_weather_live() -> dict[str, Any]:
    return parse(fetch_raw())
