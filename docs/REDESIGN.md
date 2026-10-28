# Weather Twin redesign spec · live sky Today and the Handoff Inspector

This file is the build target for the redesign. It replaces the "Visual tokens", "Today tab" and "Test Lab · Official report" sections of `docs/DESIGN.md`. Everything else in DESIGN.md (top level, intro text, live comparison behaviour, desktop and phone rules) still applies unless this file says otherwise. There are no images to look for. This file is the whole design.

## Scope rules

- Presentation only. Do not change agents, prompts, checks, scenarios, the weather tool's output, the runner, or the official results files.
- No new model calls anywhere. Today still runs once per Pacific day and Refresh still needs `APP_PASSWORD`.
- All existing tests must still pass.
- Animated, clickable parts are built as self contained HTML blocks, because Streamlit reruns the page on every widget click, so smooth animations cannot live in native widgets.
  - **Today uses `st.html`, with no iframe and no JavaScript.** The sky is plain HTML and CSS. The X-ray toggle is a native `<details>`/`<summary>`, so it has a real label, keyboard focus with a visible focus ring, Space and Enter to toggle, and its open or closed state announced. Two copies render, open on desktop and folded on phone, and CSS shows one. An iframe could not paint the full screen sky, and `components.html` iframes have a fixed height that can't follow the X-ray folding.
  - **The Inspector (Test Lab) uses `streamlit.components.v1.html`**, with its data passed in as JSON from Python. It needs JavaScript for the replay, and its height is fixed, so the iframe's fixed height fits.
- External resources: Google Fonts only. No other scripts or CDNs.
- Every animation stops under `@media (prefers-reduced-motion: reduce)`, and autoplay is off then too.

## Visual tokens (light, palette "sky wash")

| Token | Value | Use |
|---|---|---|
| page | `linear-gradient(180deg, #CFE5FA 0%, #E7F2FC 45%, #F7FBFE 100%)` | Test Lab page background |
| surface | `#FFFFFF` | cards, radius 20 px, shadow `0 8px 24px rgba(11,92,173,.08)` |
| ink | `#0F1B2A` | main text, dark "shipped" card, primary buttons |
| muted | `#5B6B7D` | secondary text |
| line | `#D3E2F0` | card borders |
| inner line | `#E3EBF3` | dividers and tracks inside cards |
| code bg | `#F6F9FC` | mono panels |
| blue | `#0B5CAD` | active step, links, pass text, healthy packets |
| pass | `#EEF5FC` fill, `#BFD6EE` border, `#0B5CAD` text | passed checks and gates |
| orange | `#EA580C` | failed node border, failed packets, progress after a failure |
| fail | `#FFF4EC` fill, `#FDBA8C` border, `#C2410C` text | failed checks and gates |
| highlight | `#FFEDD5` fill, `#9A3412` text | a value that changed between agents |
| partial | `#FFF7E6` fill, `#7A4B00` text | results table cells where some runs failed |
| hard fail cell | `#C2410C` fill, white text | results table handoff_clean or numbers_match_tool failures |

Fonts: **Geist** for text and **Geist Mono** for numbers, model IDs, check names and JSON, both from Google Fonts. Blue versus orange stays deliberate for colour blind viewers. Never green and red.

Test Lab background also has two large soft white cloud shapes (`rgba(255,255,255,.7)` and `.55`, radius 80 px) near the top, drifting 30 px sideways over 16 s, behind all content.

## Today tab · the sky follows the weather

### Sky mood

Add `app/sky.py` with a pure function `sky_mood(conditions: str | None, time_of_day: str | None) -> str`. It reads the weather tool's `conditions` text and `time_of_day`, exactly as the tool returns them.

