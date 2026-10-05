"""
social_post.py — one weather report post, twice a day, to X and Bluesky.

What changed (October 2026)
---------------------------
* One post per report, not a five-post thread: the combined 2x2 card plus a
  line per station. Light hashtags on X; none on Bluesky (they only work there
  with facets), where the dashboard link is a real link instead.
* Reads weather_data.json, written earlier in the same run, instead of
  fetching every station again.
* Posts on the first run inside each window (morning 6–11 AM PT, evening
  5–10 PM PT) that hasn't posted yet. The old check only posted when a run
  happened to land in the 7 AM or 6 PM hour, and GitHub's schedule rarely
  obliged: 5 tries in 10 days.
* X and Bluesky are independent. The old workflow stopped at the first X
  error, so Bluesky never posted either.
* If the card can't be uploaded, the report still goes out as text.
* Every attempt is logged to logs/posts.jsonl and logs/last_run.log, and the
  status lives in social_state.json. When a network starts failing, the run
  fails once so GitHub sends an email, then logs quietly until it recovers.

Env: TWITTER_* , BLUESKY_HANDLE, BLUESKY_APP_PASSWORD
     POST_NOW=1   post regardless of window / already-posted (manual runs)
     DRY_RUN=1    log the post, send nothing
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

PT = ZoneInfo("America/Los_Angeles")
STATE_FILE = "social_state.json"
LOG_DIR = "logs"
DASHBOARD = "https://brooksgroves.com/weather-report-bot/"
X_TAGS = "#WAwx #CAwx #NVwx"
ORDER = ["Lakewood", "Groveland", "Death Valley", "Reno"]
ICON = {"Lakewood": "🌲", "Groveland": "🏔️", "Death Valley": "🔥", "Reno": "🎰"}
WINDOWS = {"morning": range(6, 12), "evening": range(17, 23)}
DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
POST_NOW = os.environ.get("POST_NOW", "").lower() in ("1", "true", "yes")

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(os.path.join(LOG_DIR, "last_run.log"), "w", "utf-8")])
log = logging.getLogger("social")


# ── What to say ───────────────────────────────────────────────────────────────
def current_slot(now: datetime) -> str | None:
    for period, hours in WINDOWS.items():
        if now.hour in hours:
            return f"{now:%Y-%m-%d}-{period}"
    return None


def alert_notes(stations: list[dict]) -> list[str]:
    """Warnings and watches only; statements and advisories stay off the post."""
    notes = []
    for s in stations:
        for a in s.get("nws_alerts") or []:
            if a.endswith(("Warning", "Watch")):
                notes.append(f"⚠️ {s['name']}: {a}")
    return notes[:2]


def station_line(s: dict) -> str:
    desc = (s.get("description") or "").lower()
    return (f"{ICON.get(s['name'], '•')} {s['name']} {s['temp']}° {desc} · "
            f"H{s['temp_high']} L{s['temp_low']}")


def build_text(data: dict, now: datetime, network: str) -> str:
    by = {s["name"]: s for s in data.get("stations", [])}
    stations = [by[n] for n in ORDER if n in by]
    when = f"{now:%a %b} {now.day}, {now.strftime('%I:%M %p').lstrip('0')}"
    lines = [f"West Coast weather · {when}"]
    lines += [station_line(s) for s in stations]
    lines += alert_notes(stations)
    tail = [DASHBOARD] + ([X_TAGS] if network == "x" else [])
    text = "\n".join(lines + [""] + tail)
    limit = 280 if network == "x" else 300
    # X counts a link as 23 characters.
    size = len(text) - (len(DASHBOARD) - 23 if network == "x" else 0)
    while size > limit and len(lines) > 1 + len(stations):
        lines.pop()  # drop alert notes before anything else
        text = "\n".join(lines + [""] + tail)
        size = len(text) - (len(DASHBOARD) - 23 if network == "x" else 0)
    return text


def alt_text(data: dict) -> str:
    by = {s["name"]: s for s in data.get("stations", [])}
    parts = [f"{s['display']}: {s['temp']}°F, {s.get('description', '').lower()}, "
             f"high {s['temp_high']}, low {s['temp_low']}, humidity {s['humidity']}%, "
             f"wind {s['wind_speed']} mph"
             for s in (by[n] for n in ORDER if n in by)]
    return "Weather cards for four stations. " + ". ".join(parts) + "."


# ── X ─────────────────────────────────────────────────────────────────────────
def x_upload(image: str) -> tuple[str | None, str]:
    """Upload the card. Tries the v2 media endpoint, then the old v1.1 one."""
    from requests_oauthlib import OAuth1
    auth = OAuth1(os.environ["TWITTER_API_KEY"], os.environ["TWITTER_API_SECRET"],
                  os.environ["TWITTER_ACCESS_TOKEN"], os.environ["TWITTER_ACCESS_SECRET"])
    errors = []
    try:
        with open(image, "rb") as f:
            r = requests.post("https://api.x.com/2/media/upload", auth=auth, timeout=60,
                              files={"media": (os.path.basename(image), f, "image/png")},
                              data={"media_category": "tweet_image"})
        if r.ok:
            mid = (r.json().get("data") or {}).get("id") or r.json().get("media_id_string")
            if mid:
                return str(mid), ""
        errors.append(f"v2 HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        errors.append(f"v2 {type(e).__name__}: {e}")
    try:
        import tweepy
        a = tweepy.OAuth1UserHandler(os.environ["TWITTER_API_KEY"], os.environ["TWITTER_API_SECRET"],
                                     os.environ["TWITTER_ACCESS_TOKEN"], os.environ["TWITTER_ACCESS_SECRET"])
        return str(tweepy.API(a).media_upload(image).media_id), ""
    except Exception as e:
        errors.append(f"v1.1 {type(e).__name__}: {e}")
    return None, " | ".join(errors)[:400]


def post_x(text: str, image: str | None) -> str:
    import tweepy
    media_id, img_err = (x_upload(image) if image else (None, "no card"))
    if img_err:
        log.warning(f"X image upload failed, posting text only: {img_err}")
    client = tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"], consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"], access_token_secret=os.environ["TWITTER_ACCESS_SECRET"])
    r = client.create_tweet(text=text, media_ids=[media_id] if media_id else None)
    return f"posted id={r.data['id']}" + (f" (text only: {img_err})" if img_err else "")


# ── Bluesky ───────────────────────────────────────────────────────────────────
BSKY = "https://bsky.social/xrpc"


def post_bsky(text: str, image: str | None, alt: str) -> str:
    s = requests.post(f"{BSKY}/com.atproto.server.createSession", timeout=20, json={
        "identifier": os.environ["BLUESKY_HANDLE"], "password": os.environ["BLUESKY_APP_PASSWORD"]})
    s.raise_for_status()
    sess = s.json()
    hdr = {"Authorization": f"Bearer {sess['accessJwt']}"}
    record = {"$type": "app.bsky.feed.post", "text": text,
              "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    # Make the dashboard URL a real link (byte offsets, as Bluesky wants).
    b = text.encode("utf-8")
    start = b.find(DASHBOARD.encode())
    if start >= 0:
        record["facets"] = [{"index": {"byteStart": start, "byteEnd": start + len(DASHBOARD.encode())},
                             "features": [{"$type": "app.bsky.richtext.facet#link", "uri": DASHBOARD}]}]
    note = ""
    if image:
        try:
            with open(image, "rb") as f:
                u = requests.post(f"{BSKY}/com.atproto.repo.uploadBlob", data=f.read(), timeout=60,
                                  headers={**hdr, "Content-Type": "image/png"})
            u.raise_for_status()
            record["embed"] = {"$type": "app.bsky.embed.images",
                               "images": [{"image": u.json()["blob"], "alt": alt[:1000]}]}
        except Exception as e:
            note = f" (text only: {e})"
            log.warning(f"Bluesky image upload failed, posting text only: {e}")
    r = requests.post(f"{BSKY}/com.atproto.repo.createRecord", headers=hdr, timeout=20, json={
        "repo": sess["did"], "collection": "app.bsky.feed.post", "record": record})
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    return f"posted {r.json().get('uri')}{note}"


# ── Run ───────────────────────────────────────────────────────────────────────
def load_state() -> dict:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def record(network: str, slot: str, outcome: str, text: str) -> None:
    path = os.path.join(LOG_DIR, "posts.jsonl")
    lines = open(path, encoding="utf-8").read().splitlines() if os.path.exists(path) else []
    lines.append(json.dumps({"t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "network": network, "slot": slot, "outcome": outcome, "text": text},
                            ensure_ascii=False))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines[-500:]) + "\n")


def main() -> int:
    now = datetime.now(PT)
    slot = current_slot(now) or (f"{now:%Y-%m-%d-%H%M}-manual" if POST_NOW else None)
    if not slot:
        log.info(f"{now:%H:%M} PT is outside the posting windows; nothing to post.")
        return 0
    state = load_state()
    with open("weather_data.json", encoding="utf-8") as f:
        data = json.load(f)
    image = next((p for p in ("weather_report_k5.png", "weather_report.png") if os.path.exists(p)), None)
    alt = alt_text(data)

    networks = {
        "x": (post_x, os.environ.get("POST_TO_X", "on").lower() == "on" and all(os.environ.get(k) for k in (
            "TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"))),
        "bluesky": (lambda t, i: post_bsky(t, i, alt),
                    bool(os.environ.get("BLUESKY_HANDLE") and os.environ.get("BLUESKY_APP_PASSWORD"))),
    }
    exit_code = 0
    for name, (send, configured) in networks.items():
        st = state.setdefault(name, {})
        if st.get("last_slot") == slot and not POST_NOW:
            log.info(f"{name}: already posted {slot}")
            continue
        text = build_text(data, now, name)
        if not configured:
            log.warning(f"{name}: secrets not set; skipping")
            continue
        if DRY_RUN:
            log.info(f"[DRY RUN] {name} ({len(text)} chars)\n{text}")
            record(name, slot, "dry-run", text)
            continue
        try:
            outcome = send(text, image)
        except Exception as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            err = f"HTTP {status} {type(e).__name__}: {e}"[:400]
            log.error(f"{name}: post failed: {err}")
            record(name, slot, f"error: {err}", text)
            if st.get("ok", True):
                log.error(f"{name} stopped accepting posts. Failing this run once so GitHub sends an email.")
                exit_code = 1
            st.update(ok=False, error=err, error_since=st.get("error_since") or now.isoformat(timespec="minutes"))
            continue
        log.info(f"{name}: {outcome}")
        record(name, slot, outcome, text)
        st.update(ok=True, error="", error_since="", last_slot=slot,
                  last_post=now.isoformat(timespec="minutes"))
    state["last_run"] = now.isoformat(timespec="minutes")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
        f.write("\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
