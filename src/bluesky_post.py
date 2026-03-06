import os
import requests
from datetime import datetime, timezone

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

    period_text = "Morning" if report_period == "morning" else "Evening"

    post_text = (
        f"{period_text} Weather Report\n"
        f"Lakewood WA | Groveland CA | Death Valley CA | Reno NV\n"
        f"{timestamp}\n\n"
        f"Current conditions, temps, UV, wind and more!\n\n"
        f"#Weather #Lakewood #DeathValley #Reno #GrovelandCA #PNW"
    )

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
                    "alt": f"{period_text} weather report for Lakewood WA, Groveland CA, Death Valley CA, Reno NV",
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


if __name__ == "__main__":
    post_to_bluesky()