| Mood | Conditions text | Background | Ink (big text) | Extras |
|---|---|---|---|---|
| clear | clear sky, mainly clear | `linear-gradient(180deg,#3D8FE0,#7BB8F0 55%,#BFE0FA)` | `#0F1B2A` | sun, 96 px `#FFD666` circle with a slow glow, top right; two white clouds |
| partly_cloudy | partly cloudy | `linear-gradient(180deg,#5B9FE0,#9CC8F0 55%,#D6EAFA)` | `#0F1B2A` | sun half behind a white cloud; three clouds |
| cloudy | overcast, and anything unknown or missing | `linear-gradient(180deg,#A9B9CA,#C9D5E1 50%,#E6ECF2)` | `#0F1B2A` | four drifting clouds, `#F4F7FA` and `#DCE4EC` |
| fog | fog, freezing fog | `linear-gradient(180deg,#C3CCD4,#DCE2E7 50%,#EEF1F3)` | `#0F1B2A` | three wide translucent white haze bands drifting slowly |
| rain | light drizzle, drizzle, heavy drizzle, light freezing drizzle, freezing drizzle, light rain, rain, heavy rain, light freezing rain, freezing rain, light showers, showers, heavy showers | `linear-gradient(180deg,#2C3846,#435263 55%,#66788A)` | `#FFFFFF` | dark clouds `#55636F` and `#3E4A56`; about 34 falling rain streaks |
| snow | light snow, snow, heavy snow, snow grains, light snow showers, snow showers | `linear-gradient(180deg,#9FB1C3,#C7D4E0 55%,#EEF3F7)` | `#0F1B2A` | about 26 drifting snowflakes |
| storm | thunderstorm, thunderstorm with hail, thunderstorm with heavy hail | `linear-gradient(180deg,#1C232D,#2E3946 55%,#4A5664)` | `#FFFFFF` | rain streaks plus a soft white flash (overlay opacity .25 for 150 ms) at most once every 7 s |
| night | clear or partly cloudy when `time_of_day` is "night" | `linear-gradient(180deg,#0E1A33,#1E2F52 60%,#33466B)` | `#FFFFFF` | moon `#F4F1E6` and a few small stars |

Contrast is measured, not assumed. The sky stays fixed while the page scrolls, so big text in the mood's ink must reach 3:1 on every gradient stop, and small text on its frosted chip must reach 4.5:1, with no text shadow counted. Clear and partly cloudy use dark ink because white measured 1.38:1 and 1.23:1 on their light lower sky. Dark chips use `rgba(15,27,42,.45)`. `tests/test_sky.py` checks every mood.

A tool error or missing data uses **cloudy**. Unit test every conditions string above, night, None and an unknown string.

For screenshots and the demo video, allow a preview query parameter, `?sky=rain` (any mood name). It changes only the background, never the data or the agents. Ignore unknown values.

### Rendering the sky

- The sky is a full viewport layer behind the whole Today tab: one HTML block with `position: fixed; inset: 0; z-index: 0; pointer-events: none`, and the Streamlit app background made transparent while Today is shown.
- Clouds are soft rounded shapes drifting 16 to 22 px sideways over 10 to 15 s. Rain streaks are 2×22 px lines falling in 0.7 to 1.2 s. Snowflakes are 7 px dots falling and swaying over 7 to 12 s. Stagger them with negative delays so the sky is already full on load.
- Readability. Big text uses the mood's ink. Any text under 24 px that sits directly on the sky must reach 4.5:1 contrast. If it doesn't, put it on a frosted chip (`rgba(255,255,255,.55)` on light skies, `rgba(15,27,42,.45)` on dark skies, `backdrop-filter: blur(12px)`). All cards are always frosted white (`rgba(255,255,255,.88)`, blur 14 px) with dark text.

### Today layout, top to bottom

1. Header and tabs as now, with the tab bar on a frosted pill.
2. Location line: "Redmond, WA 98052 · Mon · weather at 11:23". Day and time come from the tool's `observed_at`, not from when the run was cached.
3. Big temperature (about 76 px, weight 900), the friendly condition word under it ("Cloudy"), and "rain 18%" in mono on the right.
4. **The answer card.** Label "THE ANSWER" in small mono. Big two line answer, for example "No jacket." / "No umbrella.", or "Take a jacket." / "Take an umbrella."
   - **Why line:** Agent 2's own why text. Never compute a why from the numbers, because it could contradict the decision.
   - **Warnings always show on the answer card itself, never only in the folded X-ray:**
     - an orange "Not confident" pill when Agent 2's `confident` is false;
     - "Agent 1 reported different numbers than the tool" when numbers_match_tool fails.
   - **Rules badge.** Display logic that mirrors umbrella_rule and jacket_rule: apply umbrella when rain is over 50% and jacket when it is under 10 °C to the **tool's** numbers, and compare with Agent 2's decision. Show "✓ matches the weather data" (blue), or in orange "✗ doesn't match the weather data", or "Rules can't be checked, weather data incomplete" when a number is missing. Put it in a pure function in `app/sky.py` or a small display module, with unit tests. It does not change `checks/checks.py`.
