"""Today's sky mood: every conditions string the live tool can return, night, None and unknown."""
import re

import pytest

from app.sky import MOODS, SKIES, chip, ink, preview_mood, sky_html, sky_mood
from tools.weather_live import WEATHER_CODES

EXPECTED = {
    "clear sky": "clear", "mainly clear": "clear", "partly cloudy": "partly_cloudy", "overcast": "cloudy",
    "fog": "fog", "freezing fog": "fog",
    "light drizzle": "rain", "drizzle": "rain", "heavy drizzle": "rain", "light freezing drizzle": "rain",
    "freezing drizzle": "rain", "light rain": "rain", "rain": "rain", "heavy rain": "rain",
    "light freezing rain": "rain", "freezing rain": "rain", "light showers": "rain", "showers": "rain",
    "heavy showers": "rain",
    "light snow": "snow", "snow": "snow", "heavy snow": "snow", "snow grains": "snow",
    "light snow showers": "snow", "snow showers": "snow",
    "thunderstorm": "storm", "thunderstorm with hail": "storm", "thunderstorm with heavy hail": "storm",
}


@pytest.mark.parametrize("conditions,mood", EXPECTED.items())
def test_every_conditions_string(conditions, mood):
    assert sky_mood(conditions, "afternoon") == mood


def test_table_covers_every_string_the_live_tool_returns():
    assert set(WEATHER_CODES.values()) == set(EXPECTED)


@pytest.mark.parametrize("conditions", ["clear sky", "mainly clear", "partly cloudy"])
def test_clear_or_partly_cloudy_at_night_is_night(conditions):
    assert sky_mood(conditions, "night") == "night"


@pytest.mark.parametrize("conditions,mood", [("rain", "rain"), ("overcast", "cloudy"), ("snow", "snow")])
def test_other_skies_keep_their_mood_at_night(conditions, mood):
    assert sky_mood(conditions, "night") == mood


@pytest.mark.parametrize("conditions,time_of_day", [(None, None), (None, "night"), ("", "morning"),
                                                    ("volcanic ash", "afternoon")])
def test_missing_or_unknown_is_cloudy(conditions, time_of_day):
    assert sky_mood(conditions, time_of_day) == "cloudy"


def test_preview_accepts_only_mood_names():
    assert preview_mood("rain") == "rain"
    assert preview_mood("tornado") is None
    assert preview_mood(None) is None


@pytest.mark.parametrize("mood", MOODS)
def test_sky_html_is_decorative_and_stable(mood):
    html = sky_html(mood)
    assert 'aria-hidden="true"' in html and f"wt-sky-{mood}" in html
    assert html == sky_html(mood)


def _luminance(rgb: tuple[float, float, float]) -> float:
    c = [x / 255 for x in rgb]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contrast(a, b) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _hex(h: str) -> tuple[int, int, int]:
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _stops(mood: str) -> list[tuple[int, int, int]]:
    return [_hex(h) for h in re.findall(r"#[0-9A-Fa-f]{6}", SKIES[mood][0])]


@pytest.mark.parametrize("mood", MOODS)
def test_big_text_ink_reaches_3_to_1_on_every_gradient_stop(mood):
    """The sky is fixed while the page scrolls, so big text can sit over any stop. No shadow counted."""
    assert min(_contrast(_hex(ink(mood)), s) for s in _stops(mood)) >= 3


@pytest.mark.parametrize("mood", MOODS)
def test_small_text_on_its_chip_reaches_4_5_to_1_on_every_stop(mood):
    (rgb, alpha), text = chip(mood), _hex(ink(mood))
    for stop in _stops(mood):
        composite = tuple(alpha * c + (1 - alpha) * s for c, s in zip(rgb, stop))
        assert _contrast(text, composite) >= 4.5
