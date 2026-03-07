#!/usr/bin/env python3
"""
Download Twemoji PNGs for our weather chart.
Twemoji CDN: https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/
Filename = unicode codepoint in hex (lowercase) + .png
"""
import requests
import os

# Create emoji directory
os.makedirs("assets/emoji", exist_ok=True)

BASE_URL = "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/"

# Emoji we need: name -> unicode hex codepoint
EMOJI_NEEDED = {
    # Location icons
    "tree":         "1f332",   # evergreen tree    - Lakewood
    "mountain":     "26f0",    # mountain          - Groveland
    "fire":         "1f525",   # fire              - Death Valley
    "slots":        "1f3b0",   # slot machine      - Reno

    # Header
    "sunrise":      "1f305",   # sunrise           - morning
    "sunset":       "1f306",   # sunset city       - evening

    # Fun stats
    "thermometer":  "1f321",   # thermometer       - temp spread
    "snowflake":    "2744",    # snowflake         - coolest
    "wind":         "1f32c",   # wind face         - windiest
    "droplet":      "1f4a7",   # droplet           - humidity
    "sun":          "2600",    # sun               - UV
    "lightning":    "26a1",    # lightning         - hottest

    # KPI row icons
    "clock":        "1f551",   # clock             - time
    "pin":          "1f4cd",   # pin               - location
    "cloud":        "2601",    # cloud             - clouds
    "umbrella":     "2614",    # umbrella rain     - precip
    "eye":          "1f441",   # eye               - visibility
    "dash":         "1f4a8",   # dash/wind         - wind speed
    "gauge":        "1f321",   # thermometer       - pressure
    "wave":         "1f30a",   # wave              - dew point
}

print(f"Downloading {len(EMOJI_NEEDED)} emoji files...")
failed = []

for name, code in EMOJI_NEEDED.items():
    url      = f"{BASE_URL}{code}.png"
    filepath = f"assets/emoji/{name}.png"

    if os.path.exists(filepath):
        print(f"  SKIP  {name}.png (already exists)")
        continue

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)
        print(f"  OK    {name}.png  ({len(resp.content)/1024:.1f} KB)")
    except Exception as e:
        print(f"  FAIL  {name}.png  -> {e}")
        failed.append(name)

print(f"\nDone! {len(EMOJI_NEEDED) - len(failed)}/{len(EMOJI_NEEDED)} downloaded")
if failed:
    print(f"Failed: {failed}")

# Verify all files
print("\nVerifying files:")
for name in EMOJI_NEEDED:
    path = f"assets/emoji/{name}.png"
    size = os.path.getsize(path) if os.path.exists(path) else 0
    status = "OK" if size > 0 else "MISSING"
    print(f"  {status}  {name}.png  ({size} bytes)")