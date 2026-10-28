"""Today's live sky: pick a mood from the weather tool's words, then draw it.

Pure functions, no Streamlit. Presentation only: the mood reads the tool's
`conditions` and `time_of_day` exactly as returned, and never changes data.
Spec: docs/REDESIGN.md, "Today tab · the sky follows the weather".
"""
import random

MOODS = ("clear", "partly_cloudy", "cloudy", "fog", "rain", "snow", "storm", "night")

CONDITION_MOODS = {
    "clear sky": "clear", "mainly clear": "clear",
    "partly cloudy": "partly_cloudy",
    "overcast": "cloudy",
    "fog": "fog", "freezing fog": "fog",
    **{c: "rain" for c in (
        "light drizzle", "drizzle", "heavy drizzle", "light freezing drizzle", "freezing drizzle",
        "light rain", "rain", "heavy rain", "light freezing rain", "freezing rain",
        "light showers", "showers", "heavy showers")},
    **{c: "snow" for c in (
        "light snow", "snow", "heavy snow", "snow grains", "light snow showers", "snow showers")},
    **{c: "storm" for c in ("thunderstorm", "thunderstorm with hail", "thunderstorm with heavy hail")},
}

# Background gradient and ink (big text colour) per mood. The sky is fixed while the page
# scrolls, so ink must pass on every stop: 3:1 for big text (tests/test_sky.py measures it).
# Clear and partly cloudy use dark ink because white fails on their light lower sky.
SKIES = {
    "clear": ("linear-gradient(180deg,#3D8FE0,#7BB8F0 55%,#BFE0FA)", "#0F1B2A"),
    "partly_cloudy": ("linear-gradient(180deg,#5B9FE0,#9CC8F0 55%,#D6EAFA)", "#0F1B2A"),
    "cloudy": ("linear-gradient(180deg,#A9B9CA,#C9D5E1 50%,#E6ECF2)", "#0F1B2A"),
    "fog": ("linear-gradient(180deg,#C3CCD4,#DCE2E7 50%,#EEF1F3)", "#0F1B2A"),
    "rain": ("linear-gradient(180deg,#2C3846,#435263 55%,#66788A)", "#FFFFFF"),
    "snow": ("linear-gradient(180deg,#9FB1C3,#C7D4E0 55%,#EEF3F7)", "#0F1B2A"),
    "storm": ("linear-gradient(180deg,#1C232D,#2E3946 55%,#4A5664)", "#FFFFFF"),
    "night": ("linear-gradient(180deg,#0E1A33,#1E2F52 60%,#33466B)", "#FFFFFF"),
}


def sky_mood(conditions: str | None, time_of_day: str | None) -> str:
    """The sky for the tool's conditions text. Unknown or missing data is cloudy."""
    mood = CONDITION_MOODS.get((conditions or "").strip().lower(), "cloudy")
    if mood in ("clear", "partly_cloudy") and (time_of_day or "").strip().lower() == "night":
        return "night"
    return mood


def preview_mood(value: str | None) -> str | None:
    """The ?sky= preview value if it names a mood, else None (ignored)."""
    return value if value in MOODS else None


# Frosted chips behind small text on the sky (RGB, alpha). Must reach 4.5:1 on every stop.
CHIP_LIGHT = ((255, 255, 255), 0.55)
CHIP_DARK = ((15, 27, 42), 0.45)


def chip(mood: str) -> tuple[tuple[int, int, int], float]:
    return CHIP_DARK if is_dark(mood) else CHIP_LIGHT


def rgba(c: tuple[tuple[int, int, int], float]) -> str:
    return f"rgba({c[0][0]},{c[0][1]},{c[0][2]},{c[1]})"


def ink(mood: str) -> str:
    return SKIES[mood][1]


def is_dark(mood: str) -> bool:
    return ink(mood) == "#FFFFFF"


def _clouds(rng: random.Random, n: int, colours: tuple[str, ...], top: tuple[int, int]) -> str:
    out = []
    for i in range(n):
        w = rng.randint(160, 300)
        out.append(
            f'<div class="sk-cloud" style="--w:{w}px;--c:{colours[i % len(colours)]};'
            f'left:{rng.randint(-5, 85)}%;top:{rng.randint(*top)}px;'
            f'--dx:{rng.randint(16, 22)}px;animation-duration:{rng.randint(10, 15)}s;'
            f'animation-delay:-{rng.uniform(0, 10):.1f}s"></div>')
    return "".join(out)


def _rain(rng: random.Random, n: int) -> str:
    return "".join(
        f'<i class="sk-rain" style="left:{rng.uniform(0, 100):.1f}%;--y:{rng.uniform(35, 125):.0f}vh;'
        f'animation-duration:{rng.uniform(0.7, 1.2):.2f}s;animation-delay:-{rng.uniform(0, 1.2):.2f}s"></i>'
        for _ in range(n))


def _snow(rng: random.Random, n: int) -> str:
    return "".join(
        f'<i class="sk-snow" style="left:{rng.uniform(0, 100):.1f}%;--y:{rng.uniform(10, 100):.0f}vh;'
        f'animation-duration:{rng.uniform(7, 12):.1f}s;animation-delay:-{rng.uniform(0, 12):.1f}s">'
        f'<b style="animation-duration:{rng.uniform(2.5, 4):.1f}s"></b></i>'
        for _ in range(n))


