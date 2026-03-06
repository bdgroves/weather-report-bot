import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from weather import get_weather_data
from chart import create_weather_chart


def main():
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        print("ERROR: OPENWEATHER_API_KEY not set")
        sys.exit(1)

    report_period = os.environ.get("REPORT_PERIOD", "morning")
    timestamp = os.environ.get("TIMESTAMP", "")

    print(f"Fetching weather data - {report_period} report")
    weather_data = get_weather_data(api_key)
    print(f"Got data for {len(weather_data)} locations")

    print("Generating chart...")
    create_weather_chart(
        weather_data=weather_data,
        report_period=report_period,
        timestamp=timestamp,
        output_path="weather_report.png",
    )
    print("Done!")


if __name__ == "__main__":
    main()