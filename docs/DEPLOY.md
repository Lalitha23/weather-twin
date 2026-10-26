# Deploying to Streamlit Community Cloud

The repo is ready: `requirements.txt` is pinned, `.streamlit/config.toml` sets the theme, and the
app starts with no secrets at all. Without secrets, Today stays locked and the Official report
still works, because it only reads committed files in `results/`.

## 1. Before you start

- The latest code is pushed to `master` on GitHub (`Lalitha23/weather-twin`).
- Have these values ready. They are the same as in your local `.env`:
  `NEBIUS_API_KEY`, `NEMOTRON_MODEL`, `COMPARE_MODEL`, `APP_PASSWORD`.
  `NEBIUS_BASE_URL` is optional; leave it empty to use the default.

## 2. Connect the repo

1. Go to https://share.streamlit.io and sign in with GitHub.
2. If asked, authorize Streamlit to read your repositories.
3. Click **Create app**, then choose **Deploy a public app from GitHub**.

## 3. Fill in the deploy form

| Field | Value |
|---|---|
| Repository | `Lalitha23/weather-twin` |
| Branch | `master` |
| Main file path | `app/streamlit_app.py` |
| App URL | pick a short name, for example `weather-twin` |

## 4. Advanced settings (before you click Deploy)

1. Open **Advanced settings**.
2. **Python version:** choose **3.13**. The pinned requirements and all tests were checked on 3.13.
3. **Secrets:** open `.streamlit/secrets.example.toml` in the repo, copy all of it into the
   Secrets box, and fill in the values between the quotes:

   ```toml
   NEBIUS_API_KEY = "your key"
   NEBIUS_BASE_URL = ""
   NEMOTRON_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"
   COMPARE_MODEL = "openai/gpt-oss-120b"
   APP_PASSWORD = "pick a password"
   ```

   Empty values are ignored, so the empty base URL falls back to the default.
4. Click **Save**, then **Deploy**. The first build takes a few minutes.

## 5. Check it once it's live

Open the app URL on a laptop and on your phone.

**Without the password (what judges see first)**
- [ ] Today shows the "Enter your password" card and nothing else.
- [ ] A wrong password says "That password didn't work." and stays locked.
- [ ] Test Lab › Official report shows the dark decision card "Ship Nemotron 3 Ultra with prompt v2",
      the results table (Nemotron v1 handoff_clean "3 of 12", Nemotron v2 "12 of 12"),
      and the gpt-oss v2 "misleading alone" cell.
- [ ] "Look inside a run" opens on injection_holdout, gpt-oss v2, with panel 2 marked
      "failure starts here".
- [ ] Test Lab › Live comparison shows the password card.
- [ ] On the phone, nothing scrolls sideways except the results table inside its own box.

**With the password**
- [ ] Today shows "Redmond, WA 98052", the temperature, Jacket and Umbrella tiles, and a Why card.
      The footer shows the Nemotron model, prompt v2, tokens and "Cached · updated HH:MM".
- [ ] Refresh runs it again (this spends a few thousand tokens).
- [ ] Live comparison shows Current (Nemotron 3 Ultra, v2) and Candidate 1 with
      "✓ Real tool calls work".
- [ ] Optional small run: keep only `snow` and `injection_holdout`, Repeats 1, then Run comparison.
      It is 4 runs, about 8,000 tokens. Results appear with Download results.

If something is wrong, open **Manage app** (bottom right of the app) to see the logs.

| Symptom | Likely cause |
|---|---|
| "Couldn't reach the model on Token Factory" on Today | `NEBIUS_API_KEY` or `NEMOTRON_MODEL` missing or wrong in Secrets |
| Password never works | `APP_PASSWORD` missing or empty in Secrets |
| `ModuleNotFoundError` in the logs | a package missing from `requirements.txt` |
| Live comparison: "Couldn't load the model list" | API key problem, or Token Factory is down |

## 6. After it's live

- **Updates:** every push to `master` redeploys the app on its own.
- **Changing secrets:** app menu › **Settings** › **Secrets**. Saving restarts the app.
- **Lab runs vanish** when the app restarts or redeploys. Use Download results to keep one.
  The Official report never changes, because it comes from committed files.
- **Sleeping apps:** Community Cloud puts apps to sleep after a period without visitors. Open the URL
  yourself shortly before judging so it is awake, and click "Yes, get this app back up" if asked.
- **After the hackathon:** change `APP_PASSWORD`, or remove the API key from Secrets, so nobody can
  keep spending your Token Factory credits.