def _haze(rng: random.Random, n: int) -> str:
    return "".join(
        f'<div class="sk-haze" style="top:{18 + i * 26}%;--dx:{rng.randint(30, 50)}px;'
        f'animation-duration:{rng.randint(18, 26)}s;animation-delay:-{rng.uniform(0, 18):.1f}s"></div>'
        for i in range(n))


def _stars(rng: random.Random, n: int) -> str:
    return "".join(
        f'<i class="sk-star" style="left:{rng.uniform(2, 98):.1f}%;top:{rng.uniform(2, 45):.1f}%;'
        f'animation-delay:-{rng.uniform(0, 4):.1f}s"></i>'
        for _ in range(n))


def sky_html(mood: str) -> str:
    """The full viewport sky layer for one mood. Positions use a fixed seed, so it renders the same every time."""
    mood = mood if mood in SKIES else "cloudy"
    rng = random.Random(f"weather-twin-{mood}")
    white = ("#FFFFFF", "#F4F8FC")
    extras = {
        "clear": lambda: '<div class="sk-sun"></div>' + _clouds(rng, 2, white, (120, 320)),
        "partly_cloudy": lambda: ('<div class="sk-sun"></div>'
                                  '<div class="sk-cloud sk-over-sun" style="--w:220px;--c:#FFFFFF;--dx:18px;'
                                  'animation-duration:12s"></div>' + _clouds(rng, 2, white, (160, 360))),
        "cloudy": lambda: _clouds(rng, 4, ("#F4F7FA", "#DCE4EC"), (40, 380)),
        "fog": lambda: _haze(rng, 3),
        "rain": lambda: _clouds(rng, 3, ("#55636F", "#3E4A56"), (20, 160)) + _rain(rng, 34),
        "snow": lambda: _clouds(rng, 2, ("#E6ECF2", "#D4DEE8"), (20, 140)) + _snow(rng, 26),
        "storm": lambda: (_clouds(rng, 3, ("#3E4A56", "#2E3946"), (10, 140)) + _rain(rng, 34)
                          + '<div class="sk-flash"></div>'),
        "night": lambda: '<div class="sk-moon"></div>' + _stars(rng, 18),
    }[mood]()
    return (f'<div class="wt-sky wt-sky-{mood}" aria-hidden="true" style="background:{SKIES[mood][0]}">'
            f'{extras}</div>')


SKY_CSS = """
.wt-sky { position:fixed; inset:0; z-index:-1; pointer-events:none; overflow:hidden; }
.sk-cloud { position:absolute; width:var(--w); height:calc(var(--w) * .34); background:var(--c);
  border-radius:999px; opacity:.92; animation:sk-drift ease-in-out infinite alternate; filter:blur(.5px); }
.sk-cloud::before, .sk-cloud::after { content:""; position:absolute; background:inherit; border-radius:50%; }
.sk-cloud::before { width:46%; height:120%; left:14%; top:-58%; }
.sk-cloud::after { width:34%; height:92%; left:50%; top:-40%; }
@keyframes sk-drift { from { transform:translateX(0); } to { transform:translateX(var(--dx)); } }
.sk-sun { position:absolute; top:84px; right:9%; width:96px; height:96px; border-radius:50%; background:#FFD666;
  box-shadow:0 0 40px 12px rgba(255,214,102,.45); animation:sk-glow 6s ease-in-out infinite alternate; }
@keyframes sk-glow { to { box-shadow:0 0 64px 22px rgba(255,214,102,.6); } }
.sk-over-sun { right:calc(9% - 70px); top:132px; }
.sk-rain { position:absolute; top:-30vh; width:2px; height:22px; border-radius:2px;
  background:linear-gradient(180deg, rgba(255,255,255,0), rgba(220,232,245,.75));
  animation:sk-fall linear infinite; }
@keyframes sk-fall { to { transform:translateY(140vh); } }
.sk-snow { position:absolute; top:-5vh; animation:sk-fall linear infinite; }
.sk-snow b { display:block; width:7px; height:7px; border-radius:50%; background:#FFFFFF;
  box-shadow:0 0 4px rgba(255,255,255,.8); animation:sk-sway ease-in-out infinite alternate; }
@keyframes sk-sway { from { transform:translateX(-12px); } to { transform:translateX(12px); } }
.sk-haze { position:absolute; left:-20vw; width:140vw; height:120px;
  background:linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.55) 30%, rgba(255,255,255,.4) 70%, rgba(255,255,255,0));
  filter:blur(18px); animation:sk-drift ease-in-out infinite alternate; }
.sk-flash { position:absolute; inset:0; background:#FFFFFF; opacity:0; animation:sk-flash 7s linear infinite; }
@keyframes sk-flash { 0%, 97.8% { opacity:0; } 98.2% { opacity:.25; } 100% { opacity:0; } }
.sk-moon { position:absolute; top:80px; right:10%; width:72px; height:72px; border-radius:50%; background:#F4F1E6;
  box-shadow:0 0 36px 8px rgba(244,241,230,.25); }
.sk-star { position:absolute; width:3px; height:3px; border-radius:50%; background:#FFFFFF; opacity:.8;
  animation:sk-twinkle 4s ease-in-out infinite alternate; }
@keyframes sk-twinkle { to { opacity:.25; } }
@media (prefers-reduced-motion: reduce) {
  .wt-sky *, .wt-sky *::before, .wt-sky *::after { animation:none !important; }
  .sk-rain, .sk-snow { transform:translateY(var(--y)); }  /* frozen in place, so the mood still reads */
}
"""
