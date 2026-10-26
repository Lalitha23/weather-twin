"""Location comes from config/active.yaml and reaches the live tool."""
import tools.weather_live as weather_live
from app.today import display_conditions


def test_location_keeps_redmond_coordinates():
    loc = weather_live.load_location()
    assert loc == {"name": "Redmond, WA", "zip": "98052", "latitude": 47.674, "longitude": -122.121}


def test_live_tool_uses_config_coordinates(monkeypatch):
    seen = {}

    class Resp:
        def raise_for_status(self): pass
        def json(self): return {}

    def fake_get(url, params, timeout):
        seen.update(params)
        return Resp()

    monkeypatch.setattr(weather_live.requests, "get", fake_get)
    weather_live.fetch_raw()
    assert (seen["latitude"], seen["longitude"]) == (47.674, -122.121)


def test_display_conditions_only_changes_the_card_words():
    assert display_conditions("overcast") == "Cloudy"
    assert display_conditions("light rain") == "Light rain"
    assert display_conditions(None) == ""
    assert weather_live.conditions(3) == "overcast"  # the tool's text is unchanged
