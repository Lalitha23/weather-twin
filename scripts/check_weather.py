"""Print what get_weather returns for Redmond.

Run:  python scripts/check_weather.py          tool output via WEATHER_BACKEND
      python scripts/check_weather.py --raw    raw Open-Meteo JSON only
      python scripts/check_weather.py --raw > scenarios/live_sample.json
"""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.weather_live import fetch_raw  # noqa: E402
from tools.weather_tool import get_weather  # noqa: E402

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--raw", action="store_true", help="print only the raw Open-Meteo JSON")
args = parser.parse_args()

if args.raw:
    print(json.dumps(fetch_raw(), indent=2))
else:
    print(json.dumps(get_weather(), indent=2))
