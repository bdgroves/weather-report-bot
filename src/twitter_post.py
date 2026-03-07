import os
import sys
import tweepy

sys.path.insert(0, os.path.dirname(__file__))
from weather import get_weather_data
from chart import build_post_text


def post_to_twitter():
    api_key       = os.environ["TWITTER_API_KEY"]
    api_secret    = os.environ["TWITTER_API_SECRET"]
    access_token  = os.environ["TWITTER_ACCESS_TOKEN"]
    access_secret = os.environ["TWITTER_ACCESS_SECRET"]
    report_period = os.environ.get("REPORT_PERIOD", "morning")
    timestamp     = os.environ.get("TIMESTAMP", "")
    owm_key       = os.environ.get("OPENWEATHER_API_KEY", "")

    # Build rich post text from live data if available, else fallback
    if owm_key:
        print("Fetching weather data for post text...")
        try:
            weather_data = get_weather_data(owm_key)
            tweet_text = build_post_text(weather_data, report_period, timestamp)
        except Exception as e:
            print(f"  Could not fetch live data for text: {e}")
            tweet_text = _fallback_text(report_period, timestamp)
    else:
        tweet_text = _fallback_text(report_period, timestamp)

    # Twitter has a 280 char limit — truncate gracefully if needed
    if len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + "..."

    auth = tweepy.OAuthHandler(api_key, api_secret)
    auth.set_access_token(access_token, access_secret)
    api_v1 = tweepy.API(auth)

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    print("Uploading image to Twitter...")
    media = api_v1.media_upload("weather_report.png")

    print("Posting tweet...")
    response = client.create_tweet(text=tweet_text, media_ids=[media.media_id])
    print(f"Tweet posted! ID: {response.data['id']}")


def _fallback_text(report_period, timestamp):
    period = "Morning" if report_period == "morning" else "Evening"
    return (
        f"{period} Weather Report  |  {timestamp}\n"
        f"Lakewood WA  |  Groveland CA  |  Death Valley CA  |  Reno NV\n\n"
        f"#Weather #Lakewood #DeathValley #Reno #GrovelandCA #PNW #DailyWeather"
    )


if __name__ == "__main__":
    post_to_twitter()
