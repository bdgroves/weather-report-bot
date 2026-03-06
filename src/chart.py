import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from datetime import datetime
import pytz

BG_COLOR      = "#0D1117"
CARD_COLOR    = "#161B22"
CARD_BORDER   = "#30363D"
ACCENT_BLUE   = "#58A6FF"
ACCENT_ORANGE = "#F78166"
ACCENT_GREEN  = "#3FB950"
ACCENT_YELLOW = "#E3B341"
TEXT_PRIMARY  = "#E6EDF3"
TEXT_SECONDARY= "#8B949E"
TEXT_MUTED    = "#484F58"
GRADIENT_HOT  = "#FF6B35"
GRADIENT_COOL = "#58A6FF"

LOCATION_COLORS = ["#58A6FF", "#3FB950", "#F78166", "#E3B341"]


def temp_to_color(temp_f):
    if temp_f >= 100: return "#FF2D2D"
    elif temp_f >= 90: return "#FF6B35"
    elif temp_f >= 80: return "#F78166"
    elif temp_f >= 70: return "#E3B341"
    elif temp_f >= 60: return "#3FB950"
    elif temp_f >= 50: return "#58A6FF"
    elif temp_f >= 32: return "#79C0FF"
    else: return "#B0D8FF"


def uv_label(uv):
    if uv <= 2: return "Low", "#3FB950"
    elif uv <= 5: return "Moderate", "#E3B341"
    elif uv <= 7: return "High", "#F78166"
    elif uv <= 10: return "Very High", "#FF6B35"
    else: return "Extreme", "#FF2D2D"


def create_weather_chart(weather_data, report_period, timestamp, output_path="weather_report.png"):
    fig = plt.figure(figsize=(16, 20), facecolor=BG_COLOR)

    outer = gridspec.GridSpec(
        5, 1, figure=fig,
        hspace=0.35, top=0.93, bottom=0.03,
        left=0.04, right=0.96,
        height_ratios=[0.7, 3.5, 2.2, 2.0, 1.0],
    )

    _draw_header(fig, outer[0], report_period, timestamp)
    _draw_location_cards(fig, outer[1], weather_data)
    _draw_comparison_bars(fig, outer[2], weather_data)
    _draw_fun_stats(fig, outer[3], weather_data)
    _draw_footer(fig, outer[4])

    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)
    print(f"Chart saved to {output_path}")


def _draw_header(fig, spec, report_period, timestamp):
    ax = fig.add_subplot(spec)
    ax.set_facecolor(BG_COLOR)
    ax.axis("off")

    period_icon = "Morning" if report_period == "morning" else "Evening"
    period_emoji = "Sunrise" if report_period == "morning" else "Sunset"

    ax.text(0.5, 0.75,
        f"{period_emoji}  Daily Weather Report  -  {period_icon} Edition",
        transform=ax.transAxes, ha="center", va="center",
        fontsize=22, fontweight="bold", color=TEXT_PRIMARY, fontfamily="monospace")

    ax.text(0.5, 0.15,
        f"Lakewood WA  |  Groveland CA  |  Death Valley CA  |  Reno NV      {timestamp}",
        transform=ax.transAxes, ha="center", va="center",
        fontsize=11, color=TEXT_SECONDARY)

    ax.axhline(y=0.02, xmin=0.05, xmax=0.95, color=CARD_BORDER, linewidth=1.5, alpha=0.8)


def _draw_location_cards(fig, spec, weather_data):
    inner = gridspec.GridSpecFromSubplotSpec(1, 4, subplot_spec=spec, wspace=0.06)

    for i, (loc, color) in enumerate(zip(weather_data, LOCATION_COLORS)):
        ax = fig.add_subplot(inner[i])
        ax.set_facecolor(CARD_COLOR)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(color)
            spine.set_linewidth(1.5)

        tc = temp_to_color(loc["temp"])
        uv_lbl, uv_color = uv_label(loc["uv_index"])

        ax.text(0.5, 0.96, f"{loc['emoji']}  {loc['display']}",
            ha="center", va="top", fontsize=11, fontweight="bold",
            color=color, transform=ax.transAxes)

        ax.text(0.5, 0.80, f"{loc['temp']}F",
            ha="center", va="top", fontsize=36, fontweight="bold",
            color=tc, transform=ax.transAxes)

        ax.text(0.5, 0.63, loc["heat_label"],
            ha="center", va="top", fontsize=10,
            color=tc, transform=ax.transAxes)

        ax.text(0.5, 0.575, loc["description"],
            ha="center", va="top", fontsize=9,
            color=TEXT_SECONDARY, transform=ax.transAxes)

        ax.axhline(y=0.53, xmin=0.08, xmax=0.92, color=CARD_BORDER, linewidth=0.8)

        kpis = [
            ("Feels Like", f"{loc['feels_like']}F"),
            ("High / Low", f"{loc['temp_high']}F / {loc['temp_low']}F"),
            ("Humidity", f"{loc['humidity']}%"),
            ("Wind", f"{loc['wind_speed']} mph {loc['wind_dir']}"),
            ("Precip Chance", f"{loc['pop']}%"),
            ("UV Index", f"{loc['uv_index']} ({uv_lbl})"),
            ("Visibility", f"{loc['visibility']} mi"),
            ("Sunrise", loc["sunrise"]),
            ("Sunset", loc["sunset"]),
        ]

        y_start = 0.50
        row_h = 0.050
        for j, (label, value) in enumerate(kpis):
            y = y_start - j * row_h
            ax.text(0.08, y, label, ha="left", va="center",
                fontsize=7.5, color=TEXT_SECONDARY, transform=ax.transAxes)
            ax.text(0.92, y, value, ha="right", va="center",
                fontsize=7.5, fontweight="bold", color=TEXT_PRIMARY, transform=ax.transAxes)

        ax.axhline(y=0.055, xmin=0.08, xmax=0.92, color=CARD_BORDER, linewidth=0.6)
        ax.text(0.5, 0.03,
            f"Dew Pt: {loc['dew_point']}F  |  Pressure: {loc['pressure']} hPa  |  Clouds: {loc['cloud_cover']}%",
            ha="center", va="bottom", fontsize=6.5,
            color=TEXT_MUTED, transform=ax.transAxes)


