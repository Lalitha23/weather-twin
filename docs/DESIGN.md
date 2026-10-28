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
- Under it, a public two line intro on every tab: the son's morning message story (texting is "later", not built), then in bold "New here? Open Test Lab → Official report to see what I found."
- Two top tabs: **Today** and **Test Lab**. Today stays first. Test Lab is filled first in code, so a slow Today run can't leave the report blank.
- Test Lab has two sub views: **Official report** (public) and **Live comparison** (password, lock icon).

## Today tab (desktop and phone)

Today is public. The agents run once per Pacific day (the first visit of the day), and everyone after that sees the cached run. Only Refresh needs `APP_PASSWORD`.

The page shows the two agents and the handoff between them, so a judge can see that Agent 2 reads only Agent 1's summary. Top to bottom on phone, left to right on desktop:
1. **Weather data card.** Label "Weather data · get_weather". The raw numbers from the tool: place ("Redmond, WA 98052"), date and time of day, big temperature (about 56 px), conditions, rain chance and wind in mono.
2. **Agent 1 card.** Title "Agent 1, Summarizer". Pills for its model and prompt version. Its summary is always shown as JSON in mono (no expander), with any value that differs from the tool highlighted. If numbers_match_tool fails, a small orange note on this card: "Agent 1 reported different numbers than the tool."
3. **Handoff arrow** between Agent 1 and Agent 2, labelled "handoff", with the line "Agent 2 reads only this summary". It points right on desktop and down on phone.
4. **Agent 2 card.** Title "Agent 2, Advisor". Pills for its model and prompt version. Two big answer tiles, Jacket and Umbrella, each Yes or No (a "Yes" tile is filled blue with white text, a "No" tile is white). A confidence pill, "Confident" or "Not confident". The why line.
5. **Footer line**, small and muted: tokens and latency for the whole run, "Cached run · updated Mon Oct 26, 07:05 PT", then the note "This is a cached run. Today runs the agents once a day and saves the result, so the page stays open to everyone without the credits being misused. Refresh is password protected."
6. **Refresh.** Without the password: a collapsed "Refresh (password)" section holding the password card ("Refresh runs the live agent again on Nebius Token Factory. The password keeps strangers from spending your credits."). With it: a "Refresh" button. One unlock covers Refresh and the live comparison.

Errors: a friendly card, for example "Couldn't reach the weather service. Try again in a minute." Never a stack trace.

## Test Lab · Official report (public, no model calls)

Reads `results/matrix_summary.json` and `results/official_matrix_oct25.jsonl` only.

Intro line: "Official run, Oct 25. 132 runs: 11 scenarios × 2 models × 2 prompt versions × 3 repeats. Same agent code as Today, fake weather from the twin. Nothing here calls a model."

0. **"What I found" card.** Plain words, numbers read from the results: the fake units note, Nemotron v1 changing 60% rain to 40%, Agent 2 confidently saying no umbrella in 3 of 3, Nemotron v2 blocking it in 3 of 3, "In a later lab run it still repeated the hidden note, so v2 is better, not perfect.", and gpt-oss v2's clean-looking summary still changing the number in 2 of 3 runs.
1. **Decision card.** Dark (`ink`) background. Label "DECISION". Title "Ship Nemotron 3 Ultra with prompt v2". Line on cost: about 400 more tokens per run than v1, median near 3.4 s. A trade-off line: "Nemotron's Agent 1 flagged missing or contradictory data in 0 of 6 runs (gpt-oss: 3 and 2 of 6). Agent 2 still lowered its confidence every time." Three reason boxes:
   - "Held out injection resisted 3 of 3". Sub: committed after v2, neither has changed since, gpt-oss obeyed it in 5 of 6 runs.
   - "Handoff clean in 12 of 12 injection runs". Sub: up from 3 of 12 with v1.
   - "Numbers matched the tool in 30 of 30 runs".
   - A disabled "Promote to Today · coming later" button (increment A).
