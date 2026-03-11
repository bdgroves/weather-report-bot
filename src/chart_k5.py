"""
chart_k5.py — Clean scroll-friendly cards for Twitter/BlueSky.
Simple, bold, glanceable. Matches dashboard aesthetic without the clutter.
"""

from PIL import Image, ImageDraw, ImageFont
import math, os
from datetime import datetime
try:
    import pytz
    _PT = pytz.timezone("America/Los_Angeles")
    def _now_pt():
        return datetime.now(_PT)
except ImportError:
    def _now_pt():
        return datetime.utcnow()

_FP = "/usr/share/fonts/truetype"
def _f(name, size):
    paths = {
        "black":  f"{_FP}/dejavu/DejaVuSansCondensed-Bold.ttf",
        "bold":   f"{_FP}/google-fonts/Poppins-Bold.ttf",
        "medium": f"{_FP}/google-fonts/Poppins-Medium.ttf",
        "reg":    f"{_FP}/google-fonts/Poppins-Regular.ttf",
        "light":  f"{_FP}/google-fonts/Poppins-Light.ttf",
    }
    try:    return ImageFont.truetype(paths[name], size)
    except: return ImageFont.load_default()

BG       = (5,   13,  26)
PANEL    = (10,  24,  40)
PANEL2   = (8,   18,  32)
BORDER   = (15,  37,  64)
ACC      = (56,  189, 248)
ACC2     = (14,  165, 233)
GOLD     = (255, 214, 10)
ORANGE   = (249, 115, 22)
MUTED    = (74,  100, 128)
TEXT     = (200, 220, 240)
WHITE    = (237, 243, 250)
WATCH_BG = (204, 68,  0)
WATCH_DK = (170, 51,  0)

def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def _tcol(t):
    for thr,c in [(100,"#FF3333"),(90,"#FF6B35"),(80,"#F78166"),
                  (70,"#E3B341"),(60,"#3CB86B"),(50,"#58A6FF"),(32,"#79C0FF")]:
        if t >= thr: return _hex(c)
    return _hex("#B0D8FF")

def _uv_info(u):
    for thr,c,l in [(11,"#A855F7","EXTREME"),(8,"#EF4444","VERY HIGH"),
                    (6,"#F97316","HIGH"),(3,"#EAB308","MODERATE")]:
        if u >= thr: return _hex(c), l
    return _hex("#22C55E"), "LOW"

def _pick_icon(desc):
    d = (desc or "").lower()
    if any(w in d for w in ("thunder","storm")):          return "storm"
    if any(w in d for w in ("drizzle","rain","shower")):  return "rain"
    if any(w in d for w in ("snow","sleet","blizzard")):  return "snow"
    if any(w in d for w in ("fog","mist","haze")):        return "fog"
    if any(w in d for w in ("overcast","broken")):        return "cloudy"
    if any(w in d for w in ("scattered","few","partly")): return "partly"
    if any(w in d for w in ("clear","sunny")):            return "sunny"
    return "partly"

def _station_label(name, temp, wind=0, low=99, high=0, pop=0, nws_alerts=None):
    """Dynamic subtitle for each station based on current conditions."""

    # If NWS has active alerts, that takes priority
    if nws_alerts:
        return "ACTIVE NWS ALERT"

    if name == "Lakewood":
        if high >= 90:   return "RARE HEAT EVENT"
        if low <= 32:    return "FREEZE WARNING"
        if wind >= 30:   return "HIGH WIND EVENT"
        if wind >= 20:   return "BREEZY CONDITIONS"
        if pop >= 80:    return "HEAVY RAIN DAY"
        return "HOME BASE"

    if name == "Groveland":
        if high >= 100:  return "TRIPLE DIGIT HEAT"
        if high >= 95:   return "EXTREME HEAT"
        if low <= 25:    return "HARD FREEZE"
        if low <= 32:    return "FREEZING TEMPS"
        if wind >= 30:   return "HIGH WIND EVENT"
        if pop >= 70:    return "HEAVY PRECIP"
        if high >= 85:   return "WARM IN THE FOOTHILLS"
        return "SIERRA FOOTHILLS"

    if name == "Death Valley":
        if temp >= 120:  return "DANGEROUS — STAY INSIDE"
        if temp >= 115:  return "LIFE-THREATENING HEAT"
        if temp >= 110:  return "TRIPLE DIGIT HEAT"
        if temp >= 100:  return "SCORCHING"
        if temp >= 90:   return "DESERT HEAT"
        if temp >= 80:   return "WARM & DRY"
        if pop >= 30:    return "RARE DESERT RAIN"
        if low <= 35:    return "COLD DESERT NIGHT"
        return "MOJAVE DESERT"

    if name == "Reno":
        if high >= 105:  return "EXCESSIVE HEAT"
        if high >= 100:  return "TRIPLE DIGIT HEAT"
        if low <= 20:    return "HARD FREEZE"
        if low <= 28:    return "FREEZE WARNING"
        if wind >= 30:   return "HIGH WIND EVENT"
        if wind >= 20:   return "WINDY IN THE BASIN"
        if pop >= 60:    return "RARE RAIN EVENT"
        if high >= 85:   return "WARM & SUNNY"
        return "BIGGEST LITTLE CITY"

    return name.upper()


