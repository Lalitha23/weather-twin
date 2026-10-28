"""Today's sky mood: every conditions string the live tool can return, night, None and unknown."""
import pytest

from app.sky import MOODS, preview_mood, sky_html, sky_mood
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
