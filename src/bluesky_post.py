import os
import sys
import time
import requests
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from weather import get_weather_data

BSKY_API = "https://bsky.social/xrpc"

STATION_HASHTAGS = {
    "Lakewood":     "#Lakewood #LakewoodWA #Tacoma #PNW #PNWwx #WAwx #SeattleWx #wxtwitter",
    "Groveland":    "#Groveland #TuolumneCounty #SierraNevada #Yosemite #CAwx #NorCalWx #wxtwitter",
    "Death Valley": "#DeathValley #DeathValleyNP #MojaveDesert #CAwx #SoCalWx #DesertWx #wxtwitter",
    "Reno":         "#Reno #RenoNV #TahoeWx #NVwx #GreatBasin #HighDesert #wxtwitter",
}
LEAD_HASHTAGS = (
    "#Weather #WestCoast #WAwx #CAwx #NVwx #PNW #PNWwx "
    "#wxtwitter #DailyWeather #WeatherReport #ClimateWatch"
)
STATION_ORDER = ["Lakewood", "Groveland", "Death Valley", "Reno"]


def _build_station_caption(loc, timestamp):
    """Per-station post — condensed format fits within 300 chars with full hashtags."""
    name  = loc["name"]
    htags = STATION_HASHTAGS.get(name, "")
    lines = [
        f"{name}, {loc['state']}  |  {timestamp}",
        f"Temp: {loc['temp']}F  Feels {loc['feels_like']}F  H {loc['temp_high']}  L {loc['temp_low']}",
        f"Humidity: {loc['humidity']}%  Precip: {loc['pop']}%  Wind: {loc['wind_speed']} mph {loc.get('wind_dir','')}",
        f"UV: {loc['uv_index']}  Clouds: {loc['cloud_cover']}%  Vis: {loc['visibility']} mi",
        f"Sunrise: {loc['sunrise'].lstrip('0')}  Sunset: {loc['sunset'].lstrip('0')}",
        "",
        htags,
    ]
    return "\n".join(lines)


# ── BlueSky API helpers ───────────────────────────────────────────────────────
def _create_session(handle, password):
    resp = requests.post(
        f"{BSKY_API}/com.atproto.server.createSession",
        json={"identifier": handle, "password": password},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _upload_image(session, image_path):
    with open(image_path, "rb") as f:
        data = f.read()
    resp = requests.post(
        f"{BSKY_API}/com.atproto.repo.uploadBlob",
        headers={
            "Authorization": f"Bearer {session['accessJwt']}",
            "Content-Type":  "image/png",
        },
        data=data,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["blob"]


def _post_record(session, text, blob, alt_text, reply_ref=None):
    record = {
        "$type":     "app.bsky.feed.post",
        "text":      text,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "embed": {
            "$type":  "app.bsky.embed.images",
            "images": [{"image": blob, "alt": alt_text}],
        },
    }
    if reply_ref:
        record["reply"] = {
            "root":   reply_ref["root"],
            "parent": reply_ref["parent"],
        }
    resp = requests.post(
        f"{BSKY_API}/com.atproto.repo.createRecord",
        headers={
            "Authorization": f"Bearer {session['accessJwt']}",
            "Content-Type":  "application/json",
        },
        json={
            "repo":       session["did"],
            "collection": "app.bsky.feed.post",
            "record":     record,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"uri": data["uri"], "cid": data["cid"]}


# ── Main ──────────────────────────────────────────────────────────────────────
def post_to_bluesky():
    handle        = os.environ["BLUESKY_HANDLE"]
    password      = os.environ["BLUESKY_APP_PASSWORD"]
    timestamp     = os.environ.get("TIMESTAMP", "")

    owm_key = os.environ.get("OPENWEATHER_API_KEY")
    if not owm_key:
        print("ERROR: OPENWEATHER_API_KEY not set"); sys.exit(1)

    print("Fetching weather data...")
    weather_data = get_weather_data(owm_key)
    loc_by_name  = {loc["name"]: loc for loc in weather_data}

    print("Authenticating with BlueSky...")
    session = _create_session(handle, password)

    # ── Lead post: combined 2×2 K5 card ──────────────────────────────────────
    lead_text = (
        f"West Coast Weather Report\n"
        f"Lakewood WA · Groveland CA · Death Valley CA · Reno NV\n"
        f"{timestamp}\n\n"
        f"Full conditions at each station below 👇\n\n"
        f"{LEAD_HASHTAGS}"
    )
    combined_img = "weather_report_k5.png" if os.path.exists("weather_report_k5.png") else "weather_report.png"

    print("Uploading combined card...")
    blob = _upload_image(session, combined_img)
    print("Posting lead...")
    lead = _post_record(session, lead_text, blob,
                        alt_text="West Coast weather — 4 stations")
    print(f"  Lead posted — URI: {lead['uri']}")

    root_ref   = {"uri": lead["uri"], "cid": lead["cid"]}
    parent_ref = root_ref

    # ── Station thread replies ────────────────────────────────────────────────
    for name in STATION_ORDER:
        loc = loc_by_name.get(name)
        if not loc:
            print(f"  Skipping {name} — no data"); continue

        slug      = name.lower().replace(" ", "_")
        card_path = f"weather_{slug}_k5.png"
        if not os.path.exists(card_path):
            print(f"  K5 card not found for {name}, using combined"); card_path = combined_img

        caption  = _build_station_caption(loc, timestamp)
        alt_text = (f"{name}, {loc['state']} — {loc['temp']}°F "
                    f"{loc.get('description','')} H:{loc['temp_high']} L:{loc['temp_low']}")

        print(f"  Waiting 10s before {name}...")
        time.sleep(10)  # BlueSky has no paid-tier delay requirement

        print(f"  Posting {name}...")
        blob  = _upload_image(session, card_path)
        reply = _post_record(session, caption, blob, alt_text,
                             reply_ref={"root": root_ref, "parent": parent_ref})
        parent_ref = {"uri": reply["uri"], "cid": reply["cid"]}
        print(f"    {name} posted — URI: {reply['uri']}")

    print("BlueSky thread complete.")


if __name__ == "__main__":
    post_to_bluesky()
