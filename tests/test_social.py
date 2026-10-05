"""Offline tests for social_post.py: fake data, fake networks. Run: pytest -q tests"""
import importlib, json, os, sys
from datetime import datetime
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

STATIONS = [
    {"name": n, "display": f"{n}, {st}", "state": st, "temp": t, "temp_high": t + 3, "temp_low": t - 20,
     "description": d, "humidity": 40, "wind_speed": 5, "nws_alerts": a}
    for n, st, t, d, a in [
        ("Lakewood", "WA", 66, "Clear Sky", ["Special Weather Statement"]),
        ("Groveland", "CA", 87, "Clear Sky", ["Red Flag Warning"]),
        ("Death Valley", "CA", 112, "Clear Sky", ["Extreme Heat Warning", "Wind Advisory"]),
        ("Reno", "NV", 80, "Broken Clouds", [])]]


@pytest.fixture
def sp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "weather_data.json").write_text(json.dumps({"stations": STATIONS}))
    for k in ("TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET",
              "BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"):
        monkeypatch.setenv(k, "x")
    for k in ("DRY_RUN", "POST_NOW"):
        monkeypatch.delenv(k, raising=False)
    sys.modules.pop("social_post", None)
    m = importlib.import_module("social_post")
    sent = {"x": [], "bluesky": []}
    m._fail = {"x": None, "bluesky": None}

    def fake(name):
        def send(text, image, *a):
            if m._fail[name]:
                raise RuntimeError(m._fail[name])
            sent[name].append(text)
            return "posted"
        return send
    monkeypatch.setattr(m, "post_x", fake("x"))
    monkeypatch.setattr(m, "post_bsky", lambda t, i, alt: fake("bluesky")(t, i))
    return m, sent


def at(m, monkeypatch, h):
    class D(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 4, h, 33, tzinfo=m.PT)
    monkeypatch.setattr(m, "datetime", D)


def test_text(sp):
    m, _ = sp
    now = datetime(2026, 10, 4, 18, 33, tzinfo=m.PT)
    x = m.build_text({"stations": STATIONS}, now, "x")
    b = m.build_text({"stations": STATIONS}, now, "bluesky")
    assert x.startswith("West Coast weather · Sun Oct 4, 6:33 PM")
    assert "🔥 Death Valley 112° clear sky · H115 L92" in x
    assert "⚠️ Groveland: Red Flag Warning" in x and "Special Weather Statement" not in x
    assert "Wind Advisory" not in x and "#WAwx" in x and "#" not in b
    assert len(x) - (len(m.DASHBOARD) - 23) <= 280 and len(b) <= 300


def test_once_per_window_and_independent(sp, monkeypatch):
    m, sent = sp
    at(m, monkeypatch, 3)
    assert m.main() == 0 and not sent["x"]           # outside windows
    at(m, monkeypatch, 18)
    m._fail["x"] = "403 Forbidden"
    assert m.main() == 1                              # X broke: fail once
    assert len(sent["bluesky"]) == 1                  # Bluesky still posted
    assert m.main() == 0 and len(sent["bluesky"]) == 1  # no repeat; X still failing, quiet
    m._fail["x"] = None
    m.main()
    assert len(sent["x"]) == 1                        # X catches up in the same window
    st = json.load(open("social_state.json"))
    assert st["x"]["ok"] and st["bluesky"]["last_slot"] == "2026-10-04-evening"
    assert "error: " in open("logs/posts.jsonl").read()
