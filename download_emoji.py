import requests
import os

os.makedirs("assets/emoji", exist_ok=True)

BASE = "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/"

EMOJI_NEEDED = {
    # Location icons
    "tree":         "1f332",   # evergreen tree    - Lakewood
    "mountain2":    "1f5fb",   # mount fuji        - Groveland
    "fire":         "1f525",   # fire              - Death Valley
    "gem":          "1f48e",   # gem               - Reno

    # Header
    "sunrise2":     "1f304",   # sunrise mountains - morning
    "moon":         "1f319",   # crescent moon     - evening

    # Fun stats
    "lightning":    "26a1",    # lightning         - hottest
    "snowflake":    "2744",    # snowflake         - coolest
    "wind":         "1f4a8",   # dash wind         - windiest
    "droplet":      "1f4a7",   # droplet           - humidity
    "sun2":         "1f31e",   # sun with face     - UV
    "thermometer":  "1f321",   # thermometer       - temp spread

    # Extras
    "cactus":       "1f335",   # cactus
    "cloud":        "2601",    # cloud
    "umbrella":     "2614",    # umbrella rain
}

print(f"Downloading {len(EMOJI_NEEDED)} emoji files...")
ok, fail = 0, 0

for name, code in EMOJI_NEEDED.items():
    url      = f"{BASE}{code}.png"
    filepath = f"assets/emoji/{name}.png"

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)
        print(f"  OK    {name}.png")
        ok += 1
    except Exception as e:
        print(f"  FAIL  {name}.png -> {e}")
        fail += 1

print(f"\nDone! {ok} OK  {fail} failed")