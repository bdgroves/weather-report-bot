import os
import sys
import time
import requests
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from weather import get_weather_data
from chart import _uv_info

BSKY_API = "https://bsky.social/xrpc"

STATION_HASHTAGS = {
    "Lakewood":     "#Lakewood #LakewoodWA #WAwx #PNWwx #PNW #Tacoma #wxtwitter",
    "Groveland":    "#Groveland #GrovelandCA #CAwx #SierraNevada #Yosemite #wxtwitter",
    "Death Valley": "#DeathValley #DeathValleyNP #CAwx #MojaveDesert #wxtwitter",
    "Reno":         "#Reno #RenoNV #NVwx #GreatBasin #HighDesert #wxtwitter",
}

STATION_LABELS = {
    "Lakewood":     "HOME BASE",
    "Groveland":    "SIERRA FOOTHILLS",
    "Death Valley": "EXTREME CONDITIONS",
    "Reno":         "BIGGEST LITTLE CITY",
}

def _icon(desc):
    d = desc.lower()
    if any(w in d for w in ("thunder", "storm")):           return "⛈"
    if any(w in d for w in ("rain", "drizzle", "shower")):  return "🌧"
    if any(w in d for w in ("snow", "sleet")):              return "❄️"
    if any(w in d for w in ("fog", "mist", "haze")):        return "🌫"
    if any(w in d for w in ("overcast", "broken")):         return "☁️"
    if any(w in d for w in ("scattered", "few", "partly")): return "⛅"
    if any(w in d for w in ("clear", "sunny")):             return "☀️"
    return "🌤"

def build_station_text(loc, period, timestamp):
    _, uvlbl = _uv_info(loc["uv_index"])
    label    = STATION_LABELS.get(loc["name"], loc["name"].upper())
    ic       = _icon(loc["description"])
    tags     = STATION_HASHTAGS.get(loc["name"], "")
    lines = [
        f"{ic} {loc['name']}, {loc['state']} — {label}",
        f"{period} Report | {timestamp}",
        f"🌡 {loc['temp']}°F (Feels {loc['feels_like']}°F)  H {loc['temp_high']}° L {loc['temp_low']}°",
        f"💧 {loc['humidity']}%  ☔ {loc['pop']}%  💨 {loc['wind_speed']} mph {loc['wind_dir']}",
        f"🌞 UV {loc['uv_index']} {uvlbl}  ☁️ {loc['cloud_cover']}%  👁 {loc['visibility']} mi",
        f"🌅 {loc['sunrise']}  🌇 {loc['sunset']}  📊 {loc['pressure']} hPa",
        "",
        tags,
        "#DailyWeather #WeatherReport",
    ]
    text = "\n".join(lines)
    if len(text) > 300:
        text = text[:297] + "..."
    return text

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

def create_post(session, text, blob, alt_text, reply_ref=None):
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "embed": {
            "$type": "app.bsky.embed.images",
            "images": [{"image": blob, "alt": alt_text}],
        },
    }
    if reply_ref:
        record["reply"] = reply_ref
    resp = requests.post(
        f"{BSKY_API}/com.atproto.repo.createRecord",
        headers={
            "Authorization": f"Bearer {session['accessJwt']}",
            "Content-Type": "application/json",
        },
        json={"repo": session["did"], "collection": "app.bsky.feed.post", "record": record},
    )
    resp.raise_for_status()
    return resp.json()

def post_to_bluesky():
    handle        = os.environ["BLUESKY_HANDLE"]
    password      = os.environ["BLUESKY_APP_PASSWORD"]
    report_period = os.environ.get("REPORT_PERIOD", "morning")
    timestamp     = os.environ.get("TIMESTAMP", "")
    owm_key       = os.environ.get("OPENWEATHER_API_KEY", "")
    period        = "Morning" if report_period == "morning" else "Evening"

    if not owm_key:
        print("ERROR: OPENWEATHER_API_KEY not set")
        return

    print("Fetching weather data...")
    weather_data = get_weather_data(owm_key)

    print("Authenticating with BlueSky...")
    session = create_session(handle, password)

    lead_ref = None
    if os.path.exists("weather_report.png"):
        lead_text = (
            f"{period} Weather Report  |  {timestamp}\n"
            f"Lakewood WA  ·  Groveland CA  ·  Death Valley CA  ·  Reno NV\n\n"
            f"#WAwx #CAwx #NVwx #PNWwx #PNW #wxtwitter #DailyWeather #WeatherReport"
        )
        print("Posting combined card (lead)...")
        blob   = upload_image(session, "weather_report.png")
        result = create_post(session, lead_text, blob, "Daily weather report — all 4 stations")
        lead_ref = {
            "root":   {"uri": result["uri"], "cid": result["cid"]},
            "parent": {"uri": result["uri"], "cid": result["cid"]},
        }
        print(f"  Lead post: {result['uri']}")
        time.sleep(90)

    for loc in weather_data:
        slug     = loc["name"].lower().replace(" ", "_")
        img_path = f"weather_{slug}.png"
        if not os.path.exists(img_path):
            continue
        text = build_station_text(loc, period, timestamp)
        alt  = f"{loc['name']}, {loc['state']} — {loc['temp']}°F {loc['description']}"
        print(f"Posting {loc['name']}... ({len(text)} chars)")
        blob   = upload_image(session, img_path)
        result = create_post(session, text, blob, alt, reply_ref=lead_ref)
        if lead_ref:
            lead_ref["parent"] = {"uri": result["uri"], "cid": result["cid"]}
        print(f"  Posted: {result['uri']}")
        time.sleep(90)

if __name__ == "__main__":
    post_to_bluesky()
