import os
import sys
import requests
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from weather import get_weather_data
from chart import build_post_text

BSKY_API = "https://bsky.social/xrpc"


def create_session(handle, password):
    resp = requests.post(
        f"{BSKY_API}/com.atproto.server.createSession",
        json={"identifier": handle, "password": password},
    )
    resp.raise_for_status()
    return resp.json()


def upload_image(session, image_path):
    with open(image_path, "rb") as f:
        image_data = f.read()
    resp = requests.post(
        f"{BSKY_API}/com.atproto.repo.uploadBlob",
        headers={
            "Authorization": f"Bearer {session['accessJwt']}",
            "Content-Type": "image/png",
        },
        data=image_data,
    )
    resp.raise_for_status()
    return resp.json()["blob"]


def post_to_bluesky():
    handle        = os.environ["BLUESKY_HANDLE"]
    password      = os.environ["BLUESKY_APP_PASSWORD"]
    report_period = os.environ.get("REPORT_PERIOD", "morning")
    timestamp     = os.environ.get("TIMESTAMP", "")
    owm_key       = os.environ.get("OPENWEATHER_API_KEY", "")

    # Build rich post text from live data if available, else fallback
    if owm_key:
        print("Fetching weather data for post text...")
        try:
            weather_data = get_weather_data(owm_key)
            post_text = build_post_text(weather_data, report_period, timestamp)
        except Exception as e:
            print(f"  Could not fetch live data for text: {e}")
            post_text = _fallback_text(report_period, timestamp)
    else:
        post_text = _fallback_text(report_period, timestamp)

    # BlueSky has a 300 grapheme limit
    if len(post_text) > 300:
        post_text = post_text[:297] + "..."

    period = "Morning" if report_period == "morning" else "Evening"

    print("Authenticating with BlueSky...")
    session = create_session(handle, password)

    print("Uploading image to BlueSky...")
    blob = upload_image(session, "weather_report.png")

    print("Posting to BlueSky...")
    post_record = {
        "$type": "app.bsky.feed.post",
        "text": post_text,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "embed": {
            "$type": "app.bsky.embed.images",
            "images": [
                {
                    "image": blob,
                    "alt": (
                        f"{period} weather report for "
                        f"Lakewood WA, Groveland CA, Death Valley CA, Reno NV"
                    ),
                }
            ],
        },
    }

    resp = requests.post(
        f"{BSKY_API}/com.atproto.repo.createRecord",
        headers={
            "Authorization": f"Bearer {session['accessJwt']}",
            "Content-Type": "application/json",
        },
        json={
            "repo": session["did"],
            "collection": "app.bsky.feed.post",
            "record": post_record,
        },
    )
    resp.raise_for_status()
    print(f"BlueSky post created! URI: {resp.json().get('uri')}")


def _fallback_text(report_period, timestamp):
    period = "Morning" if report_period == "morning" else "Evening"
    return (
        f"{period} Weather Report  |  {timestamp}\n"
        f"Lakewood WA  |  Groveland CA  |  Death Valley CA  |  Reno NV\n\n"
        f"#Weather #Lakewood #DeathValley #Reno #GrovelandCA #PNW #DailyWeather"
    )


if __name__ == "__main__":
    post_to_bluesky()
