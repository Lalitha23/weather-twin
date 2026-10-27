# Weather Twin

A test bench that catches agent failures before they spread from one agent to the next.

Weather Twin copies a small two agent workflow and swaps its live weather tool for a twin. It runs the same scenarios across NVIDIA Nemotron and a second model on Nebius Token Factory. Simple checks score every run. The results show which model broke, where, and whether the failure travelled to the next agent.

Built for the Nebius x NVIDIA Global AI Hackathon 2026.

## Live demo
The app has two tabs.
- **Today** shows the agents' run for Redmond, WA. It is a cached run: the agents run once a day and the result is saved, so the page stays open to everyone without the Token Factory credits being misused. Refreshing it early is password protected.
- **Test Lab** shows the saved official results and is open to everyone. The live comparison inside it is password protected.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then add your NEBIUS_API_KEY
python scripts/list_models.py    # pick model IDs, add them to .env
python scripts/hello_nemotron.py # smoke test
```

## License
MIT
