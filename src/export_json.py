"""
export_json.py — Export weather data to weather_data.json for GitHub Pages dashboard.
Run after chart.py generates cards.
"""

import json
import os
import sys
from datetime import datetime, timezone
try:
    import pytz
    _PT = pytz.timezone("America/Los_Angeles")
    def _now_pt():
        return datetime.now(_PT)
except ImportError:
    def _now_pt():
        return datetime.now(timezone.utc)

sys.path.insert(0, os.path.dirname(__file__))
from weather import get_weather_data

# Try to import forecast fetcher if available
try:
    from weather import get_forecast_data
    HAS_FORECAST = True
except ImportError:
    HAS_FORECAST = False


def export_weather_json(owm_key, report_period="morning", timestamp=""):
    print("Exporting weather data to JSON...")

    weather_data = get_weather_data(owm_key)

    forecast_data = {}
    if HAS_FORECAST:
        try:
            forecast_data = get_forecast_data(owm_key)
            print("  Forecast data included.")
        except Exception as e:
            print(f"  Forecast fetch failed (skipping): {e}")

    output = {
        "timestamp":     timestamp or _now_pt().strftime("%-I:%M %p PT · %b %-d, %Y"),
        "report_period": report_period,
        "generated_at":  datetime.now(timezone.utc).isoformat() + "Z",
        "stations":      weather_data,
        "forecast":      forecast_data,
    }

    with open("weather_data.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"  Saved weather_data.json ({len(weather_data)} stations)")
    return output


if __name__ == "__main__":
    owm_key       = os.environ.get("OPENWEATHER_API_KEY", "")
    report_period = os.environ.get("REPORT_PERIOD", "morning")
    timestamp     = os.environ.get("TIMESTAMP", "")

    if not owm_key:
        print("ERROR: OPENWEATHER_API_KEY not set")
        sys.exit(1)

    export_weather_json(owm_key, report_period, timestamp)