def _draw_comparison_bars(fig, spec, weather_data):
    inner = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=spec, wspace=0.35)
    labels = [d["display"].split(",")[0] for d in weather_data]

    # Temperature
    ax1 = fig.add_subplot(inner[0])
    ax1.set_facecolor(CARD_COLOR)
    for spine in ax1.spines.values():
        spine.set_color(CARD_BORDER)
    ax1.tick_params(colors=TEXT_SECONDARY, labelsize=8)

    x = np.arange(len(labels))
    w = 0.25
    lows  = [d["temp_low"]  for d in weather_data]
    temps = [d["temp"]      for d in weather_data]
    highs = [d["temp_high"] for d in weather_data]

    b1 = ax1.bar(x - w, lows,  w, label="Low",     color=ACCENT_BLUE,   alpha=0.85)
    b2 = ax1.bar(x,     temps, w, label="Current", color=ACCENT_ORANGE, alpha=0.85)
    b3 = ax1.bar(x + w, highs, w, label="High",    color=GRADIENT_HOT,  alpha=0.85)

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, color=TEXT_SECONDARY, fontsize=8)
    ax1.set_title("Temperature (F)", color=TEXT_PRIMARY, fontsize=10, pad=8)
    ax1.legend(fontsize=7, labelcolor=TEXT_SECONDARY, facecolor=CARD_COLOR, edgecolor=CARD_BORDER)

    for bars in [b1, b2, b3]:
        for rect in bars:
            h = rect.get_height()
            ax1.text(rect.get_x() + rect.get_width() / 2.0, h + 0.5,
                f"{int(h)}", ha="center", va="bottom", fontsize=6, color=TEXT_SECONDARY)

    # Humidity & Wind
    ax2 = fig.add_subplot(inner[1])
    ax2.set_facecolor(CARD_COLOR)
    for spine in ax2.spines.values():
        spine.set_color(CARD_BORDER)
    ax2.tick_params(colors=TEXT_SECONDARY, labelsize=8)

    humidity = [d["humidity"]   for d in weather_data]
    wind     = [d["wind_speed"] for d in weather_data]

    bh = ax2.bar(x - 0.2, humidity, 0.35, label="Humidity %", color=ACCENT_BLUE,  alpha=0.85)
    bw = ax2.bar(x + 0.2, wind,     0.35, label="Wind mph",   color=ACCENT_GREEN, alpha=0.85)

    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, color=TEXT_SECONDARY, fontsize=8)
    ax2.set_title("Humidity % & Wind mph", color=TEXT_PRIMARY, fontsize=10, pad=8)
    ax2.legend(fontsize=7, labelcolor=TEXT_SECONDARY, facecolor=CARD_COLOR, edgecolor=CARD_BORDER)

    for bars in [bh, bw]:
        for rect in bars:
            h = rect.get_height()
            ax2.text(rect.get_x() + rect.get_width() / 2.0, h + 0.3,
                f"{int(h)}", ha="center", va="bottom", fontsize=6.5, color=TEXT_SECONDARY)

    # UV Index
    ax3 = fig.add_subplot(inner[2])
    ax3.set_facecolor(CARD_COLOR)
    for spine in ax3.spines.values():
        spine.set_color(CARD_BORDER)
    ax3.tick_params(colors=TEXT_SECONDARY, labelsize=8)

    uv_vals   = [d["uv_index"] for d in weather_data]
    uv_colors = [uv_label(u)[1] for u in uv_vals]

    bars = ax3.bar(labels, uv_vals, color=uv_colors, alpha=0.9, width=0.5)
    ax3.set_title("UV Index", color=TEXT_PRIMARY, fontsize=10, pad=8)
    ax3.set_xticklabels(labels, color=TEXT_SECONDARY, fontsize=8)

    for rect, uv in zip(bars, uv_vals):
        lbl, _ = uv_label(uv)
        ax3.text(rect.get_x() + rect.get_width() / 2.0, rect.get_height() + 0.1,
            f"{uv} {lbl}", ha="center", va="bottom", fontsize=7, color=TEXT_SECONDARY)

    for level, col in [(3, ACCENT_GREEN), (6, ACCENT_YELLOW), (8, ACCENT_ORANGE)]:
        ax3.axhline(y=level, color=col, linestyle="--", linewidth=0.7, alpha=0.4)


