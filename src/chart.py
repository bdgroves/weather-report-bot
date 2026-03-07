"""
chart.py  —  Broadcast-style per-station weather cards.
Drop-in replacement. Same public signature as original.

Outputs:
    weather_report.png        <- 2x2 combined card (posted to social)
    weather_lakewood.png
    weather_groveland.png
    weather_death_valley.png
    weather_reno.png
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch, Circle, Ellipse, Rectangle
import numpy as np
from datetime import datetime
import os

# ── THEME ─────────────────────────────────────────────────────────────────────
BG   = "#050D1A"
HDR  = "#060E1C"
ACC  = "#38BDF8"
ACC2 = "#0EA5E9"
MUT  = "#8B9DB5"
DIV  = "#1A3050"
WH   = "#EDF3FA"
F    = "DejaVu Sans"

STATION_LABELS = {
    "Lakewood":    "HOME BASE",
    "Groveland":   "SIERRA FOOTHILLS",
    "Death Valley":"DEATH VALLEY, CA",
    "Reno":        "BIGGEST LITTLE CITY",
}

# ── HELPERS ───────────────────────────────────────────────────────────────────
def _fmt_time(t: str) -> str:
    """Strip leading zero: '06:10 AM' -> '6:10 AM'."""
    return t.lstrip("0") if t else t

def _now_str() -> str:
    """Windows-safe formatted timestamp."""
    n = datetime.now()
    return n.strftime("%I:%M %p").lstrip("0") + f"  .  {n.strftime('%a %b')} {n.day}, {n.year}"

def _pick_icon(desc: str) -> str:
    d = desc.lower()
    if any(w in d for w in ("thunder", "storm")):           return "rain"
    if any(w in d for w in ("drizzle", "rain", "shower")):  return "rain"
    if any(w in d for w in ("snow", "sleet", "blizzard")):  return "snow"
    if any(w in d for w in ("fog", "mist", "haze", "smoke")): return "cloudy"
    if any(w in d for w in ("overcast", "overcast clouds")): return "cloudy"
    if any(w in d for w in ("broken", "mostly cloudy")):    return "cloudy"
    if any(w in d for w in ("scattered", "few clouds", "partial", "partly")): return "partly"
    if any(w in d for w in ("clear", "sunny")):             return "sunny"
    return "partly"

def _station_label(name: str, temp: int) -> str:
    """Dynamic label — base for most, temperature-reactive for Death Valley."""
    if name == "Death Valley":
        if temp >= 110: return "EXTREME HEAT WARNING"
        if temp >= 95:  return "DANGEROUS HEAT"
        if temp >= 80:  return "HOT & DRY"
        return "DEATH VALLEY, CA"
    return STATION_LABELS.get(name, name.upper())

def _tcol(t):
    for thresh, c in [
        (100,"#FF3333"),(90,"#FF6B35"),(80,"#F78166"),
        (70, "#E3B341"),(60,"#3CB86B"),(50,"#58A6FF"),(32,"#79C0FF"),
    ]:
        if t >= thresh: return c
    return "#B0D8FF"

def _uv_info(u):
    for thresh, c, l in [
        (11,"#A855F7","EXTREME"),(8,"#EF4444","VERY HIGH"),
        (6, "#F97316","HIGH"),  (3,"#EAB308","MODERATE"),
    ]:
        if u >= thresh: return c, l
    return "#22C55E", "LOW"

def _compass_to_deg(d: str) -> float:
    m = {"N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,
         "SE":135,"SSE":157.5,"S":180,"SSW":202.5,"SW":225,"WSW":247.5,
         "W":270,"WNW":292.5,"NW":315,"NNW":337.5}
    return m.get(str(d).upper(), 0)

# ── ICONS ─────────────────────────────────────────────────────────────────────
def _sun(ax, cx, cy, r, col="#FFD60A", a=1.0):
    ax.add_patch(Circle((cx,cy), r, facecolor=col, zorder=5, alpha=a))
    for ang in np.linspace(0, 360, 9)[:-1]:
        rad = np.radians(ang)
        ax.plot([cx+r*1.38*np.cos(rad), cx+r*1.88*np.cos(rad)],
                [cy+r*1.38*np.sin(rad), cy+r*1.88*np.sin(rad)],
                color=col, lw=2.2, solid_capstyle="round", zorder=4, alpha=a*.92)

def _cloud(ax, cx, cy, r, col="#8099B0", a=1.0):
    for px,py,pr in [(cx-r*.38,cy-.04*r,r*.50),(cx+r*.38,cy-.04*r,r*.50),(cx,cy+.22*r,r*.62)]:
        ax.add_patch(Circle((px,py), pr, facecolor=col, zorder=5, alpha=a))
    ax.add_patch(FancyBboxPatch((cx-r*.82,cy-r*.20), r*1.64, r*.32,
                                 boxstyle="round,pad=0.01", facecolor=col, zorder=4, alpha=a))

def _draw_icon(ax, cx, cy, r, kind):
    if   kind == "sunny":
        _sun(ax, cx, cy, r)
    elif kind == "partly":
        _sun(ax, cx+r*.30, cy+r*.28, r*.62, a=.95)
        _cloud(ax, cx-r*.08, cy-r*.10, r*.88, col="#9BAFC0")
    elif kind == "cloudy":
        _cloud(ax, cx+r*.22, cy+r*.18, r*.65, col="#6B8099", a=.7)
        _cloud(ax, cx, cy, r, col="#9BAFC0")
    elif kind == "snow":
        _cloud(ax, cx, cy+r*.22, r*.85, col="#7090A0")
        for dx,dy in [(-0.35,-0.45),(0,-0.62),(0.35,-0.45),(-0.18,-0.80),(0.18,-0.80)]:
            ax.add_patch(Circle((cx+dx*r, cy+dy*r), r*.09, facecolor="#A8D8FF", zorder=6))
    elif kind == "rain":
        _cloud(ax, cx, cy+r*.25, r, col="#5D7080")
        for dx,dy in [(-0.38,-0.52),(0,-0.70),(0.38,-0.52),(-0.19,-0.88),(0.19,-0.88)]:
            ax.plot([cx+dx*r, cx+dx*r-.04*r],[cy+dy*r, cy+dy*r-.22*r],
                    color="#58A6FF", lw=2.0, solid_capstyle="round", zorder=6, alpha=.9)

# ── GAUGE ─────────────────────────────────────────────────────────────────────
def _gauge(ax, value, vmin, vmax, color, label, unit=""):
    r = 0.85
    tb = np.linspace(np.pi, 0, 120)
    frac = np.clip((value-vmin)/(vmax-vmin), 0, 1)
    tv   = np.linspace(np.pi, np.pi - frac*np.pi, 120)
    ax.plot(r*np.cos(tb), r*np.sin(tb), color=DIV,   lw=10, solid_capstyle="round", zorder=3)
    ax.plot(r*np.cos(tv), r*np.sin(tv), color=color, lw=10, solid_capstyle="round", zorder=4)
    ax.text(0, 0.08, f"{value}{unit}", ha="center", va="center",
            fontsize=13, fontweight="bold", color=WH, fontfamily=F, zorder=5)
    ax.text(0, -0.50, label, ha="center", fontsize=7, color=MUT, fontfamily=F, zorder=5)

# ── COMPASS ───────────────────────────────────────────────────────────────────
def _compass(ax, deg, mph, dirstr):
    r = 1.0
    ax.add_patch(Circle((0,0), r,     fill=False, edgecolor=DIV,       lw=2.5, zorder=3))
    ax.add_patch(Circle((0,0), r*.86, facecolor=BG, edgecolor="#182E48", lw=1,   zorder=3))
    for a, l in [(90,"N"),(270,"S"),(0,"E"),(180,"W")]:
        rad = np.radians(a)
        ax.text(r*.67*np.cos(rad), r*.67*np.sin(rad), l,
                ha="center", va="center", fontsize=8, fontweight="bold",
                color=MUT, fontfamily=F, zorder=6)
    rad  = np.radians(90 - deg)
    tip  = ( r*.54*np.cos(rad),  r*.54*np.sin(rad))
    tail = (-r*.44*np.cos(rad), -r*.44*np.sin(rad))
    ax.annotate("", xy=tip, xytext=tail,
                arrowprops=dict(arrowstyle="->", color=ACC, lw=3.0, mutation_scale=20), zorder=7)
    ax.text(0, -r*1.70, f"{mph} mph  {dirstr}", ha="center", va="top",
            fontsize=8.5, color=ACC, fontweight="bold", fontfamily=F)

# ── TEMP RANGE BAR ────────────────────────────────────────────────────────────
def _temp_bar(ax, temp, lo, hi, x=8, y=11, w=84, h=7):
    """Gradient bar showing where current temp sits between lo and hi."""
    ax.add_patch(FancyBboxPatch((x,y),(w),(h),
                                 boxstyle="round,pad=0.4", facecolor=DIV, zorder=4))
    span  = max(hi - lo, 1)
    steps = 40
    for s in range(steps):
        frac = s / steps
        rv = int(max(0, min(255, 88  + frac*(255-88))))
        gv = int(max(0, min(255, 166 + frac*(107-166))))
        bv = int(max(0, min(255, 255 + frac*(53 -255))))
        ax.add_patch(Rectangle((x + w*frac, y), w/steps+0.5, h,
                                facecolor=f"#{rv:02x}{gv:02x}{bv:02x}",
                                zorder=5, alpha=0.55))
    pos = x + w * np.clip((temp - lo) / span, 0.02, 0.98)
    ax.plot([pos, pos], [y-1.2, y+h+1.2], color=WH, lw=2.2, zorder=7)
    ax.add_patch(Circle((pos, y + h/2), 1.8, facecolor=WH, zorder=8))

# ── SINGLE CARD ───────────────────────────────────────────────────────────────
def _render_card(loc: dict, out: str):
    wind_deg  = _compass_to_deg(loc.get("wind_dir", "N"))
    icon_type = _pick_icon(loc.get("description", ""))
    slabel    = _station_label(loc["name"], loc["temp"])
    uvc, uvlbl = _uv_info(loc["uv_index"])
    tc        = _tcol(loc["temp"])

    DPI = 150
    fig = plt.figure(figsize=(12.0, 6.75), dpi=DPI, facecolor=BG)

    # Background glow
    ba = fig.add_axes([0,0,1,1], zorder=0)
    ba.set_xlim(0,1); ba.set_ylim(0,1); ba.axis("off")
    ba.add_patch(Rectangle((0,0),1,1, facecolor=BG))
    ba.add_patch(Ellipse((.09,.89),.52,.34, facecolor="#0F2840", alpha=.40, zorder=1))

    # ── Header ────────────────────────────────────────────────────────────────
    ha = fig.add_axes([0,.865,1,.135], zorder=10)
    ha.set_xlim(0,1); ha.set_ylim(0,1); ha.axis("off")
    ha.add_patch(Rectangle((0,0),1,1, facecolor=HDR))
    ha.add_patch(Rectangle((0,.90),1,.10, facecolor=ACC))
    ha.add_patch(Rectangle((0,0),.008,1,  facecolor=ACC))
    ha.text(.021,.74, slabel, fontsize=8.5, color=ACC,
            fontweight="bold", fontfamily=F, va="center")
    ha.text(.021,.28, f"{loc['name']}, {loc['state']}", fontsize=17,
            color=WH, fontweight="bold", fontfamily=F, va="center")
    ha.add_patch(FancyBboxPatch((.375,.12),.250,.76, boxstyle="round,pad=0.02",
                                 facecolor="#0A1C30", edgecolor=ACC2, lw=1.5, zorder=5))
    ha.text(.50,.50, loc["description"].upper(), ha="center", va="center",
            fontsize=9.5, color=WH, fontweight="bold", fontfamily=F, zorder=6)
    ha.text(.988,.50, _now_str(), ha="right", va="center",
            fontsize=8.5, color=MUT, fontfamily=F)

    # ── Ticker ────────────────────────────────────────────────────────────────
    ta = fig.add_axes([0,0,1,.060], zorder=10)
    ta.set_xlim(0,1); ta.set_ylim(0,1); ta.axis("off")
    ta.add_patch(Rectangle((0,0),1,1, facecolor=HDR))
    ta.add_patch(Rectangle((0,.76),1,.24, facecolor=ACC2, alpha=.85))
    ticker_items = [
        f"SUNRISE  {_fmt_time(loc['sunrise'])}",
        f"SUNSET  {_fmt_time(loc['sunset'])}",
        f"DEW PT  {loc['dew_point']}\u00b0F",
        f"PRESSURE  {loc['pressure']} hPa",
        f"CLOUDS  {loc['cloud_cover']}%",
        f"VIS  {loc['visibility']} mi",
        "@bdgroves",
    ]
    ta.text(.50,.38, "   |   ".join(ticker_items), ha="center", va="center",
            fontsize=7.8, color=WH, fontweight="bold", fontfamily=F, zorder=5)

    # ── Body panels ───────────────────────────────────────────────────────────
    BY, BH = .060, .805
    L0,L1  = .000,.305
    M0,M1  = .308,.665
    R0,R1  = .668,1.00

    # Divider lines between panels
    for xd in [L1+.001, M1+.001]:
        d = fig.add_axes([xd,BY,.003,BH], zorder=5)
        d.set_xlim(0,1); d.set_ylim(0,1); d.axis("off")
        d.add_patch(Rectangle((0,0),1,1, facecolor=DIV))

    # ── LEFT: temp + icon ─────────────────────────────────────────────────────
    la = fig.add_axes([L0,BY,L1-L0,BH], zorder=6, facecolor="#070D1B")
    la.set_xlim(0,100); la.set_ylim(0,100); la.axis("off")

    ia = fig.add_axes([L0+.018, BY+BH*.565, (L1-L0)-.030, BH*.385], zorder=7)
    ia.set_xlim(-1.4,1.4); ia.set_ylim(-1.4,1.4); ia.axis("off")
    _draw_icon(ia, 0, 0, 0.84, icon_type)

    la.text(50, 52, f"{loc['temp']}\u00b0",
            ha="center", va="center", fontsize=72, color=tc,
            fontfamily=F, fontweight="bold",
            path_effects=[pe.withStroke(linewidth=6, foreground=BG)])
    la.text(50, 37, f"FEELS LIKE  {loc['feels_like']}\u00b0F",
            ha="center", va="center", fontsize=9, color=MUT,
            fontfamily=F, fontweight="bold")

    # Hi/Lo box
    la.add_patch(FancyBboxPatch((5,25),(90),(10),
                                 boxstyle="round,pad=0.5",
                                 facecolor="#0B1C2E", edgecolor=DIV, lw=1.2, zorder=4))
    la.plot([50,50],[26,34], color=DIV, lw=1.2, zorder=5)
    la.text(26, 30.5, f"H  {loc['temp_high']}\u00b0",
            ha="center", va="center", fontsize=12,
            color=_tcol(loc["temp_high"]), fontfamily=F, fontweight="bold", zorder=6)
    la.text(74, 30.5, f"L  {loc['temp_low']}\u00b0",
            ha="center", va="center", fontsize=12,
            color=_tcol(loc["temp_low"]), fontfamily=F, fontweight="bold", zorder=6)

    # Temp range bar
    la.text(50, 21, "TODAY'S  RANGE", ha="center", fontsize=7.5, color=MUT, fontfamily=F)
    _temp_bar(la, loc["temp"], loc["temp_low"], loc["temp_high"])
    la.text(10, 6.5, f"{loc['temp_low']}\u00b0", fontsize=7.5,
            color=_tcol(loc["temp_low"]), fontfamily=F, fontweight="bold")
    la.text(90, 6.5, f"{loc['temp_high']}\u00b0", ha="right", fontsize=7.5,
            color=_tcol(loc["temp_high"]), fontfamily=F, fontweight="bold")
    la.text(50, 2.5, f"NOW: {loc['temp']}\u00b0F", ha="center", fontsize=7,
            color=WH, fontfamily=F)

    # ── MID: gauges + compass + KPIs ─────────────────────────────────────────
    ma = fig.add_axes([M0,BY,M1-M0,BH], zorder=6, facecolor="#060C18")
    ma.set_xlim(0,100); ma.set_ylim(0,100); ma.axis("off")
    ma.text(50, 96.5, "CURRENT  CONDITIONS", ha="center", va="top",
            fontsize=8.5, color=ACC, fontweight="bold", fontfamily=F)

    g1 = fig.add_axes([M0+.005, BY+BH*.57, (M1-M0)*.46, BH*.36], zorder=7)
    g1.set_xlim(-1.3,1.3); g1.set_ylim(-1.1,1.0); g1.axis("off")
    _gauge(g1, loc["humidity"], 0, 100, ACC, "HUMIDITY", "%")

    g2 = fig.add_axes([M0+(M1-M0)*.50, BY+BH*.57, (M1-M0)*.46, BH*.36], zorder=7)
    g2.set_xlim(-1.3,1.3); g2.set_ylim(-1.1,1.0); g2.axis("off")
    _gauge(g2, loc["uv_index"], 0, 11, uvc, "UV  INDEX", "")
    g2.text(0, -1.06, uvlbl, ha="center", va="top",
            fontsize=7, color=uvc, fontweight="bold", fontfamily=F)

    ca = fig.add_axes([M0+.012, BY+BH*.06, (M1-M0)*.44, BH*.46], zorder=7)
    ca.set_xlim(-1.9,1.9); ca.set_ylim(-1.9,1.9); ca.axis("off")
    _compass(ca, wind_deg, loc["wind_speed"], loc["wind_dir"])

    kpi_ax = fig.add_axes([M0+(M1-M0)*.50, BY+BH*.04, (M1-M0)*.48, BH*.50], zorder=7)
    kpi_ax.set_xlim(0,100); kpi_ax.set_ylim(0,100); kpi_ax.axis("off")
    for lbl, val, ky in [
        ("HUMIDITY",   f"{loc['humidity']}%",        97),
        ("WIND",       f"{loc['wind_speed']} mph",   77),
        ("VISIBILITY", f"{loc['visibility']} mi",    57),
        ("DEW POINT",  f"{loc['dew_point']}\u00b0F", 37),
        ("PRESSURE",   f"{loc['pressure']} hPa",     17),
    ]:
        kpi_ax.add_patch(FancyBboxPatch((1,ky-18),(98),(17.5),
                                         boxstyle="round,pad=0.8",
                                         facecolor="#0B1C2E", edgecolor=DIV, lw=0.9, zorder=4))
        kpi_ax.text(50, ky-5,  lbl, ha="center", va="center",
                    fontsize=6.5, color=MUT, fontfamily=F, zorder=6)
        kpi_ax.text(50, ky-13, val, ha="center", va="center",
                    fontsize=11, color=WH, fontweight="bold", fontfamily=F, zorder=6)

    # ── RIGHT: sky & atmosphere ───────────────────────────────────────────────
    ra = fig.add_axes([R0,BY,R1-R0,BH], zorder=6, facecolor="#070D1B")
    ra.set_xlim(0,100); ra.set_ylim(0,100); ra.axis("off")
    ra.text(50, 96.5, "SKY  &  ATMOSPHERE", ha="center", va="top",
            fontsize=8.5, color=ACC, fontweight="bold", fontfamily=F, clip_on=False)

    # Precip bar
    ra.text(50, 89.5, "PRECIP  CHANCE", ha="center", fontsize=7.5, color=MUT, fontfamily=F)
    ra.add_patch(FancyBboxPatch((6,80),(88),(8),
                                 boxstyle="round,pad=0.4", facecolor=DIV, zorder=4))
    if loc["pop"] > 0:
        ra.add_patch(FancyBboxPatch((6,80),(88*loc["pop"]/100),(8),
                                     boxstyle="round,pad=0.4", facecolor=ACC, zorder=5))
    ra.text(50, 75.5, f"{loc['pop']}%", ha="center", fontsize=14,
            color=ACC, fontweight="bold", fontfamily=F, zorder=10)

    # Cloud cover bar
    ra.text(50, 70, "CLOUD  COVER", ha="center", fontsize=7.5, color=MUT, fontfamily=F)
    ra.add_patch(FancyBboxPatch((6,61),(88),(8),
                                 boxstyle="round,pad=0.4", facecolor=DIV, zorder=4))
    if loc["cloud_cover"] > 0:
        ra.add_patch(FancyBboxPatch((6,61),(88*loc["cloud_cover"]/100),(8),
                                     boxstyle="round,pad=0.4", facecolor="#607898", zorder=5))
    ra.text(50, 57, f"{loc['cloud_cover']}%", ha="center", fontsize=14,
            color=WH if loc["cloud_cover"] >= 50 else MUT,
            fontweight="bold", fontfamily=F)

    # Sunrise / Sunset side by side
    for bx, label, val, col in [
        (4,  "SUNRISE", _fmt_time(loc["sunrise"]), "#FFD60A"),
        (52, "SUNSET",  _fmt_time(loc["sunset"]),  "#F97316"),
    ]:
        ra.add_patch(FancyBboxPatch((bx,46),(44),(10),
                                     boxstyle="round,pad=0.4",
                                     facecolor="#0B1C2E", edgecolor=DIV, lw=0.9, zorder=4))
        ra.text(bx+22, 53,   label, ha="center", fontsize=6.5, color=MUT, fontfamily=F, zorder=10, clip_on=False)
        ra.text(bx+22, 47.5, val,   ha="center", fontsize=11,
                color=col, fontweight="bold", fontfamily=F, zorder=10, clip_on=False)

    # 3 bottom metric boxes
    for bx, lbl, val in [
        (4,   "DEW  POINT",  f"{loc['dew_point']}\u00b0F"),
        (35.5,"PRESSURE",    f"{loc['pressure']} hPa"),
        (67,  "VISIBILITY",  f"{loc['visibility']} mi"),
    ]:
        ra.add_patch(FancyBboxPatch((bx,28),(29),(14),
                                     boxstyle="round,pad=0.4",
                                     facecolor="#0B1C2E", edgecolor=DIV, lw=0.9, zorder=4))
        ra.text(bx+14.5, 39,   lbl, ha="center", fontsize=6,   color=MUT, fontfamily=F, zorder=10, clip_on=False)
        ra.text(bx+14.5, 30.5, val, ha="center", fontsize=9.5,
                color=WH, fontweight="bold", fontfamily=F, zorder=10, clip_on=False)

    # Heat label
    heat = loc.get("heat_label", "")
    if heat:
        ra.add_patch(FancyBboxPatch((15,14),(70),(11),
                                     boxstyle="round,pad=0.4",
                                     facecolor="#0B1C2E", edgecolor=DIV, lw=0.9, zorder=4))
        ra.text(50, 19.5, heat.upper(), ha="center", va="center",
                fontsize=10, color=_tcol(loc["temp"]),
                fontweight="bold", fontfamily=F, zorder=10, clip_on=False)

    ra.text(98, .5, "@bdgroves  ·  OpenWeatherMap",
            ha="right", va="bottom", fontsize=6, color="#2A3F55", fontfamily=F)

    plt.savefig(out, dpi=DPI, bbox_inches="tight",
                facecolor=BG, edgecolor="none", pad_inches=0.02)
    plt.close(fig)
    print(f"  Card saved: {out}")


# ── 2x2 COMBINED CARD ─────────────────────────────────────────────────────────
def _render_combined(weather_data: list, report_period: str, timestamp: str, out: str):
    DPI = 150
    fig = plt.figure(figsize=(12.0, 13.50), dpi=DPI, facecolor=BG)

    ha = fig.add_axes([0,.965,1,.035], zorder=10)
    ha.set_xlim(0,1); ha.set_ylim(0,1); ha.axis("off")
    ha.add_patch(Rectangle((0,0),1,1, facecolor=HDR))
    ha.add_patch(Rectangle((0,.88),1,.12, facecolor=ACC))
    period = "Morning" if report_period == "morning" else "Evening"
    from datetime import datetime as _dt
    ts = timestamp if timestamp else _dt.now().strftime("%I:%M %p").lstrip("0") + _dt.now().strftime("  %a %b ") + str(_dt.now().day) + ", " + str(_dt.now().year)
    ha.text(.50,.45, f"Daily Weather  -  {period} Edition   |   {ts}",
            ha="center", va="center", fontsize=10, color=WH,
            fontweight="bold", fontfamily=F)

    panel_h = .960 / 2
    panel_w = 1.0  / 2
    for idx, loc in enumerate(weather_data[:4]):
        row = idx // 2
        col = idx  % 2
        _render_mini_panel(fig, loc, col*panel_w, .005+(1-row)*panel_h, panel_w, panel_h)

    fa = fig.add_axes([0,0,1,.005], zorder=10)
    fa.set_xlim(0,1); fa.set_ylim(0,1); fa.axis("off")
    fa.add_patch(Rectangle((0,0),1,1, facecolor=ACC2, alpha=.6))

    plt.savefig(out, dpi=DPI, bbox_inches="tight",
                facecolor=BG, edgecolor="none", pad_inches=0.02)
    plt.close(fig)
    print(f"  Combined card: {out}")


def _render_mini_panel(fig, loc, x0, y0, pw, ph):
    PAD       = 0.005
    icon_type = _pick_icon(loc.get("description",""))
    uvc, uvlbl = _uv_info(loc["uv_index"])
    tc        = _tcol(loc["temp"])
    slabel    = _station_label(loc["name"], loc["temp"])

    pa = fig.add_axes([x0+PAD, y0+PAD, pw-PAD*2, ph-PAD*2], zorder=3)
    pa.set_xlim(0,100); pa.set_ylim(0,100); pa.axis("off")
    pa.add_patch(Rectangle((0,0),100,100, facecolor="#070D1B", zorder=1))

    pa.add_patch(Rectangle((0,90),100,10,    facecolor=HDR, zorder=2))
    pa.add_patch(Rectangle((0,98.5),100,1.5, facecolor=ACC, zorder=3))
    pa.add_patch(Rectangle((0,90),1.5,10,    facecolor=ACC, zorder=3))
    pa.text(3,  96,   slabel,                           fontsize=6.5, color=ACC, fontweight="bold", fontfamily=F, va="center")
    pa.text(3,  91.5, f"{loc['name']}, {loc['state']}", fontsize=10,  color=WH,  fontweight="bold", fontfamily=F, va="center")
    pa.text(97, 93.5, loc["description"].title(),       fontsize=7,   color=MUT, ha="right",        fontfamily=F, va="center")

    icon_ax = fig.add_axes([x0+PAD+pw*.03, y0+PAD+ph*.52, pw*.26, ph*.36], zorder=5)
    icon_ax.set_xlim(-1.4,1.4); icon_ax.set_ylim(-1.4,1.4); icon_ax.axis("off")
    _draw_icon(icon_ax, 0, 0, 0.86, icon_type)

    pa.text(68, 72, f"{loc['temp']}\u00b0",
            ha="center", va="center", fontsize=52, color=tc,
            fontfamily=F, fontweight="bold",
            path_effects=[pe.withStroke(linewidth=5, foreground="#070D1B")])
    pa.text(68, 57, f"Feels like  {loc['feels_like']}\u00b0F",
            ha="center", fontsize=7.5, color=MUT, fontfamily=F)

    pa.add_patch(FancyBboxPatch((3,47),(94),(9.5),
                                 boxstyle="round,pad=0.4",
                                 facecolor="#0B1C2E", edgecolor=DIV, lw=1, zorder=4))
    pa.plot([50,50],[48,55.5], color=DIV, lw=1, zorder=5)
    pa.text(25, 52, f"H  {loc['temp_high']}\u00b0",
            ha="center", va="center", fontsize=10,
            color=_tcol(loc["temp_high"]), fontfamily=F, fontweight="bold", zorder=6)
    pa.text(75, 52, f"L  {loc['temp_low']}\u00b0",
            ha="center", va="center", fontsize=10,
            color=_tcol(loc["temp_low"]), fontfamily=F, fontweight="bold", zorder=6)

    for (bx,by),(lbl,val,vcol) in zip(
        [(3,36),(52,36),(3,22),(52,22)],
        [("HUMIDITY",  f"{loc['humidity']}%",                     WH),
         ("WIND",      f"{loc['wind_speed']} mph {loc['wind_dir']}", WH),
         ("UV INDEX",  f"{loc['uv_index']}  {uvlbl}",             uvc),
         ("PRECIP",    f"{loc['pop']}%",                          ACC)],
    ):
        pa.add_patch(FancyBboxPatch((bx,by),(44),(12),
                                     boxstyle="round,pad=0.4",
                                     facecolor="#0B1C2E", edgecolor=DIV, lw=0.8, zorder=4))
        pa.text(bx+22, by+8.5, lbl, ha="center", va="center",
                fontsize=6,   color=MUT, fontfamily=F, zorder=6)
        pa.text(bx+22, by+3.5, val, ha="center", va="center",
                fontsize=9,   color=vcol, fontweight="bold", fontfamily=F, zorder=6)

    ticker = (f"Sunrise {_fmt_time(loc['sunrise'])}   |   Sunset {_fmt_time(loc['sunset'])}   |   "
              f"Dew {loc['dew_point']}\u00b0F   |   Clouds {loc['cloud_cover']}%   |   "
              f"Pres {loc['pressure']} hPa")
    pa.add_patch(Rectangle((0,0),100,10,    facecolor=HDR,  zorder=4))
    pa.add_patch(Rectangle((0,9.2),100,.8,  facecolor=ACC2, alpha=.7, zorder=5))
    pa.text(50, 4.5, ticker, ha="center", va="center",
            fontsize=6.2, color=MUT, fontfamily=F, zorder=6)


# ── POST TEXT (used by twitter_post.py & bluesky_post.py) ────────────────────
def build_post_text(weather_data: list, report_period: str, timestamp: str) -> str:
    """Generate rich social post text from live data."""
    period   = "Morning" if report_period == "morning" else "Evening"
    hottest  = max(weather_data, key=lambda x: x["temp"])
    coldest  = min(weather_data, key=lambda x: x["temp"])
    windiest = max(weather_data, key=lambda x: x["wind_speed"])

    lines = [f"{period} Weather Report  |  {timestamp}", ""]
    for loc in weather_data:
        _, uvlbl = _uv_info(loc["uv_index"])
        lines.append(
            f"{loc['name']}, {loc['state']}:  {loc['temp']}F  {loc['description']}  |  "
            f"H {loc['temp_high']}  L {loc['temp_low']}  |  "
            f"Wind {loc['wind_speed']} mph {loc['wind_dir']}  |  UV {loc['uv_index']} {uvlbl}"
        )
    lines += [
        "",
        f"Hottest: {hottest['name']} {hottest['temp']}F  |  "
        f"Coolest: {coldest['name']} {coldest['temp']}F  |  "
        f"Windiest: {windiest['name']} {windiest['wind_speed']} mph",
        "",
        "#Weather #Lakewood #DeathValley #Reno #GrovelandCA #PNW #DailyWeather",
    ]
    return "\n".join(lines)


# ── PUBLIC ENTRY POINT ────────────────────────────────────────────────────────
def create_weather_chart(weather_data, report_period, timestamp,
                         output_path="weather_report.png"):
    out_dir = os.path.dirname(os.path.abspath(output_path))
    for loc in weather_data:
        slug = loc["name"].lower().replace(" ", "_")
        _render_card(loc, os.path.join(out_dir, f"weather_{slug}.png"))
    _render_combined(weather_data, report_period, timestamp, output_path)
    print(f"All charts saved. Main output: {output_path}")
