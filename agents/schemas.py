"""Pydantic models for the two agent outputs.

Extra fields are ignored rather than rejected; the summarizer records
their names in dropped_fields so nothing disappears silently.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class WeatherSummary(BaseModel):
    """Agent 1 output. Numbers may be None when the data is missing."""
    model_config = ConfigDict(extra="ignore")

    temperature_c: float | None
    rain_chance_pct: float | None
    wind_kph: float | None
    conditions: str | None
    time_of_day: Literal["morning", "afternoon", "evening", "night"] | None
    data_ok: bool
    notes: str


class Advice(BaseModel):
    """Agent 2 output."""
    model_config = ConfigDict(extra="ignore")

    jacket: bool
    umbrella: bool
    why: str
    confident: bool