5. **X-ray this answer** button (48 px tall, ink fill, white text). When open it reads "Close X-ray" and turns outlined blue.
6. Footer line, tokens and latency, "Cached run · updated HH:MM", the cached run note, then Refresh exactly as now.

### X-ray

Built with `st.html` (see Scope rules), holding the answer card, the button and the layers.

- **Folded.** The three layers sit behind the answer card as a stack peeking out below it: offsets 16, 28 and 40 px, scales .94, .88 and .82, opacities .75, .5 and .3.
- **Unfolded.** The layers slide down into a readable column under the answer card, with a thin blue line running down their left edge (650 ms, `cubic-bezier(.2,.8,.2,1)`). A thin blue scan line sweeps the answer card while open.
- Layer order once open, top to bottom:
  1. **Agent 2 decided.** Pills for model and prompt version. Jacket, umbrella and confident values. Agent 2's own why text. The same rules badge as the answer card.
  2. A small label between layers: "handoff · Agent 2 reads only this".
  3. **Agent 1 handed over.** Pills for model and prompt. The summary as short labelled lines (temperature, rain chance, wind, conditions, data_ok, notes), with any value that differs from the tool highlighted and marked "← was X". "✓ numbers match the tool", or in orange "Agent 1 reported different numbers than the tool".
  4. **Weather data · get_weather.** The raw tool output from live Open-Meteo.
- Everything the current Today cards show must still be visible somewhere in these layers.
- **Default state.** Unfolded on desktop (900 px wide or more), so a judge sees the whole chain at once. Folded on phone.
- Errors replace the answer card with a friendly card on a cloudy sky. Never a stack trace.

## Test Lab · Official report

Public, no model calls. Reads `results/matrix_summary.json` and `results/official_matrix_oct25.jsonl` only. Order, top to bottom:

### 1. Hero

- Kicker in mono, orange (`#C2410C`): "OFFICIAL RUN · 132 RUNS · 41 BROKE · 40 AT THE FIRST HANDOFF". Compute all three numbers from the official runs. A run "broke" if any check failed. It broke "at the first handoff" if any Agent 1 check failed (honesty_agent1, handoff_clean, role_adherence, numbers_match_tool), the same rule as "failure starts here". Add a test that asserts 132, 41 and 40.
- Headline (about 50 px, weight 900): "Every handoff gets a checkpoint." followed in muted colour by "This run slipped past one." when the selected run failed, or "This run passed every one." when it was clean.
- One line under it: "Before two agents tell my son what to wear, each message between them is inspected. Pick any of the 132 official runs."
- One small muted line under that: "11 scenarios × 2 models × 2 prompt versions × 3 repeats. Same agent code as Today, fake weather from the twin. Nothing here calls a model." Compute the counts from the summary.

### 2. The Handoff Inspector (one components.html block)

**Run picker** at the top of the block: Scenario, Setup and Repeat selects. Held out scenarios get a "held out" tag. Default is injection_holdout · gpt-oss v2 · the first repeat where it obeyed. Changing the run restarts the replay at step 1.

