# 🌪️ weather-report-bot

> *"It's already on the ground. It's not gonna stop."*

A fully automated broadcast-quality weather intelligence system. Every hour it pulls live conditions for four wildly different places and refreshes the [dashboard](https://brooksgroves.com/weather-report-bot/). Twice a day — once in the morning, once in the evening — it posts one report to X and Bluesky: the combined card and a line per station. No human required.

---

## 📡 The Stations

| Station | Location | Label |
|---|---|---|
| 🏠 | Lakewood, WA | **HOME BASE** — Pacific Northwest maritime climate. Cool, wet, green. |
| 🏔️ | Groveland, CA | **SIERRA FOOTHILLS** — Gateway to Yosemite. Four seasons in one week. |
| 🔥 | Death Valley, CA | **EXTREME CONDITIONS** — Hottest place on Earth. No mercy. |
| 🎰 | Reno, NV | **BIGGEST LITTLE CITY** — High desert. Wind. Dry. |

Four locations. Four completely different air masses. One report.

---

## 📸 Latest Cards

### Combined Report
![Daily Weather Report](https://raw.githubusercontent.com/bdgroves/weather-report-bot/charts/weather_report.png)

### Individual Station Cards

| Lakewood, WA | Groveland, CA |
|---|---|
| ![Lakewood](https://raw.githubusercontent.com/bdgroves/weather-report-bot/charts/weather_lakewood.png) | ![Groveland](https://raw.githubusercontent.com/bdgroves/weather-report-bot/charts/weather_groveland.png) |

| Death Valley, CA | Reno, NV |
|---|---|
| ![Death Valley](https://raw.githubusercontent.com/bdgroves/weather-report-bot/charts/weather_death_valley.png) | ![Reno](https://raw.githubusercontent.com/bdgroves/weather-report-bot/charts/weather_reno.png) |

---

## ⚡ How It Works

```
GitHub Actions (hourly; posts once per morning and evening window)
        │
        ▼
  OpenWeatherMap API
  ┌─────────────────────────────────────┐
  │  Current conditions  ·  Forecast    │
  │  UV index  ·  Humidity  ·  Wind     │
  │  Pressure  ·  Dew point  ·  Clouds  │
  └─────────────────────────────────────┘
        │
        ▼
  Matplotlib renderer (pure geometry, no emoji fonts)
  ┌─────────────────────────────────────┐
  │  Broadcast TV-style station cards   │
  │  1200×675 · 16:9 · 150 DPI          │
  │  Weather icons drawn from scratch   │
  │  Temp range bar · Wind compass      │
  │  Arc gauges · Sky & atmosphere      │
  └─────────────────────────────────────┘
        │
        ▼
  One post to X + Bluesky:
  combined card, a line per station,
  NWS warnings/watches if any
```

---

## 🗂️ Project Structure

```
weather-report-bot/
├── src/
│   ├── main.py           # Orchestrator
│   ├── weather.py        # OpenWeatherMap fetcher
│   ├── chart.py          # Broadcast card renderer + post text builder
│   ├── chart_k5.py       # The 2x2 card that gets posted
│   ├── export_json.py    # weather_data.json for the dashboard
│   └── social_post.py    # One report post to X and Bluesky
├── tests/test_social.py  # Offline tests (fake data, fake networks)
├── logs/                 # last_run.log + posts.jsonl, committed each run
├── social_state.json     # What posted when, and each network's status
├── .github/
│   └── workflows/
│       └── weather_report.yml   # Scheduled automation
└── pixi.toml             # Environment & task runner
```

---

## 🛠️ Stack

| Tool | Purpose |
|---|---|
| **Python 3.11+** | Core language |
| **Matplotlib** | Card rendering — every pixel hand-drawn |
| **OpenWeatherMap API** | Live weather data (One Call 3.0) |
| **Tweepy** | Twitter / X v2 API |
| **Requests** | BlueSky AT Protocol |
| **Pixi** | Reproducible environment + task runner |
| **GitHub Actions** | Scheduled automation — no server needed |

---

## 🚀 Running Locally

```powershell
# Install pixi if you haven't
# https://prefix.dev/docs/pixi/overview

# Clone and enter
git clone https://github.com/bdgroves/weather-report-bot
cd weather-report-bot

# Set your API key
$env:OPENWEATHER_API_KEY = "your_key_here"

# Generate cards
pixi run chart

# Post the report (requires X + Bluesky secrets)
$env:POST_NOW = "1"   # post even outside the morning/evening windows
$env:DRY_RUN = "1"   # print the post, send nothing
pixi run social

# Or do everything at once
pixi run all
```

---

## 🔐 Required Secrets

Set these in **GitHub → Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `OPENWEATHER_API_KEY` | [openweathermap.org](https://openweathermap.org/api) — One Call 3.0 |
| `TWITTER_API_KEY` | Twitter Developer App — OAuth 1.0a |
| `TWITTER_API_SECRET` | Twitter Developer App |
| `TWITTER_ACCESS_TOKEN` | User access token (Read + Write) |
| `TWITTER_ACCESS_SECRET` | User access token secret |
| `BLUESKY_HANDLE` | e.g. `yourhandle.bsky.social` |
| `BLUESKY_APP_PASSWORD` | BlueSky App Password (not your login password) |

---

## 📅 Schedule

The workflow runs hourly for the dashboard (GitHub decides exactly when; lately every two or three hours). The report posts on the **first run of each window** that hasn't posted yet:

| Report | Window (Pacific) |
|---|---|
| Morning | 6:00–11:59 AM |
| Evening | 5:00–10:59 PM |

From the **Actions** tab, **Run workflow** has two switches: *Post now* (post outside the windows) and *Dry run* (log the post, send nothing).

## 🩺 Is it posting?

- `logs/posts.jsonl` — every post attempt, per network, with the exact error if one failed
- `logs/last_run.log` — the latest run
- `social_state.json` — last post and current status for X and Bluesky

X and Bluesky post independently, so one failing never stops the other. If the card won't upload, the report goes out as text. When a network starts refusing posts, the run **fails once** so GitHub sends an email, then logs quietly until it recovers.

---

## 🌡️ Card Design

Each station card is a **1200×675 broadcast-style graphic** with three panels:

**Left — Current Conditions**
Big temperature (color-coded by heat level), drawn weather icon, feels like, Hi/Lo box, today's temperature range bar with live position marker.

**Center — Instruments**
Arc gauge for humidity, arc gauge for UV index (color-coded LOW→EXTREME), wind compass with directional arrow, and five KPI boxes (humidity, wind, visibility, dew point, pressure).

**Right — Sky & Atmosphere**
Precipitation chance bar, cloud cover bar, sunrise/sunset times, dew point, pressure, visibility, and current heat label.

**Header:** Station label, city/state, condition badge, live timestamp.
**Ticker:** Sunrise · Sunset · Dew Pt · Pressure · Clouds · Visibility · @bdgroves

---

## 📣 Follow the Reports

- **Twitter/X:** [@bdgroves](https://twitter.com/bdgroves)
- **BlueSky:** [@bdgroves.bsky.social](https://bsky.app/profile/bdgroves.bsky.social)

Hashtags on X: `#WAwx #CAwx #NVwx`. Bluesky gets a link to the dashboard instead.

---

*Built with Python, Matplotlib, and a deep appreciation for atmospheric chaos.*
*Data: OpenWeatherMap API · Automation: GitHub Actions*
