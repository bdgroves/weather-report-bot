import os
import sys
import tweepy


def post_to_twitter():
    api_key      = os.environ["TWITTER_API_KEY"]
    api_secret   = os.environ["TWITTER_API_SECRET"]
    access_token = os.environ["TWITTER_ACCESS_TOKEN"]
    access_secret= os.environ["TWITTER_ACCESS_SECRET"]
    report_period= os.environ.get("REPORT_PERIOD", "morning")
    timestamp    = os.environ.get("TIMESTAMP", "")

    period_text = "Morning" if report_period == "morning" else "Evening"

    tweet_text = (
        f"{period_text} Weather Report\n"
        f"Lakewood WA | Groveland CA | Death Valley CA | Reno NV\n"
        f"{timestamp}\n\n"
        f"Current conditions, temps, UV, wind and more!\n\n"
        f"#Weather #Lakewood #DeathValley #Reno #GrovelandCA #PNW #DailyWeather"
    )

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


if __name__ == "__main__":
    post_to_twitter()