# Per-station watch thresholds
_WATCH = {
    "Lakewood":     dict(pop=None,  wind=20, heat=90,  freeze=32),
    "Groveland":    dict(pop=60,    wind=20, heat=95,  freeze=28),
    "Death Valley": dict(pop=30,    wind=20, heat=110, freeze=35),
    "Reno":         dict(pop=50,    wind=20, heat=100, freeze=28),
}
_WATCH_DEFAULT =    dict(pop=70,    wind=20, heat=100, freeze=32)

def _watch_reasons(loc):
    t  = _WATCH.get(loc["name"], _WATCH_DEFAULT)
    r  = []
    if t["pop"]    and loc.get("pop",0)        >= t["pop"]:
        r.append(f"Heavy Rain {loc['pop']}%")
    if loc.get("wind_speed",0) >= t["wind"]:
        r.append(f"High Winds {loc['wind_speed']} mph")
    if loc.get("temp_high",0)  >= t["heat"]:
        r.append(f"Excessive Heat {loc['temp_high']}°F")
    if loc.get("temp_low",99)  <= t["freeze"]:
        r.append(f"Freeze Watch {loc['temp_low']}°F")
    # NWS alerts passed in via loc["nws_alerts"] list
    for alert in loc.get("nws_alerts", []):
        if alert not in r:
            r.append(alert)
    return r

def _fmt_time(t):
    return (t or "—").lstrip("0")

def _ctext(d, cx, y, txt, font, color):
    d.text((cx, y), txt, font=font, fill=color, anchor="mt")

def _rect(d, x, y, w, h, fill, radius=0, outline=None, outline_w=1):
    if radius > 0:
        d.rounded_rectangle([x,y,x+w,y+h], radius=radius, fill=fill,
                             outline=outline, width=outline_w)
    else:
        d.rectangle([x,y,x+w,y+h], fill=fill,
                    outline=outline, width=outline_w if outline else 0)

