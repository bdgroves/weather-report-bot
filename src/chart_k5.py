"""
chart_k5.py — K5-style bold broadcast weather cards.

Outputs per station:
    weather_lakewood_k5.png
    weather_groveland_k5.png
    weather_death_valley_k5.png
    weather_reno_k5.png
    weather_report_k5.png  (2x2 combined)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch, Circle, Ellipse, Rectangle, Arc
import numpy as np
from datetime import datetime
import os

# ── THEME ──────────────────────────────────────────────────────────────────────
BG_ALERT = "#B22234"   # K5 red for alert days
BG_MAIN  = "#1A3A5C"   # deep navy for normal days
BG_DARK  = "#0D1F33"   # darker navy
ACC      = "#38BDF8"   # cyan accent
GOLD     = "#FFD60A"   # sunrise gold
WH       = "#FFFFFF"
MUT      = "#A8C4DC"
F        = "DejaVu Sans"

STATION_COLORS = {
    "Lakewood":     "#1A3A5C",
    "Groveland":    "#1A3A5C",
    "Death Valley": "#8B1A1A",
    "Reno":         "#1A3A5C",
}

STATION_LABELS = {
    "Lakewood":     "HOME BASE",
    "Groveland":    "SIERRA FOOTHILLS",
    "Death Valley": "EXTREME CONDITIONS",
    "Reno":         "BIGGEST LITTLE CITY",
}

ALERT_THRESHOLD = {
    "wind_speed": 25,
    "pop": 70,
    "temp_high": 100,
    "temp_low": 20,
}


def _tcol(t):
    for thresh, c in [
        (100,"#FF3333"),(90,"#FF6B35"),(80,"#F78166"),
        (70,"#E3B341"),(60,"#3CB86B"),(50,"#58A6FF"),(32,"#79C0FF"),
    ]:
        if t >= thresh: return c
    return "#B0D8FF"


def _uv_info(u):
    for thresh, c, l in [
        (11,"#A855F7","EXTREME"),(8,"#EF4444","VERY HIGH"),
        (6,"#F97316","HIGH"),(3,"#EAB308","MODERATE"),
    ]:
        if u >= thresh: return c, l
    return "#22C55E", "LOW"


def _pick_icon(desc):
    d = desc.lower()
    if any(w in d for w in ("thunder","storm")):          return "storm"
    if any(w in d for w in ("drizzle","rain","shower")):  return "rain"
    if any(w in d for w in ("snow","sleet","blizzard")):  return "snow"
    if any(w in d for w in ("fog","mist","haze")):        return "fog"
    if any(w in d for w in ("overcast","broken")):        return "cloudy"
    if any(w in d for w in ("scattered","few","partly")): return "partly"
    if any(w in d for w in ("clear","sunny")):            return "sunny"
    return "partly"


def _fmt_time(t):
    return t.lstrip("0") if t else t


def _is_alert(loc):
    return (
        loc["wind_speed"] >= ALERT_THRESHOLD["wind_speed"] or
        loc["pop"] >= ALERT_THRESHOLD["pop"] or
        loc["temp_high"] >= ALERT_THRESHOLD["temp_high"] or
        loc["temp_low"] <= ALERT_THRESHOLD["temp_low"]
    )


def _alert_reason(loc):
    reasons = []
    if loc["pop"] >= ALERT_THRESHOLD["pop"]:       reasons.append(f"HEAVY RAIN  {loc['pop']}%")
    if loc["wind_speed"] >= ALERT_THRESHOLD["wind_speed"]: reasons.append(f"HIGH WINDS  {loc['wind_speed']} MPH")
    if loc["temp_high"] >= ALERT_THRESHOLD["temp_high"]:  reasons.append(f"EXTREME HEAT  {loc['temp_high']}°")
    if loc["temp_low"] <= ALERT_THRESHOLD["temp_low"]:    reasons.append(f"FREEZE WARNING  {loc['temp_low']}°")
    return "  ·  ".join(reasons)


def _station_label(name, temp):
    if name == "Death Valley":
        if temp >= 110: return "EXTREME HEAT WARNING"
        if temp >= 95:  return "DANGEROUS HEAT"
        if temp >= 80:  return "HOT & DRY"
    return STATION_LABELS.get(name, name.upper())


# ── ICON DRAWING ───────────────────────────────────────────────────────────────
def _sun(ax, cx, cy, r, col="#FFD60A", a=1.0):
    ax.add_patch(Circle((cx,cy), r, facecolor=col, zorder=5, alpha=a))
    for ang in np.linspace(0, 360, 9)[:-1]:
        rad = np.radians(ang)
        ax.plot([cx+r*1.35*np.cos(rad), cx+r*1.85*np.cos(rad)],
                [cy+r*1.35*np.sin(rad), cy+r*1.85*np.sin(rad)],
                color=col, lw=3, solid_capstyle="round", zorder=4, alpha=a*.9)


def _cloud(ax, cx, cy, r, col="#C8D8E8", a=1.0):
    for dx,dy,rr in [(0,0,r),(-.65*r,.1*r,.62*r),(.6*r,.05*r,.58*r),(-.2*r,-.35*r,.5*r),(.2*r,-.35*r,.5*r)]:
        ax.add_patch(Ellipse((cx+dx,cy+dy),rr*2.2,rr*1.5,facecolor=col,zorder=5,alpha=a))
    ax.add_patch(Rectangle((cx-r,cy-r*.55),r*2,r*.6,facecolor=col,zorder=4,alpha=a))


def _rain_drops(ax, cx, cy, r, col="#60A5FA"):
    for dx, dy in [(-0.35,0),(0.05,-0.15),(0.4,0.05),(-0.1,0.2)]:
        x0,y0 = cx+dx*r*2, cy+dy*r*2-r*0.8
        ax.plot([x0,x0-0.08*r],[y0,y0-0.55*r],color=col,lw=2.2,
                solid_capstyle="round",zorder=6)


def _draw_icon(ax, cx, cy, r, kind):
    if kind == "sunny":
        _sun(ax, cx, cy, r)
    elif kind == "partly":
        _sun(ax, cx+r*.3, cy+r*.35, r*.68)
        _cloud(ax, cx-r*.1, cy-r*.15, r*.75)
    elif kind in ("cloudy","fog"):
        _cloud(ax, cx, cy, r*.9, col="#A0B8C8")
        _cloud(ax, cx, cy+r*.3, r*.75)
    elif kind == "rain":
        _cloud(ax, cx, cy+r*.2, r*.8)
        _rain_drops(ax, cx, cy, r)
    elif kind == "storm":
        _cloud(ax, cx, cy+r*.2, r*.8, col="#607080")
        _rain_drops(ax, cx, cy, r, col="#93C5FD")
        ax.plot([cx+.1*r,cx-.25*r,cx+.05*r,cx-.3*r],
                [cy-r*.3,cy-r*.75,cy-r*.75,cy-r*1.3],
                color="#FDE047",lw=3,solid_capstyle="round",zorder=7)
    elif kind == "snow":
        _cloud(ax, cx, cy+r*.2, r*.8)
        for dx,dy in [(-0.4,0),(0,0),(0.4,0),(-0.2,-0.35),(0.2,-0.35)]:
            ax.plot([cx+dx*r*1.2],[cy+dy*r*1.2-r*0.5],"o",
                    color="white",ms=4,zorder=6)


# ── FORECAST STRIP ─────────────────────────────────────────────────────────────
def _forecast_strip(ax, forecast, bg):
    """Draw 5-day mini forecast across bottom of card."""
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.add_patch(Rectangle((0,0),100,100,facecolor=BG_DARK,alpha=0.6))

    days = forecast[:5] if forecast else []
    n = len(days)
    if n == 0:
        return

    col_w = 100 / n
    for i, day in enumerate(days):
        x = i * col_w
        cx = x + col_w/2

        # Day label
        ax.text(cx, 88, day.get("day","").upper(), ha="center", va="center",
                fontsize=7, color=MUT, fontfamily=F, fontweight="bold")

        # Mini icon
        ia = plt.axes([0,0,0,0])  # placeholder — we draw inline
        kind = _pick_icon(day.get("description",""))
        # Simple dot-based mini icons
        if kind == "sunny":
            ax.add_patch(Circle((cx, 68), 7, facecolor="#FFD60A", zorder=5))
        elif kind == "partly":
            ax.add_patch(Circle((cx+2, 71), 5, facecolor="#FFD60A", zorder=4))
            ax.add_patch(Ellipse((cx-1,66),14,9,facecolor="#A0B8C8",zorder=5))
        elif kind in ("cloudy","fog"):
            ax.add_patch(Ellipse((cx,68),16,10,facecolor="#607898",zorder=5))
        elif kind in ("rain","storm"):
            ax.add_patch(Ellipse((cx,70),16,10,facecolor="#607898",zorder=5))
            for dx in [-4,0,4]:
                ax.plot([cx+dx,cx+dx-1],[62,57],color="#60A5FA",lw=1.5,zorder=6)
        elif kind == "snow":
            ax.add_patch(Ellipse((cx,70),16,10,facecolor="#607898",zorder=5))
            for dx in [-4,0,4]:
                ax.plot([cx+dx],[61],"o",color="white",ms=2.5,zorder=6)

        # Hi / Lo
        hi = day.get("temp_high", "")
        lo = day.get("temp_low", "")
        ax.text(cx-4, 50, f"{hi}°" if hi != "" else "--",
                ha="center", va="center", fontsize=9,
                color=_tcol(hi) if hi != "" else MUT,
                fontfamily=F, fontweight="bold")
        ax.text(cx+4, 50, f"{lo}°" if lo != "" else "--",
                ha="center", va="center", fontsize=8,
                color=_tcol(lo) if lo != "" else MUT, fontfamily=F)

        # Precip chance
        pop = day.get("pop", 0)
        if pop >= 20:
            ax.text(cx, 33, f"☔ {pop}%", ha="center", fontsize=7,
                    color="#60A5FA", fontfamily=F)

        # Divider
        if i > 0:
            ax.plot([x,x],[10,95],color="#1A3050",lw=0.8,alpha=0.6)


# ── MAIN K5 CARD ───────────────────────────────────────────────────────────────
def render_k5_card(loc, forecast=None, out="weather_k5.png"):
    alert     = _is_alert(loc)
    bg        = "#8B1A1A" if loc["name"] == "Death Valley" and loc["temp"] >= 90 else STATION_COLORS.get(loc["name"], BG_MAIN)
    icon_type = _pick_icon(loc.get("description",""))
    slabel    = _station_label(loc["name"], loc["temp"])
    tc        = _tcol(loc["temp"])
    _, uvlbl  = _uv_info(loc["uv_index"])
    has_forecast = forecast and len(forecast) > 0

    DPI = 150
    fig = plt.figure(figsize=(8.0, 4.5), dpi=DPI, facecolor=bg)

    # ── Background gradient effect
    ba = fig.add_axes([0,0,1,1], zorder=0)
    ba.set_xlim(0,1); ba.set_ylim(0,1); ba.axis("off")
    ba.add_patch(Rectangle((0,0),1,1, facecolor=bg))
    ba.add_patch(Ellipse((.85,.5),1.0,.9, facecolor=BG_DARK, alpha=.45, zorder=1))
    ba.add_patch(Ellipse((.12,.85),.6,.5, facecolor=BG_DARK, alpha=.25, zorder=1))

    # ── FIRST ALERT banner (if alert conditions)
    if alert:
        ab = fig.add_axes([0,.91,1,.09], zorder=20)
        ab.set_xlim(0,1); ab.set_ylim(0,1); ab.axis("off")
        ab.add_patch(Rectangle((0,0),1,1, facecolor="#CC0000"))
        ab.add_patch(Rectangle((0,0),.25,1, facecolor="#AA0000"))
        ab.text(.02,.5,"⚠ FIRST ALERT", ha="left", va="center",
                fontsize=9, color=WH, fontweight="bold", fontfamily=F)
        ab.text(.28,.5, _alert_reason(loc), ha="left", va="center",
                fontsize=8.5, color=WH, fontfamily=F)
        header_top = .91
    else:
        header_top = 1.0

    # ── HEADER BAR
    hh = .11
    ha = fig.add_axes([0, header_top-hh, 1, hh], zorder=15)
    ha.set_xlim(0,1); ha.set_ylim(0,1); ha.axis("off")
    ha.add_patch(Rectangle((0,0),1,1, facecolor=BG_DARK, alpha=.85))
    ha.add_patch(Rectangle((0,.85),1,.15, facecolor=ACC, alpha=.9))
    ha.text(.018,.60, slabel, fontsize=8, color=ACC,
            fontweight="bold", fontfamily=F, va="center")
    ha.text(.018,.18, f"{loc['name']}, {loc['state']}",
            fontsize=16, color=WH, fontweight="bold", fontfamily=F, va="center")

    # Condition badge — center
    ha.add_patch(FancyBboxPatch((.35,.08),.30,.84,
                                 boxstyle="round,pad=0.02",
                                 facecolor="#0A1C30", edgecolor=ACC, lw=1.5, zorder=5))
    ha.text(.50,.50, loc["description"].upper(),
            ha="center", va="center", fontsize=8.5,
            color=WH, fontweight="bold", fontfamily=F, zorder=6)

    # Timestamp right
    now = datetime.now()
    ts = now.strftime("%I:%M %p").lstrip("0") + f"  ·  {now.strftime('%b')} {now.day}"
    ha.text(.988,.50, ts, ha="right", va="center",
            fontsize=8, color=MUT, fontfamily=F)

    # ── FORECAST STRIP (bottom)
    forecast_h = .20 if has_forecast else 0
    fs_bottom  = .0

    if has_forecast:
        fa = fig.add_axes([0, fs_bottom, 1, forecast_h], zorder=10)
        _forecast_strip(fa, forecast, bg)
        body_bottom = forecast_h
    else:
        body_bottom = 0.0

    # ── BODY
    body_top    = header_top - hh
    body_height = body_top - body_bottom
    body = fig.add_axes([0, body_bottom, 1, body_height], zorder=8)
    body.set_xlim(0,100); body.set_ylim(0,100); body.axis("off")

    # Left half — ICON + TEMP
    # Big icon
    icon_ax = fig.add_axes([.02, body_bottom + body_height*.42,
                             .32, body_height*.52], zorder=9)
    icon_ax.set_xlim(-1.5,1.5); icon_ax.set_ylim(-1.5,1.5); icon_ax.axis("off")
    _draw_icon(icon_ax, 0, 0, 1.0, icon_type)

    # Giant temperature
    body.text(22, 54, f"{loc['temp']}°",
              ha="center", va="center",
              fontsize=88, color=tc, fontfamily=F, fontweight="bold",
              path_effects=[pe.withStroke(linewidth=8, foreground=BG_DARK)])

    # Feels like
    body.text(22, 22, f"FEELS LIKE  {loc['feels_like']}°F",
              ha="center", va="center", fontsize=9, color=MUT,
              fontfamily=F, fontweight="bold")

    # Hi / Lo — big and bold like K5
    body.add_patch(FancyBboxPatch((1,8),(40),(13),
                                   boxstyle="round,pad=0.5",
                                   facecolor=BG_DARK, edgecolor="#1A3050",
                                   alpha=0.7, lw=1.2, zorder=4))
    body.plot([21,21],[9,20], color="#1A3050", lw=1.2, zorder=5)
    body.text(11, 14.5, f"H  {loc['temp_high']}°",
              ha="center", va="center", fontsize=14,
              color=_tcol(loc["temp_high"]), fontfamily=F, fontweight="bold", zorder=6)
    body.text(31, 14.5, f"L  {loc['temp_low']}°",
              ha="center", va="center", fontsize=14,
              color=_tcol(loc["temp_low"]), fontfamily=F, fontweight="bold", zorder=6)

    # Right half — KPI grid
    # Vertical divider
    body.plot([48,48],[2,98], color="#1A3050", lw=1.0, alpha=0.6)

    kpis = [
        ("💧", "HUMIDITY",   f"{loc['humidity']}%",       ACC),
        ("💨", "WIND",       f"{loc['wind_speed']} mph {loc['wind_dir']}", WH),
        ("🌞", "UV INDEX",   f"{loc['uv_index']}  {uvlbl}", _uv_info(loc['uv_index'])[0]),
        ("☔", "PRECIP",     f"{loc['pop']}%",            "#60A5FA"),
        ("☁️", "CLOUDS",     f"{loc['cloud_cover']}%",    MUT),
        ("👁", "VISIBILITY", f"{loc['visibility']} mi",   WH),
    ]

    cols = [55, 78]
    rows = [82, 55, 28]
    for idx, (emoji, label, value, color) in enumerate(kpis):
        col = idx % 2
        row = idx // 2
        cx  = cols[col]
        cy  = rows[row]

        body.add_patch(FancyBboxPatch((cx-13, cy-14),(26),(17),
                                       boxstyle="round,pad=0.5",
                                       facecolor=BG_DARK, edgecolor="#1A3050",
                                       alpha=0.7, lw=0.8, zorder=4))
        body.text(cx, cy-3,  label, ha="center", fontsize=6,
                  color=MUT, fontfamily=F, zorder=6)
        body.text(cx, cy-10, value, ha="center", fontsize=9.5,
                  color=color, fontweight="bold", fontfamily=F, zorder=6)

    # Sunrise / Sunset
    body.add_patch(FancyBboxPatch((49,5),(48),(13),
                                   boxstyle="round,pad=0.5",
                                   facecolor=BG_DARK, edgecolor="#1A3050",
                                   alpha=0.7, lw=0.8, zorder=4))
    body.plot([73,73],[6,17], color="#1A3050", lw=0.8, zorder=5)
    body.text(61, 13.5, f"🌅 {_fmt_time(loc['sunrise'])}",
              ha="center", fontsize=8.5, color=GOLD,
              fontweight="bold", fontfamily=F, zorder=6)
    body.text(85, 13.5, f"🌇 {_fmt_time(loc['sunset'])}",
              ha="center", fontsize=8.5, color="#F97316",
              fontweight="bold", fontfamily=F, zorder=6)

    # Branding
    body.text(99, 1, "@bdgroves  ·  OpenWeatherMap",
              ha="right", va="bottom", fontsize=5.5,
              color="#2A3F55", fontfamily=F)

    plt.savefig(out, dpi=DPI, bbox_inches="tight",
                facecolor=bg, edgecolor="none", pad_inches=0.02)
    plt.close(fig)
    print(f"  K5 card saved: {out}")


def render_k5_combined(weather_data, forecast_data=None, out="weather_report_k5.png"):
    """2x2 grid of K5 cards."""
    DPI = 150
    fig = plt.figure(figsize=(16.0, 9.0), dpi=DPI, facecolor="#050D1A")

    positions = [(0,.5,.5,.5),(0.5,.5,.5,.5),(0,0,.5,.5),(0.5,0,.5,.5)]

    for i, loc in enumerate(weather_data[:4]):
        x0, y0, w, h = positions[i]
        sub = fig.add_axes([x0+.005, y0+.005, w-.010, h-.010])
        sub.set_xlim(0,1); sub.set_ylim(0,1); sub.axis("off")

        bg = STATION_COLORS.get(loc["name"], BG_MAIN)
        if loc["name"] == "Death Valley" and loc["temp"] >= 90:
            bg = "#8B1A1A"

        sub.add_patch(Rectangle((0,0),1,1, facecolor=bg))
        sub.add_patch(Ellipse((.85,.5),1.0,.9, facecolor=BG_DARK, alpha=.4))

        tc = _tcol(loc["temp"])
        icon_type = _pick_icon(loc.get("description",""))
        slabel = _station_label(loc["name"], loc["temp"])

        # Header strip
        sub.add_patch(Rectangle((0,.88),1,.12, facecolor=BG_DARK, alpha=.9))
        sub.add_patch(Rectangle((0,.96),1,.04, facecolor=ACC, alpha=.8))
        sub.text(.02,.935, slabel, fontsize=6, color=ACC,
                 fontweight="bold", fontfamily=F, va="center", transform=sub.transAxes)
        sub.text(.02,.895, f"{loc['name']}, {loc['state']}",
                 fontsize=11, color=WH, fontweight="bold",
                 fontfamily=F, va="center", transform=sub.transAxes)
        sub.text(.98,.92, loc["description"].upper(),
                 ha="right", fontsize=7, color=MUT,
                 fontfamily=F, va="center", transform=sub.transAxes)

        # Icon (left side)
        ia = fig.add_axes([x0+.01, y0+h*.38, w*.28, h*.48])
        ia.set_xlim(-1.5,1.5); ia.set_ylim(-1.5,1.5); ia.axis("off")
        _draw_icon(ia, 0, 0, 1.0, icon_type)

        # Giant temp
        sub.text(.35,.54, f"{loc['temp']}°",
                 ha="center", va="center",
                 fontsize=62, color=tc, fontfamily=F, fontweight="bold",
                 transform=sub.transAxes,
                 path_effects=[pe.withStroke(linewidth=6, foreground=BG_DARK)])

        # H/L
        sub.text(.26,.25, f"H {loc['temp_high']}°",
                 ha="center", fontsize=12,
                 color=_tcol(loc["temp_high"]), fontfamily=F, fontweight="bold",
                 transform=sub.transAxes)
        sub.text(.44,.25, f"L {loc['temp_low']}°",
                 ha="center", fontsize=12,
                 color=_tcol(loc["temp_low"]), fontfamily=F, fontweight="bold",
                 transform=sub.transAxes)

        # Right KPIs
        kpis = [
            (f"💧 {loc['humidity']}%",    .72, .78),
            (f"💨 {loc['wind_speed']} mph", .72, .62),
            (f"☔ {loc['pop']}%",          .72, .46),
            (f"🌞 UV {loc['uv_index']}",   .72, .30),
            (f"🌅 {_fmt_time(loc['sunrise'])}  🌇 {_fmt_time(loc['sunset'])}", .72, .14),
        ]
        for text, tx, ty in kpis:
            sub.text(tx, ty, text, ha="left", fontsize=9,
                     color=WH, fontfamily=F, transform=sub.transAxes)

        # Alert badge
        if _is_alert(loc):
            sub.add_patch(FancyBboxPatch((.55,.04),(.42),(.10),
                                          boxstyle="round,pad=0.01",
                                          facecolor="#CC0000", zorder=10,
                                          transform=sub.transAxes))
            sub.text(.76,.09, "⚠ FIRST ALERT",
                     ha="center", va="center", fontsize=7.5,
                     color=WH, fontweight="bold", fontfamily=F,
                     transform=sub.transAxes, zorder=11)

    plt.savefig(out, dpi=DPI, bbox_inches="tight",
                facecolor="#050D1A", edgecolor="none", pad_inches=0.04)
    plt.close(fig)
    print(f"  K5 combined saved: {out}")


def create_k5_charts(weather_data, forecast_data=None, report_period="morning", timestamp=""):
    """Generate all K5 cards. Call from main.py alongside existing chart."""
    for loc in weather_data:
        slug = loc["name"].lower().replace(" ", "_")
        forecast = (forecast_data or {}).get(loc["name"], [])
        render_k5_card(loc, forecast=forecast, out=f"weather_{slug}_k5.png")
    render_k5_combined(weather_data, forecast_data=forecast_data, out="weather_report_k5.png")
