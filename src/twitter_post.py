import os
import sys
import time
import tweepy

sys.path.insert(0, os.path.dirname(__file__))
from weather import get_weather_data

STATION_HASHTAGS = {
    "Lakewood":     "#Lakewood #LakewoodWA #WAwx #PNWwx #PNW #Tacoma #wxtwitter",
    "Groveland":    "#Groveland #GrovelandCA #CAwx #SierraNevada #Yosemite #wxtwitter",
    "Death Valley": "#DeathValley #DeathValleyNP #CAwx #MojaveDesert #wxtwitter",
    "Reno":         "#Reno #RenoNV #NVwx #GreatBasin #HighDesert #wxtwitter",
}
LEAD_HASHTAGS = "#Weather #WestCoast #wxtwitter #DailyWeather #WeatherReport"
STATION_ORDER = ["Lakewood", "Groveland", "Death Valley", "Reno"]


def _build_station_caption(loc, period_text, timestamp):
    name     = loc["name"]
    htags    = STATION_HASHTAGS.get(name, "")
    lines = [
        f"{loc.get('emoji','')} {name}, {loc['state']}",
        f"{period_text} Report | {timestamp}",
        f"Temp: {loc['temp']}F (Feels {loc['feels_like']}F) H {loc['temp_high']} L {loc['temp_low']}",
        f"Humidity: {loc['humidity']}% Precip: {loc['pop']}% Wind: {loc['wind_speed']} mph {loc.get('wind_dir','')}",
        f"UV: {loc['uv_index']} Clouds: {loc['cloud_cover']}% Vis: {loc['visibility']} mi",
        f"Sunrise: {loc['sunrise'].lstrip('0')} Sunset: {loc['sunset'].lstrip('0')}",
        "",
        htags,
        "#DailyWeather #WeatherReport",
    ]
    text = "\n".join(lines)
    if len(text) > 270:
        lines[-2] = ""
        text = "\n".join(lines)
    return text


def post_to_twitter():
    api_key       = os.environ["TWITTER_API_KEY"]
    api_secret    = os.environ["TWITTER_API_SECRET"]
    access_token  = os.environ["TWITTER_ACCESS_TOKEN"]
    access_secret = os.environ["TWITTER_ACCESS_SECRET"]
    report_period = os.environ.get("REPORT_PERIOD", "morning")
    timestamp     = os.environ.get("TIMESTAMP", "")
    period_text   = "Morning" if report_period == "morning" else "Evening"

    # v1 for media upload, v2 client for tweets
    auth = tweepy.OAuthHandler(api_key, api_secret)
    auth.set_access_token(access_token, access_secret)
    api_v1 = tweepy.API(auth)

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    # Fetch live weather
    owm_key = os.environ.get("OPENWEATHER_API_KEY")
    if not owm_key:
        print("ERROR: OPENWEATHER_API_KEY not set"); sys.exit(1)

    print("Fetching weather data...")
    weather_data = get_weather_data(owm_key)
    loc_by_name  = {loc["name"]: loc for loc in weather_data}

    # Lead tweet — combined 2x2 card
    lead_text = (
        f"{period_text} Weather Report\n"
        f"Lakewood WA · Groveland CA · Death Valley CA · Reno NV\n"
        f"{timestamp}\n\n"
        f"Tap for full conditions at each station 👇\n\n"
        f"{LEAD_HASHTAGS}"
    )
    combined_img = "weather_report_k5.png" if os.path.exists("weather_report_k5.png") else "weather_report.png"

    print("Posting combined card (lead tweet)...")
    media  = api_v1.media_upload(combined_img)
    lead   = client.create_tweet(
        text=lead_text,
        media_ids=[media.media_id],
        user_auth=True,
    )
    reply_to = lead.data["id"]
    print(f"  Lead posted — ID: {reply_to}")

    # Station replies
    for name in STATION_ORDER:
        loc = loc_by_name.get(name)
        if not loc:
            print(f"  Skipping {name} — no data"); continue

        slug      = name.lower().replace(" ", "_")
        card_path = f"weather_{slug}_k5.png"
        if not os.path.exists(card_path):
            card_path = combined_img

        caption = _build_station_caption(loc, period_text, timestamp)

        print(f"  Waiting 90s before {name}...")
        time.sleep(90)

        print(f"  Posting {name}...")
        media  = api_v1.media_upload(card_path)
        reply  = client.create_tweet(
            text=caption,
            media_ids=[media.media_id],
            in_reply_to_tweet_id=reply_to,
            user_auth=True,
        )
        reply_to = reply.data["id"]
        print(f"    {name} — ID: {reply_to}")

    print("Twitter thread complete.")


if __name__ == "__main__":
    post_to_twitter()