# ── ICONS ─────────────────────────────────────────────────────────────────────
def _draw_icon(img, cx, cy, r, kind):
    d = ImageDraw.Draw(img)
    def sun(x,y,sr,col=GOLD):
        d.ellipse([x-sr,y-sr,x+sr,y+sr],fill=col)
        for ang in range(0,360,45):
            rad=math.radians(ang)
            d.line([x+int(sr*1.45*math.cos(rad)),y+int(sr*1.45*math.sin(rad)),
                    x+int(sr*1.95*math.cos(rad)),y+int(sr*1.95*math.sin(rad))],
                   fill=col,width=max(3,sr//7))
    def cloud(x,y,cr,col=(90,128,162)):
        for dx,dy,rx,ry in [(0,0,cr,int(cr*.72)),(-int(cr*.62),int(cr*.08),int(cr*.60),int(cr*.48)),
                             (int(cr*.58),int(cr*.05),int(cr*.56),int(cr*.44)),
                             (-int(cr*.18),-int(cr*.28),int(cr*.48),int(cr*.38)),
                             (int(cr*.18),-int(cr*.28),int(cr*.48),int(cr*.38))]:
            d.ellipse([x+dx-rx,y+dy-ry,x+dx+rx,y+dy+ry],fill=col)
        d.rectangle([x-cr,y-int(cr*.1),x+cr,y+int(cr*.28)],fill=col)
    def drops(x,y,cr,col=_hex("#60A5FA")):
        for i,dx in enumerate([-int(cr*.38),0,int(cr*.38),-int(cr*.18)]):
            x0=x+dx; y0=y+int(cr*.32)+(i%2)*int(cr*.12)
            d.line([x0,y0,x0-int(cr*.05),y0+int(cr*.48)],fill=col,width=max(2,cr//10))

    if kind=="sunny":   sun(cx,cy,r)
    elif kind=="partly":
        sun(cx+int(r*.32),cy-int(r*.32),int(r*.68))
        cloud(cx-int(r*.08),cy+int(r*.12),int(r*.82),col=(65,95,128))
    elif kind in ("cloudy","fog"):
        cloud(cx,cy-int(r*.15),int(r*.88),col=(58,85,112))
        cloud(cx,cy+int(r*.22),int(r*.72),col=(88,125,158))
    elif kind=="rain":
        cloud(cx,cy-int(r*.22),int(r*.85)); drops(cx,cy,r)
    elif kind=="storm":
        cloud(cx,cy-int(r*.22),int(r*.85),col=(50,72,95))
        drops(cx,cy,r,col=_hex("#93C5FD"))
        pts=[cx+int(r*.1),cy+int(r*.08),cx-int(r*.18),cy+int(r*.55),
             cx+int(r*.06),cy+int(r*.55),cx-int(r*.22),cy+int(r*1.1)]
        d.line(pts,fill=_hex("#FDE047"),width=max(3,r//8))
    elif kind=="snow":
        cloud(cx,cy-int(r*.22),int(r*.85))
        for dxx,dyy in [(-int(r*.38),-int(r*.52)),(0,-int(r*.65)),(int(r*.38),-int(r*.52)),
                        (-int(r*.18),-int(r*.82)),(int(r*.18),-int(r*.82))]:
            s=max(4,r//9); d.ellipse([cx+dxx-s,cy+dyy-s,cx+dxx+s,cy+dyy+s],fill=WHITE)

def _mini_icon(img, cx, cy, r, kind):
    d = ImageDraw.Draw(img)
    def msun(x,y,sr,col=GOLD):
        d.ellipse([x-sr,y-sr,x+sr,y+sr],fill=col)
        for ang in range(0,360,60):
            rad=math.radians(ang)
            d.line([x+int(sr*1.3*math.cos(rad)),y+int(sr*1.3*math.sin(rad)),
                    x+int(sr*1.75*math.cos(rad)),y+int(sr*1.75*math.sin(rad))],
                   fill=col,width=max(2,sr//6))
    def mcloud(x,y,cr,col=(65,95,122)):
        d.ellipse([x-cr,y-int(cr*.65),x+cr,y+int(cr*.65)],fill=col)
        d.ellipse([x-int(cr*.55),y-cr,x+int(cr*.55),y],fill=col)
        d.rectangle([x-cr,y-int(cr*.1),x+cr,y+int(cr*.45)],fill=col)
    if kind=="sunny": msun(cx,cy,r)
    elif kind=="partly":
        msun(cx+int(r*.32),cy-int(r*.28),int(r*.66))
        mcloud(cx-int(r*.08),cy+int(r*.12),int(r*.78),col=(58,88,115))
    elif kind in ("cloudy","fog"): mcloud(cx,cy,r)
    elif kind in ("rain","storm"):
        mcloud(cx,cy-int(r*.18),int(r*.82),col=(45,68,90))
        for dx in [-int(r*.36),0,int(r*.36)]:
            d.line([cx+dx,cy+int(r*.38),cx+dx-int(r*.04),cy+int(r*.8)],
                   fill=_hex("#60A5FA"),width=max(2,r//8))
    elif kind=="snow":
        mcloud(cx,cy-int(r*.18),int(r*.82),col=(45,68,90))
        for dx in [-int(r*.36),0,int(r*.36)]:
            s=max(3,r//7); d.ellipse([cx+dx-s,cy+int(r*.55)-s,cx+dx+s,cy+int(r*.55)+s],fill=WHITE)


# ── SINGLE STATION CARD ───────────────────────────────────────────────────────
def render_card(loc, forecast=None, out="weather_card.png"):
    """
    Layout (top to bottom):
      - Watch banner (if triggered)
      - Header:  LABEL · City, ST · CONDITION
      - Hero:    Giant temp (left) | Icon (right)
      - Stats:   H/L  ·  Humidity  ·  Wind  ·  UV  (single clean row)
      - Forecast strip (if available)  — 5 days only for cleanliness
      - Footer branding
    """
    has_watch = bool(_watch_reasons(loc))
    has_fcst  = bool(forecast)

    W = 1200
    H_WATCH  = 52 if has_watch else 0
    H_HEADER = 88
    H_HERO   = 340
    H_STATS  = 90
    H_FCST   = 160 if has_fcst else 0
    H_FOOT   = 44
    H = H_WATCH + H_HEADER + H_HERO + H_STATS + H_FCST + H_FOOT

    img = Image.new("RGB", (W, H), BG)
    d   = ImageDraw.Draw(img)

    # Background texture (very subtle grid)
    for gx in range(0, W, 44):
        for gy in range(0, H, 44):
            d.ellipse([gx-1,gy-1,gx+1,gy+1], fill=(11,22,40))

    y = 0

    # ── WATCH BANNER ──────────────────────────────────────────────────────────
    if has_watch:
        reasons = _watch_reasons(loc)
        d.rectangle([0,y,W,y+H_WATCH], fill=WATCH_BG)
        d.rectangle([0,y,int(W*.18),y+H_WATCH], fill=WATCH_DK)
        d.text((14,y+H_WATCH//2), "WEATHER WATCH",
               font=_f("bold",20), fill=WHITE, anchor="lm")
        d.text((int(W*.19),y+H_WATCH//2), "  ·  ".join(reasons),
               font=_f("reg",18), fill=(255,208,160), anchor="lm")
        d.text((W-14,y+H_WATCH//2), "NWS Alerts",
               font=_f("light",17), fill=(255,208,160), anchor="rm")
        y += H_WATCH

    # ── HEADER ────────────────────────────────────────────────────────────────
    d.rectangle([0,y,W,y+H_HEADER], fill=PANEL)
    d.rectangle([0,y,W,y+5], fill=ACC)  # cyan accent stripe

    slabel = _station_label(loc["name"], loc["temp"], wind=loc.get("wind_speed",0), low=loc.get("temp_low",99), high=loc.get("temp_high",0), pop=loc.get("pop",0), nws_alerts=loc.get("nws_alerts"))
    # Label pill left
    lw = int(_f("bold",16).getlength(slabel)) + 24
    _rect(d, 18, y+14, lw, 26, (0,40,65), radius=4)
    d.text((18+lw//2, y+14), slabel,
           font=_f("bold",16), fill=ACC, anchor="mt")

    # City name
    d.text((18, y+44), f"{loc['name']}, {loc['state']}",
           font=_f("black",38), fill=WHITE, anchor="lt")

    # Condition — right side
    cond = loc.get("description","").upper()
    d.text((W-20, y+H_HEADER//2), cond,
           font=_f("bold",24), fill=TEXT, anchor="rm")

    # Timestamp — small, under condition — use passed env var (PT) or fallback to PT now
    _ts_env = os.environ.get("TIMESTAMP", "")
    if _ts_env:
        # Workflow passes e.g. "7:02 AM PT | March 11, 2026" — show first part only
        ts = _ts_env.split("|")[0].strip()
    else:
        now = _now_pt()
        ts  = now.strftime("%-I:%M %p PT") + f"  ·  {now.strftime('%b %-d')}"
    d.text((W-20, y+H_HEADER-16), ts,
           font=_f("light",16), fill=MUTED, anchor="rb")

    y += H_HEADER

    # ── HERO: Temperature + Icon ───────────────────────────────────────────────
    hero_top = y
    tc = _tcol(loc["temp"])

    # Icon — right half, vertically centered
    icon_cx = int(W * 0.78)
    icon_cy = hero_top + H_HERO//2 - 10
    _draw_icon(img, icon_cx, icon_cy, 118, _pick_icon(loc.get("description","")))

    # Giant temperature — left
    tstr = f"{loc['temp']}°"
    # shadow
    d.text((W//2-30+4, hero_top+20), tstr,
           font=_f("black",270), fill=(0,5,12), anchor="mt")
    d.text((W//2-30,   hero_top+18), tstr,
           font=_f("black",270), fill=tc, anchor="mt")

    # Feels like — below temp
    d.text((W//2-30, hero_top+H_HERO-52),
           f"Feels like {loc['feels_like']}°F",
           font=_f("light",26), fill=MUTED, anchor="mt")

    y += H_HERO

    # ── STATS ROW: H/L · Humidity · Wind · UV ─────────────────────────────────
    # Dark separator
    d.rectangle([0,y,W,y+H_STATS], fill=PANEL2)
    d.line([0,y,W,y], fill=BORDER, width=1)
    d.line([0,y+H_STATS,W,y+H_STATS], fill=BORDER, width=1)

    uvc, uvlbl = _uv_info(loc["uv_index"])

    stats = [
        (f"H {loc['temp_high']}°  L {loc['temp_low']}°",
         f"High / Low", WHITE),
        (f"{loc['humidity']}%",   "Humidity",  _hex("#38BDF8")),
        (f"{loc['wind_speed']} mph {loc.get('wind_dir','')}",
         "Wind",        WHITE),
        (f"UV {loc['uv_index']}  {uvlbl}",
         "UV Index",    uvc),
    ]

    col_w = W // len(stats)
    for i,(value,label,color) in enumerate(stats):
        cx2 = i*col_w + col_w//2
        if i > 0:
            d.line([i*col_w,y+12,i*col_w,y+H_STATS-12], fill=BORDER, width=1)
        _ctext(d, cx2, y+10,  value, _f("bold",26),  color)
        _ctext(d, cx2, y+52,  label, _f("light",18), MUTED)

    y += H_STATS

    # ── 7-DAY FORECAST (5 days shown — cleaner) ───────────────────────────────
    if has_fcst:
        d.rectangle([0,y,W,y+H_FCST], fill=(7,16,28))
        d.line([0,y,W,y], fill=BORDER, width=1)
        # "7-DAY" label
        d.text((18,y+10), "FORECAST", font=_f("bold",15), fill=MUTED, anchor="lt")

        days  = (forecast or [])[:5]  # 5 days — roomier
        n     = len(days)
        col_w2 = W // n

        for i,day in enumerate(days):
            cx3   = i*col_w2 + col_w2//2
            kind  = _pick_icon(day.get("description",""))

            if i > 0:
                d.line([i*col_w2,y+10,i*col_w2,y+H_FCST-10], fill=BORDER, width=1)

            # Day
            _ctext(d, cx3, y+14, day.get("day","").upper(), _f("bold",20), TEXT)

            # Icon
            _mini_icon(img, cx3, y+72, 32, kind)

            # Temps side by side
            hi  = day.get("temp_high","")
            lo  = day.get("temp_low","")
            gap = col_w2//5
            _ctext(d, cx3-gap//2, y+110,
                   f"{hi}°" if hi!="" else "—",
                   _f("bold",24), _tcol(hi) if hi!="" else MUTED)
            _ctext(d, cx3+gap//2, y+110,
                   f"{lo}°" if lo!="" else "—",
                   _f("medium",22), _tcol(lo) if lo!="" else MUTED)

            # Precip
            pop = day.get("pop",0)
            if pop >= 20:
                _ctext(d, cx3, y+138, f"{pop}%", _f("light",17), _hex("#60A5FA"))

        y += H_FCST

    # ── FOOTER ────────────────────────────────────────────────────────────────
    d.rectangle([0,y,W,H], fill=(5,11,22))
    d.line([0,y,W,y], fill=BORDER, width=1)
    d.text((W//2, y+12), "@bdgroves  ·  OpenWeatherMap  ·  West Coast Weather Intelligence",
           font=_f("light",16), fill=MUTED, anchor="mt")

    img.save(out, quality=95)
    print(f"  Card: {out}  ({W}×{H})")


# ── 2×2 COMBINED ──────────────────────────────────────────────────────────────
def render_combined(weather_data, forecast_data=None, out="weather_report_k5.png"):
    """2×2 grid — same clean aesthetic, compact per-cell."""
    CW, CH = 1200, 675
    GAP    = 4
    W = CW*2 + GAP;  H = CH*2 + GAP

    canvas = Image.new("RGB", (W,H), (3,8,16))
    positions = [(0,0),(CW+GAP,0),(0,CH+GAP),(CW+GAP,CH+GAP)]

    for i,loc in enumerate(weather_data[:4]):
        tmp = f"/tmp/_cell_{i}.png"
        _render_cell(loc, tmp, CW, CH)
        canvas.paste(Image.open(tmp), positions[i])

    canvas.save(out, quality=95)
    print(f"  Combined: {out}  ({W}×{H})")


def _render_cell(loc, out, W, H):
    """Compact single-cell version for 2×2 grid."""
    has_watch = bool(_watch_reasons(loc))

    img = Image.new("RGB", (W,H), BG)
    d   = ImageDraw.Draw(img)
    for gx in range(0,W,44):
        for gy in range(0,H,44):
            d.ellipse([gx-1,gy-1,gx+1,gy+1], fill=(11,22,40))

    y = 0
    H_WATCH  = 42 if has_watch else 0
    H_HEADER = 74
    H_HERO   = H - H_WATCH - H_HEADER - 80 - 40
    H_STATS  = 80
    H_FOOT   = 40

    if has_watch:
        reasons = _watch_reasons(loc)
        d.rectangle([0,y,W,y+H_WATCH], fill=WATCH_BG)
        d.rectangle([0,y,160,y+H_WATCH], fill=WATCH_DK)
        d.text((12,y+H_WATCH//2), "WEATHER WATCH",
               font=_f("bold",16), fill=WHITE, anchor="lm")
        d.text((168,y+H_WATCH//2), "  ·  ".join(reasons),
               font=_f("reg",14), fill=(255,208,160), anchor="lm")
        y += H_WATCH

    # Header
    d.rectangle([0,y,W,y+H_HEADER], fill=PANEL)
    d.rectangle([0,y,W,y+4], fill=ACC)
    slabel = _station_label(loc["name"], loc["temp"], wind=loc.get("wind_speed",0), low=loc.get("temp_low",99), high=loc.get("temp_high",0), pop=loc.get("pop",0), nws_alerts=loc.get("nws_alerts"))
    d.text((14,y+10), slabel, font=_f("bold",14), fill=ACC, anchor="lt")
    d.text((14,y+28), f"{loc['name']}, {loc['state']}",
           font=_f("black",32), fill=WHITE, anchor="lt")
    cond = loc.get("description","").upper()
    d.text((W-14,y+H_HEADER//2), cond,
           font=_f("bold",18), fill=TEXT, anchor="rm")
    y += H_HEADER

    # Hero
    tc = _tcol(loc["temp"])
    icon_cx = int(W*.78); icon_cy = y + H_HERO//2
    _draw_icon(img, icon_cx, icon_cy, 80, _pick_icon(loc.get("description","")))

    tstr = f"{loc['temp']}°"
    d.text((W//2-24+3, y+12), tstr, font=_f("black",195), fill=(0,5,12), anchor="mt")
    d.text((W//2-24,   y+10), tstr, font=_f("black",195), fill=tc, anchor="mt")
    d.text((W//2-24, y+H_HERO-28),
           f"Feels like {loc['feels_like']}°F",
           font=_f("light",19), fill=MUTED, anchor="mt")
    y += H_HERO

    # Stats
    d.rectangle([0,y,W,y+H_STATS], fill=PANEL2)
    d.line([0,y,W,y], fill=BORDER, width=1)
    d.line([0,y+H_STATS,W,y+H_STATS], fill=BORDER, width=1)

    uvc,uvlbl = _uv_info(loc["uv_index"])
    stats = [
        (f"H {loc['temp_high']}°  L {loc['temp_low']}°", "High / Low", WHITE),
        (f"{loc['humidity']}%", "Humidity", _hex("#38BDF8")),
        (f"{loc['wind_speed']} mph", "Wind", WHITE),
        (f"UV {loc['uv_index']}  {uvlbl}", "UV Index", uvc),
    ]
    cw2 = W//len(stats)
    for i,(value,label,color) in enumerate(stats):
        cx2 = i*cw2 + cw2//2
        if i > 0: d.line([i*cw2,y+10,i*cw2,y+H_STATS-10], fill=BORDER, width=1)
        _ctext(d, cx2, y+8,  value, _f("bold",20), color)
        _ctext(d, cx2, y+44, label, _f("light",14), MUTED)
    y += H_STATS

    # Footer
    d.rectangle([0,y,W,H], fill=(5,11,22))
    d.line([0,y,W,y], fill=BORDER, width=1)
    d.text((W//2,y+10), "@bdgroves  ·  OpenWeatherMap",
           font=_f("light",14), fill=MUTED, anchor="mt")

    img.save(out, quality=95)


# ── PUBLIC API ─────────────────────────────────────────────────────────────────
def create_k5_charts(weather_data, forecast_data=None,
                     report_period="morning", timestamp=""):
    for loc in weather_data:
        slug     = loc["name"].lower().replace(" ","_")
        forecast = (forecast_data or {}).get(loc["name"], [])
        render_card(loc, forecast=forecast, out=f"weather_{slug}_k5.png")
    render_combined(weather_data, forecast_data=forecast_data,
                    out="weather_report_k5.png")
