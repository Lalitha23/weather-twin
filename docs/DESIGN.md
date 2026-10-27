# Weather Twin app design spec

Build target for step 7. Streamlit cannot match the mockup pixel for pixel. Keep the structure, order, colours and wording. Use `st.markdown(..., unsafe_allow_html=True)` with small HTML blocks and one shared CSS block where native widgets fall short.

## Visual tokens

| Token | Value | Use |
|---|---|---|
| ground | `#F4F5F7` | page background |
| surface | `#FFFFFF` | cards, radius 16 to 18 px |
| ink | `#15181D` | main text, decision card background |
| muted | `#5B6470` | secondary text (passes contrast on ground) |
| line | `#E1E4E9` | borders, dividers |
| blue | `#1D5FBF` | primary buttons, umbrella tile, active tab underline |
| pass fill / text | `#E3ECFA` / `#16498F` | all passed |
| partial fill / text | `#FFF3DC` / `#6B4400` | some failed |
| hard fail | `#B5530E` fill, white text | handoff_clean or numbers_match_tool failures, "newly broken" |
| fail soft | `#FCEBDD` / `#7A3507` | a failed check in a run's check list |

Fonts: IBM Plex Sans for text, IBM Plex Mono for numbers, model IDs, check names and JSON. Load from Google Fonts in the shared CSS block.

Blue versus orange is deliberate. It stays readable for colour blind viewers. Do not swap to green and red.

## Top level

- App title "Weather Twin" with a small two circle mark.
- Two top tabs: **Today** and **Test Lab**.
- Test Lab has two sub views: **Official report** (public) and **Live comparison** (password, lock icon).

## Today tab (desktop and phone)

Locked state (until `APP_PASSWORD` is entered):
- Card titled "Enter your password". Text: "Today runs the live agent on Nebius Token Factory. The password keeps strangers from spending your credits."
- Password input and an "Unlock" button.
- Under the card: "Test Lab stays open to everyone. It only shows saved results."
- No model calls happen in this state.

Unlocked state. The page shows the two agents and the handoff between them, so a judge can see that Agent 2 reads only Agent 1's summary. Top to bottom on phone, left to right on desktop:
1. **Weather data card.** Label "Weather data · get_weather". The raw numbers from the tool: place ("Redmond, WA 98052"), date and time of day, big temperature (about 56 px), conditions, rain chance and wind in mono.
2. **Agent 1 card.** Title "Agent 1, Summarizer". Pills for its model and prompt version. Its summary is always shown as JSON in mono (no expander), with any value that differs from the tool highlighted. If numbers_match_tool fails, a small orange note on this card: "Agent 1 reported different numbers than the tool."
3. **Handoff arrow** between Agent 1 and Agent 2, labelled "handoff", with the line "Agent 2 reads only this summary". It points right on desktop and down on phone.
4. **Agent 2 card.** Title "Agent 2, Advisor". Pills for its model and prompt version. Two big answer tiles, Jacket and Umbrella, each Yes or No (a "Yes" tile is filled blue with white text, a "No" tile is white). A confidence pill, "Confident" or "Not confident". The why line.
5. **Footer line**, small and muted: tokens and latency for the whole run, "Cached · updated HH:MM", and a "Refresh" button.

Errors: a friendly card, for example "Couldn't reach the weather service. Try Refresh in a minute." Never a stack trace.

## Test Lab · Official report (public, no model calls)

Reads `results/matrix_summary.json` and `results/official_matrix_oct25.jsonl` only.

Intro line: "Official run, Oct 25. 132 runs: 11 scenarios × 2 models × 2 prompt versions × 3 repeats. Same agent code as Today, fake weather from the twin. Nothing here calls a model."

1. **Decision card.** Dark (`ink`) background. Label "DECISION". Title "Ship Nemotron 3 Ultra with prompt v2". Line on cost: about 400 more tokens per run than v1, median near 3.4 s. Three reason boxes:
   - "Held out injection resisted 3 of 3". Sub: written after v2 was frozen, gpt-oss obeyed it in 5 of 6 runs.
   - "Handoff clean in 12 of 12 injection runs". Sub: up from 3 of 12 with v1.
   - "Numbers matched the tool in 30 of 30 runs".
   - A disabled "Promote to Today · coming later" button (increment A).
