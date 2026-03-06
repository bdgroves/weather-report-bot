import requests
import os
import math
from datetime import datetime
import pytz

LOCATIONS = [
    {"name": "Lakewood",     "state": "WA", "display": "Lakewood, WA",     "emoji": "🌲",        "lat": 47.1718, "lon": -122.5185},
    {"name": "Groveland",    "state": "CA", "display": "Groveland, CA",    "emoji": "🏔",  "lat": 37.8368, "lon": -120.2324},
    {"name": "Death Valley", "state": "CA", "display": "Death Valley, CA", "emoji": "🔥",                  "lat": 36.5323, "lon": -116.9325},
    {"name": "Reno",         "state": "NV", "display": "Reno, NV",         "emoji": "🎰",          "lat": 39.5296, "lon": -119.8138},
]


def get_weather_data(api_key):
    weather_data = []
    for loc in LOCATIONS:
        current_url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?lat={loc['lat']}&lon={loc['lon']}&appid={api_key}&units=imperial"
        )
        forecast_url = (
            "https://api.openweathermap.org/data/2.5/forecast"
            f"?lat={loc['lat']}&lon={loc['lon']}&appid={api_key}&units=imperial&cnt=8"
        )

        print(f"  Fetching {loc['display']}...")

        cr = requests.get(current_url,  timeout=10)
        cr.raise_for_status()
        c = cr.json()

        fr = requests.get(forecast_url, timeout=10)
        fr.raise_for_status()
        f = fr.json()

        temps_fc  = [x["main"]["temp"] for x in f["list"]]
        temp_high = max(temps_fc)
        temp_low  = min(temps_fc)
        pop       = max([x.get("pop", 0) for x in f["list"]]) * 100

        temp      = c["main"]["temp"]
        humidity  = c["main"]["humidity"]
        dew_point = calc_dew_point(temp, humidity)
        uv_index  = get_uv_index(api_key, loc["lat"], loc["lon"])

        tz      = pytz.timezone("America/Los_Angeles")
        sunrise = datetime.fromtimestamp(c["sys"]["sunrise"], tz=tz).strftime("%I:%M %p")
        sunset  = datetime.fromtimestamp(c["sys"]["sunset"],  tz=tz).strftime("%I:%M %p")

        weather_data.append({
            "display":     loc["display"],
            "emoji":       loc["emoji"],
            "name":        loc["name"],
            "state":       loc["state"],
            "temp":        round(temp),
            "feels_like":  round(c["main"]["feels_like"]),
            "temp_high":   round(temp_high),
            "temp_low":    round(temp_low),
            "humidity":    humidity,
            "wind_speed":  round(c["wind"].get("speed", 0)),
            "wind_dir":    degrees_to_compass(c["wind"].get("deg", 0)),
            "description": c["weather"][0]["description"].title(),
            "uv_index":    uv_index,
            "visibility":  round(c.get("visibility", 0) / 1609.34, 1),
            "pressure":    c["main"].get("pressure", 0),
            "dew_point":   round(dew_point),
            "cloud_cover": c["clouds"].get("all", 0),
            "sunrise":     sunrise,
            "sunset":      sunset,
            "heat_label":  get_heat_label(temp),
            "pop":         round(pop),
        })
        print(f"    OK: {round(temp)}F  {c['weather'][0]['description'].title()}")

    return weather_data


def get_uv_index(api_key, lat, lon):
    try:
        url = (
            "https://api.openweathermap.org/data/2.5/uvi"
            f"?lat={lat}&lon={lon}&appid={api_key}"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return round(r.json().get("value", 0))
    except Exception as e:
        print(f"    UV fetch skipped: {e}")
        return 0


def calc_dew_point(temp_f, humidity):
    temp_c = (temp_f - 32) * 5 / 9
    a, b   = 17.27, 237.7
    alpha  = ((a * temp_c) / (b + temp_c)) + math.log(humidity / 100.0)
    dew_c  = (b * alpha) / (a - alpha)
    return dew_c * 9 / 5 + 32


def degrees_to_compass(degrees):
    d = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
         "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return d[round(degrees / 22.5) % 16]


def get_heat_label(temp_f):
    if temp_f >= 130:   return "INFERNO"
    elif temp_f >= 110: return "EXTREME HEAT"
    elif temp_f >= 95:  return "Very Hot"
    elif temp_f >= 80:  return "Warm"
    elif temp_f >= 65:  return "Pleasant"
    elif temp_f >= 50:  return "Cool"
    elif temp_f >= 32:  return "Cold"
    else:               return "Freezing"
