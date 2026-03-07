import os
import sys
import time
import tweepy

sys.path.insert(0, os.path.dirname(__file__))
from weather import get_weather_data
from chart import _uv_info

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
    if len(text) > 260:
        text = text[:257] + "..."
    return text

def post_to_twitter():
    api_key       = os.environ["TWITTER_API_KEY"]
    api_secret    = os.environ["TWITTER_API_SECRET"]
    access_token  = os.environ["TWITTER_ACCESS_TOKEN"]
    access_secret = os.environ["TWITTER_ACCESS_SECRET"]
    report_period = os.environ.get("REPORT_PERIOD", "morning")
    timestamp     = os.environ.get("TIMESTAMP", "")
    owm_key       = os.environ.get("OPENWEATHER_API_KEY", "")
    period        = "Morning" if report_period == "morning" else "Evening"

    if not owm_key:
        print("ERROR: OPENWEATHER_API_KEY not set")
        return

    print("Fetching weather data...")
    weather_data = get_weather_data(owm_key)

    auth = tweepy.OAuthHandler(api_key, api_secret)
    auth.set_access_token(access_token, access_secret)
    api_v1 = tweepy.API(auth)
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    lead_id = None
    if os.path.exists("weather_report.png"):
        lead_text = (
            f"{period} Weather Report  |  {timestamp}\n"
            f"Lakewood WA  ·  Groveland CA  ·  Death Valley CA  ·  Reno NV\n\n"
            f"#WAwx #CAwx #NVwx #PNWwx #PNW #wxtwitter #DailyWeather #WeatherReport"
        )
        print("Posting combined card (lead tweet)...")
        print(f"  File exists: {os.path.exists(chr(39)weather_report.png{chr(39)}}")
        print(f"  File size: {os.path.getsize(chr(39)weather_report.png{chr(39)}) if os.path.exists(chr(39)weather_report.png{chr(39)}) else 0} bytes")
        media   = api_v1.media_upload("weather_report.png")
        resp    = client.create_tweet(text=lead_text, media_ids=[media.media_id])
        lead_id = resp.data["id"]
        print(f"  Lead tweet ID: {lead_id}")
        time.sleep(90)

    for loc in weather_data:
        slug     = loc["name"].lower().replace(" ", "_")
        img_path = f"weather_{slug}.png"
        if not os.path.exists(img_path):
            continue
        text = build_station_text(loc, period, timestamp)
        print(f"Posting {loc['name']}... ({len(text)} chars)")
        media  = api_v1.media_upload(img_path)
        kwargs = dict(text=text, media_ids=[media.media_id])
        if lead_id:
            kwargs["in_reply_to_tweet_id"] = lead_id
        resp = client.create_tweet(**kwargs)
        print(f"  Posted: {resp.data['id']}")
        time.sleep(90)

if __name__ == "__main__":
    post_to_twitter()


