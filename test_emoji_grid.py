import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

EMOJI_FONT = "C:/Windows/Fonts/seguiemj.ttf"
fm.fontManager.addfont(EMOJI_FONT)

def ep(size=16):
    return fm.FontProperties(fname=EMOJI_FONT, size=size)

fig, ax = plt.subplots(figsize=(12, 8), facecolor="#0D1117")
ax.set_facecolor("#0D1117")
ax.axis("off")

# Test a grid of emojis to find which ones render well
test_rows = [
    # Weather
    ("\U0001F324", "\U000026C5", "\U0001F326", "\U0001F327", "\U000026A1", "\U0001F328", "\U0001F31F", "\U0001F525"),
    # Nature  
    ("\U0001F332", "\U0001F333", "\U000026F0",  "\U0001F3D4", "\U0001F30A", "\U0001F343", "\U0001F31E", "\U000026C4"),
    # Fun
    ("\U0001F3B0", "\U0001F3C6", "\U0001F4A7", "\U0001F4A8", "\U0001F321", "\U0001F525", "\U2744",     "\U0001F9CA"),
    # Arrows / symbols
    ("\U2B06",     "\U2B07",     "\U27A1",     "\U2197",     "\U2198",     "\U2600",     "\U26A1",     "\U2764"),
    # Numbers/indicators
    ("\U0001F7E5", "\U0001F7E7", "\U0001F7E8", "\U0001F7E9", "\U0001F7E6", "\U0001F7EA", "\U2B24",     "\U25CF"),
]

labels = [
    ["324","26C5","326","327","26A1","328","31F","525"],
    ["332","333","26F0","3D4","30A","343","31E","26C4"],
    ["3B0","3C6","4A7","4A8","321","525","2744","9CA"],
    ["2B06","2B07","27A1","2197","2198","2600","26A1","2764"],
    ["7E5","7E7","7E8","7E9","7E6","7EA","2B24","25CF"],
]

for row_idx, (row, lbl_row) in enumerate(zip(test_rows, labels)):
    y = 0.88 - row_idx * 0.18
    for col_idx, (emoji, lbl) in enumerate(zip(row, lbl_row)):
        x = 0.06 + col_idx * 0.12
        ax.text(x, y, emoji, fontproperties=ep(20),
                ha="center", va="center", color="white")
        ax.text(x, y - 0.06, lbl,
                ha="center", va="center", fontsize=6,
                color="#8B949E", transform=ax.transAxes)

ax.set_title("Emoji Rendering Test - Segoe UI Emoji",
             color="white", fontsize=14, pad=10)

plt.savefig("emoji_grid.png", dpi=120, bbox_inches="tight",
            facecolor="#0D1117")
print("Saved emoji_grid.png")