2. **Results by check.** Rows are checks, each with its name in mono and a short plain description. Columns are Nemotron v1, Nemotron v2 (with a blue "Shipped" badge), gpt-oss v1, gpt-oss v2. Cells show "x of y" in mono and are coloured pass, partial or hard fail. The hard fail colour applies only to handoff_clean and numbers_match_tool. gpt-oss v2 handoff_clean is a pass cell with a dashed orange outline and the note "misleading alone". Legend above the table. Wrap the table in a horizontal scroll box on small screens.
3. **Look inside a run.** Three selects: Scenario (held out scenarios get a "held out" tag), Setup, Repeat. Default to injection_holdout, gpt-oss v2, a repeat where it obeyed. Then:
   - A one line callout explaining the run in plain words.
   - Three panels side by side, stacking on phones: "1 · Tool output (twin)", "2 · Agent 1 summary", "3 · Agent 2 advice". JSON in mono. Highlight the values that differ between panels.
   - The panel where the failure starts gets a 2 px hard fail border and the label "failure starts here". Work it out from the checks. If any Agent 1 check failed, it is panel 2. Otherwise panel 3.
   - "Checks for this run" as a grid of small boxes, failures first, each with the check name, Pass or Fail, and the detail string.
4. **Cost and speed.** Table of setup, average tokens and median latency. Footnote: "Median, not average. One Nemotron v2 call hung for 1,551 s during the official run. A 60 s timeout was added afterwards."
5. **"No prompt fixed this" card.** Heavy snow at 30 °C. Agent 1 flagged it in 0 of 3 runs in every column. Agent 2 caught it every time. "Next step: a plausibility rule in code, not a better prompt."

## Test Lab · Live comparison (password)

Intro: "Try a new setup against the one Today runs. Same agents, same scenarios, fresh runs. This spends Token Factory credits."

**Set up a comparison** card:
- A dark "Current · what Today runs" box showing the model and prompt from `config/active.yaml`.
- Up to three candidate boxes, each with a Model select (filled from Token Factory's model list) and a Prompt select (default v2).
- Under each candidate, a tool calling check result. Either "Real tool calls work" in blue with a tick, or "Unsupported · wrote the tool call as text. Skipped." in orange with a cross.
- An "Add candidate" dashed button, "up to 3".
- Scenario chips, all selected by default, and a Repeats select (default 3).
- A summary bar: "N runs · current and K candidates × S scenarios × R repeats · about T tokens" and a primary "Run comparison" button.
- A progress bar while running.

**Results** card, one per candidate:
- Title "Current versus <model> · <prompt>". Sub: "A cell passes only if every repeat passed." A "Past lab runs" select on the right.
- Four count tiles in this order: **Newly broken** (hard fail fill), **Fixed** (pass fill), **Still failing** (partial fill), **Still passing** (neutral).
- The Newly broken list is open, a table of scenario, check, current "x of 3", candidate "x of 3" and a "See the run" link that opens the run drill down.
- Fixed, Still failing and Still passing are collapsed expanders with counts.
- Cost and speed for current versus candidate.

## Desktop and phone

Every screen must work well on both. Test each one at desktop width (about 1280 px) and phone width (about 390 px).

| Screen | Desktop | Phone |
|---|---|---|
| Today | Locked card centred in a column about 480 px wide. Unlocked: weather, Agent 1, handoff arrow and Agent 2 side by side in one row, left to right, across the full content width. | Full width with 16 to 20 px side margins. The cards stack in the same order, with the handoff arrow pointing down. Answer tiles stay side by side. Refresh button easy to reach at the bottom. |
| Official report | Decision card text and reason boxes side by side. Results table fully visible. Run trace panels in three columns. Cost table and "No prompt fixed this" card side by side. | Decision card stacks, reasons under the title. Results table scrolls sideways inside its own box. Run trace panels stack in order 1, 2, 3. Cards stack. |
| Live comparison | Current and candidate boxes in one row. Count tiles in one row of four. | Current and candidate boxes stack. Count tiles in a two by two grid. Tables scroll sideways inside their own box. |

General rules for both:
- Max content width about 1200 px, centred.
- Card padding about 24 px on desktop, 16 px on phone. Gaps 12 to 24 px.
- No sideways scrolling of the whole page at any width. Only wide tables scroll, inside their own box.
- Touch targets at least 44 px tall.
- Text never smaller than 13 px.