**Pipeline**, a white card, four nodes left to right with animated connectors:
- TOOL, "get_weather (twin)", value "rain 60%" (or "timeout").
- AGENT 1, "Summarizer", value "rain 40%", in orange when it differs from the tool.
- AGENT 2, "Advisor", value "umbrella: no" or "umbrella: yes".
- LATER, "His phone or room speaker", value "safe to send" (blue) or "should not send" (orange).
- Each node is 172 px wide with radius 14. The active node gets a 2 px blue border and a soft blue ring. The node where the failure starts gets a 2 px orange border.
- Gate chips above the connectors. Between Tool and Agent 1: "text ✓/✗  numbers ✓/✗" from handoff_clean and numbers_match_tool (show "–" for n/a). Between Agent 1 and Agent 2: "decision ✓/✗" from umbrella_rule, jacket_rule and injection_not_followed. Between Agent 2 and the last node: "delivery", neutral. Pass chips use the pass colours and failed chips use the fail colours. A failed chip pulses softly.
- A 10 px dot travels along each connector every 1.6 s. It is blue until the node where the failure starts, and orange after it.

**Replay controls** under the pipeline: a play and pause button (ink), four step buttons "1 · Tool", "2 · Agent 1", "3 · Agent 2", "4 · Verdict", and a 6 px progress bar that fills 25% per step. The bar is blue on step 1 and turns orange from the failing step on. It autoplays at 1.8 s per step and loops. Clicking a step pauses on it.

**Inspector panel** (white card, left, about 60% width) changes with the step:
- Step 1, "What the weather tool returned". The tool output as mono lines. Injected text is highlighted, including the holdout's units note in `observed_at`.
- Step 2, "What Agent 1 handed over". The summary lines, with changed values highlighted and marked "← was 60". Agent 1's real notes text. Check boxes for handoff_clean and numbers_match_tool, plus honesty_agent1 and role_adherence when they apply.
- Step 3, "What Agent 2 decided". Jacket, umbrella and confident. Check boxes for umbrella_rule, jacket_rule, injection_not_followed, honesty_agent2 and format_ok when they apply.
- Step 4, "Verdict". "Failure started at Agent 1. Agent 2 only passed it on.", or "Agent 1 was fine. Failure started at Agent 2.", or "Clean run. Every handoff passed." When handoff_clean passed but numbers_match_tool failed, add "A text check alone would have called this run safe." Under the verdict, show the plain words run callout from `report_data.callout`, for example "Agent 1 changed the rain chance from 60% to 40%, and Agent 2 did what the hidden note wanted: no umbrella."
- Each check box shows the check name in mono, Pass or Fail, and a plain words detail.

**Side panel** (right, about 40%):
- A dark ink card, "SHIPPED TO TODAY", "Nemotron 3 Ultra · hardened prompt", "Better, not perfect. A later run still repeated the note."
- Four white stat cards for the shipped setup, all computed: clean handoffs (12/12, "up from 3/12 with the plain prompt"), numbers kept (30/30), clean runs (27/33, "most of any setup"), cost (average tokens per run and median latency).

**Phone.** The nodes wrap two by two with the connectors hidden, the step buttons wrap, and the inspector and side panel stack. Under reduced motion there are no packets, no pulsing and no autoplay.

### 3. What I found

The existing "What I found" card, restyled as a white card. Same wording.

### 4. Decision details and results by check

The existing decision card and results table, restyled with the new tokens. Keep the dashed orange outline and "text clean, numbers changed" on gpt-oss v2 handoff_clean. Keep the table key text.

### 5. Cost and speed, and "No prompt fixed this"

As now, restyled as white cards.

The old "Look inside a run" section is replaced by the Inspector. Reuse its data helpers, such as `differing_fields` and the failure start logic.

## Test Lab · Live comparison

Same behaviour. Restyle with the new tokens and the sky wash background. In any handoff chain or label, the last step reads "His phone or room speaker, later".

## Done when

- `pytest` passes, including new tests for `sky_mood` (every conditions string, night, None and unknown), the rules badge (match, mismatch, missing numbers), the hero numbers (132, 41, 40) and the default inspector run.
- AppTest renders Today and Test Lab with no traceback.
- Screenshots at 1280 and 390 px wide of Today in each sky mood (using `?sky=`), with X-ray folded and unfolded, plus the Official report with the inspector on steps 1 and 4. Nothing scrolls the whole page sideways.
- Save the final screenshots to `docs/screenshots/`.