def _draw_fun_stats(fig, spec, weather_data):
    ax = fig.add_subplot(spec)
    ax.set_facecolor(CARD_COLOR)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(CARD_BORDER)

    ax.text(0.5, 0.93, "Fun Stats & Extremes",
        ha="center", va="top", fontsize=12, fontweight="bold",
        color=TEXT_PRIMARY, transform=ax.transAxes)

    ax.axhline(y=0.83, xmin=0.03, xmax=0.97, color=CARD_BORDER, linewidth=0.8)

    hottest    = max(weather_data, key=lambda x: x["temp"])
    coldest    = min(weather_data, key=lambda x: x["temp"])
    windiest   = max(weather_data, key=lambda x: x["wind_speed"])
    most_humid = max(weather_data, key=lambda x: x["humidity"])
    highest_uv = max(weather_data, key=lambda x: x["uv_index"])
    temp_spread = hottest["temp"] - coldest["temp"]

    fun_stats = [
        {"icon": "HOT",  "title": "Hottest Spot",  "value": hottest["display"].split(",")[0],
         "sub": f"{hottest['temp']}F  {hottest['heat_label']}", "color": GRADIENT_HOT},
        {"icon": "COLD", "title": "Coolest Spot",  "value": coldest["display"].split(",")[0],
         "sub": f"{coldest['temp']}F  {coldest['heat_label']}", "color": GRADIENT_COOL},
        {"icon": "WIND", "title": "Windiest",       "value": windiest["display"].split(",")[0],
         "sub": f"{windiest['wind_speed']} mph {windiest['wind_dir']}", "color": ACCENT_GREEN},
        {"icon": "HUM",  "title": "Most Humid",     "value": most_humid["display"].split(",")[0],
         "sub": f"{most_humid['humidity']}% RH", "color": ACCENT_BLUE},
        {"icon": "UV",   "title": "Highest UV",     "value": highest_uv["display"].split(",")[0],
         "sub": f"UV {highest_uv['uv_index']}  {uv_label(highest_uv['uv_index'])[0]}", "color": ACCENT_YELLOW},
        {"icon": "SPAN", "title": "Temp Spread",    "value": f"{temp_spread}F Range",
         "sub": f"{coldest['temp']}F  to  {hottest['temp']}F", "color": ACCENT_ORANGE},
    ]

    col_w = 1.0 / len(fun_stats)
    for i, stat in enumerate(fun_stats):
        xc = col_w * i + col_w / 2
        ax.text(xc, 0.72, stat["icon"], ha="center", va="top",
            fontsize=11, fontweight="bold", color=stat["color"], transform=ax.transAxes)
        ax.text(xc, 0.56, stat["title"], ha="center", va="top",
            fontsize=8.5, color=TEXT_SECONDARY, transform=ax.transAxes)
        ax.text(xc, 0.40, stat["value"], ha="center", va="top",
            fontsize=11, fontweight="bold", color=stat["color"], transform=ax.transAxes)
        ax.text(xc, 0.22, stat["sub"], ha="center", va="top",
            fontsize=8, color=TEXT_SECONDARY, transform=ax.transAxes)

        if i < len(fun_stats) - 1:
            ax.axvline(x=col_w * (i + 1), ymin=0.05, ymax=0.88,
                color=CARD_BORDER, linewidth=0.8)


def _draw_footer(fig, spec):
    ax = fig.add_subplot(spec)
    ax.set_facecolor(BG_COLOR)
    ax.axis("off")

    ax.text(0.5, 0.65,
        "Data: OpenWeatherMap API  |  Built with Python & Matplotlib  |  github.com/bdgroves",
        ha="center", va="center", fontsize=8, color=TEXT_MUTED, transform=ax.transAxes)

    ax.text(0.5, 0.2,
        "#Weather #Lakewood #GrovelandCA #DeathValley #Reno #PNW #DailyWeather",
        ha="center", va="center", fontsize=7.5, color=TEXT_MUTED, transform=ax.transAxes)