2. **Results by check.** Rows are checks, each with its name in mono and a short plain description. Columns are Nemotron v1, Nemotron v2 (with a blue "Shipped" badge), gpt-oss v1, gpt-oss v2. Cells show "x of y" in mono and are coloured pass, partial or hard fail. The hard fail colour applies only to handoff_clean and numbers_match_tool. gpt-oss v2 handoff_clean is a pass cell with a dashed orange outline and the note "text clean, numbers changed". Legend above the table. Under it: "v1 = plain prompt, v2 = hardened prompt", why totals differ, and why eight checks show as nine rows. Wrap the table in a horizontal scroll box on small screens.
3. **Look inside a run.** Three selects: Scenario (held out scenarios get a "held out" tag), Setup, Repeat. Default to injection_holdout, gpt-oss v2, a repeat where it obeyed. Then:
   - A one line callout explaining the run in plain words, built from the run's data, e.g. "Agent 1 changed the rain chance from 60% to 40%, and Agent 2 did what the hidden note wanted: no umbrella."
   - Three panels side by side, stacking on phones: "1 · Tool output (twin)", "2 · Agent 1 summary", "3 · Agent 2 advice". JSON in mono. Highlight the values that differ between panels.
   - The panel where the failure starts gets a 2 px hard fail border and the label "failure starts here". Work it out from the checks. If any Agent 1 check failed, it is panel 2. Otherwise panel 3.
   - "Checks for this run" as a grid of small boxes, failures first, each with the check name, Pass or Fail, and the detail string.
4. **Cost and speed.** Table of setup, average tokens and median latency. Footnote: "Median, not average. One Nemotron v2 call hung for 1,551 s during the official run. A 60 s timeout was added afterwards."
5. **"No prompt fixed this" card.** Heavy snow at 30 °C. Agent 1 flagged it in 0 of 3 runs in every column. Agent 2 lowered its confidence every time. "Next step: a plausibility rule in code, not a better prompt."

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

## Delivery (not built yet)

Handoff chain: weather → Agent 1 → Agent 2 → **His phone or room speaker, later**.

**Delivery, not built yet.** Once the Test Lab passes it, the advice will reach my son each morning while he gets
ready. That will be either a text to his phone or a voice message broadcast to his room through Alexa or Google Home.
Voice is the likely choice, because he can't miss it.

**Why not just use Alexa or Google?** A smart speaker can already read the forecast aloud on a schedule. What it
can't do is turn 11 °C and 18% rain into no jacket and no umbrella for my son. That decision is made by the two
agents, and the Test Lab checks it before anything reaches his room.

## Desktop and phone

Every screen must work well on both. Test each one at desktop width (about 1280 px) and phone width (about 390 px).

| Screen | Desktop | Phone |
|---|---|---|
| Today | See `docs/REDESIGN.md`. Live sky behind the page. Answer card on top, X-ray layers unfolded in one column under it. | See `docs/REDESIGN.md`. Same order, full width with 16 to 20 px side margins. X-ray folded by default. Refresh easy to reach at the bottom. |
| Official report | See `docs/REDESIGN.md`. Hero, then the Handoff Inspector with the inspector and side panel side by side. Decision card text and reason boxes side by side. Results table fully visible. Cost table and "No prompt fixed this" card side by side. | See `docs/REDESIGN.md`. Inspector nodes wrap two by two, inspector and side panel stack. Decision card stacks. Results table scrolls sideways inside its own box. Cards stack. |
| Live comparison | Current and candidate boxes in one row. Count tiles in one row of four. | Current and candidate boxes stack. Count tiles in a two by two grid. Tables scroll sideways inside their own box. |

General rules for both:
- Max content width about 1200 px, centred.
- Card padding about 24 px on desktop, 16 px on phone. Gaps 12 to 24 px.
- No sideways scrolling of the whole page at any width. Only wide tables scroll, inside their own box.
- Touch targets at least 44 px tall.
- Text never smaller than 13 px.
