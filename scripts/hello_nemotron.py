"""Saturday smoke test. Two checks against Nebius Token Factory.

1. A plain chat call works.
2. Tool calling works (the whole project depends on this,
   because Agent 1 calls get_weather as a tool).

Run:  python scripts/hello_nemotron.py
      python scripts/hello_nemotron.py --model <other-model-id>
"""
import argparse
import json
import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--model", default=os.getenv("NEMOTRON_MODEL"))
args = parser.parse_args()

if not os.getenv("NEBIUS_API_KEY"):
    sys.exit("NEBIUS_API_KEY is missing. Copy .env.example to .env and fill it in.")
if not args.model:
    sys.exit("No model set. Run scripts/list_models.py and put an ID in .env as NEMOTRON_MODEL.")

client = OpenAI(
    base_url=os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
    api_key=os.getenv("NEBIUS_API_KEY"),
)
print(f"Model: {args.model}\n")

# ---- Check 1: plain chat -------------------------------------------------
t = time.time()
resp = client.chat.completions.create(
    model=args.model,
    messages=[{"role": "user", "content": "Reply with exactly: hello from Token Factory"}],
    max_tokens=50,
    temperature=0,
)
print(f"[1] Plain chat ({time.time() - t:.1f}s): {resp.choices[0].message.content!r}")

# ---- Check 2: tool calling -----------------------------------------------
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a location.",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
            },
            "required": ["latitude", "longitude"],
        },
    },
}]

t = time.time()
resp = client.chat.completions.create(
    model=args.model,
    messages=[
        {"role": "system", "content": "You are a weather assistant. Always use the get_weather tool."},
        {"role": "user", "content": "What's the weather in Redmond, WA (47.674, -122.121)?"},
    ],
    tools=tools,
    tool_choice="auto",
    max_tokens=300,
    temperature=0,
)
msg = resp.choices[0].message
if msg.tool_calls:
    call = msg.tool_calls[0]
    print(f"[2] Tool call OK ({time.time() - t:.1f}s): {call.function.name}({call.function.arguments})")
    try:
        json.loads(call.function.arguments)
    except json.JSONDecodeError:
        print("    WARNING: tool arguments are not valid JSON. Note this for the comparison.")
else:
    print(f"[2] NO tool call. Model replied with text instead: {msg.content!r}")
    print("    This model may not support tool calling here. Try another Nemotron ID.")

print("\nUsage:", resp.usage)
