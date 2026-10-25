"""List the models your Nebius Token Factory account can use.

Run:  python scripts/list_models.py
Copy the Nemotron ID you want into .env as NEMOTRON_MODEL,
and a second model (e.g. a Llama or Qwen) as COMPARE_MODEL.
"""
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
API_KEY = os.getenv("NEBIUS_API_KEY")

if not API_KEY:
    sys.exit("NEBIUS_API_KEY is missing. Copy .env.example to .env and fill it in.")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
ids = sorted(m.id for m in client.models.list().data)

print(f"{len(ids)} models available\n")

groups = {
    "NVIDIA / Nemotron": lambda i: "nemotron" in i.lower() or i.lower().startswith("nvidia"),
    "Llama": lambda i: "llama" in i.lower(),
    "Qwen": lambda i: "qwen" in i.lower(),
}
shown = set()
for label, match in groups.items():
    hits = [i for i in ids if match(i)]
    if hits:
        print(f"== {label} ==")
        for i in hits:
            print("  ", i)
            shown.add(i)
        print()

print("== Everything else ==")
for i in ids:
    if i not in shown:
        print("  ", i)
