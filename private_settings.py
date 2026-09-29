"""Owner's private alert preferences.

They never live in this public repository. They are read from, in order:
  1. the ALERT_SETTINGS environment variable (a GitHub Actions *variable*, visible only to repo admins)
  2. a local, git-ignored private_settings.txt (for running on your own computer)
If neither exists, alerts use the neutral defaults below: no home state, no food alerts, no keywords.

Format: one "name: value" per line, "#" starts a comment.

  price_errors: push        # push = phone buzzes
  big_discounts: quiet      # quiet = no sound; waits in the ntfy app until you check
  cheap: off                # off = never sent
  freebies: quiet
  food: push                # needs state
  tech: push                # default for every tech rule...
  laptops: push             # ...or set one rule by name (see tech_watch.json)
  store_deals: push         # 80%+ finds from the retailer scan (private topic only)
  keywords: push
  state: NSW                # home state for food and state-only deals
  watch: dyson, lego        # extra words that always count as a match
"""
import os
import re
from pathlib import Path

MODES = ("off", "quiet", "push")          # ordered weakest -> strongest
DEFAULTS = {
    "price_errors": "push",
    "big_discounts": "push",
    "cheap": "quiet",
    "freebies": "quiet",
    "food": "off",
    "tech": "push",
    "store_deals": "push",
    "keywords": "push",
}
STATES = ("NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT")
STATE_CITIES = {
    "NSW": ["sydney", "newcastle", "wollongong"], "VIC": ["melbourne", "geelong", "victoria"],
    "QLD": ["brisbane", "gold coast", "queensland"], "WA": ["perth"], "SA": ["adelaide"],
    "TAS": ["hobart"], "ACT": ["canberra"], "NT": ["darwin"],
}
QUIET_PRIORITY = "2"   # ntfy "low": delivered without sound or banner; listed in the app


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def parse(text):
    modes, state, watch, problems = dict(DEFAULTS), "", [], []
    for n, raw in enumerate((text or "").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            problems.append(f"line {n}: expected 'name: value'")
            continue
        key, value = (p.strip() for p in line.split(":", 1))
        key = slug(key)
        if key == "state":
            value = value.upper()
            if value and value not in STATES:
                problems.append(f"line {n}: unknown state {value!r}")
            else:
                state = value
        elif key == "watch":
            watch = [w.strip() for w in value.split(",") if w.strip()]
        elif value.lower() in MODES:
            modes[key] = value.lower()
        else:
            problems.append(f"line {n}: {key} must be push, quiet or off")
    return {"modes": modes, "state": state, "watch": watch, "problems": problems}


def load(here):
    text = os.environ.get("ALERT_SETTINGS")
    if text is None:
        local = Path(here, "private_settings.txt")
        text = local.read_text() if local.exists() else ""
    return parse(text)


def categories(reasons):
    """Map a deal's match reasons to setting names."""
    cats = []
    for r in reasons:
        if r == "PRICE ERROR":
            cats.append("price_errors")
        elif r == "glitchy/clearance wording" or (r.endswith("% off") and "food" not in r):
            cats.append("big_discounts")
        elif r.startswith("under $"):
            cats.append("cheap")
        elif r == "FREE":
            cats.append("freebies")
        elif r == "FOOD":
            cats.append("food")
        elif r.startswith("Tech: "):
            cats.append("tech:" + slug(r[6:]))
        elif r.startswith("watch: "):
            cats.append("keywords")
    return cats


def mode_for(reasons, settings):
    """Strongest mode across everything the deal matched; 'off' if nothing is enabled."""
    modes = settings["modes"]
    best = "off"
    for c in categories(reasons):
        if c.startswith("tech:"):
            m = modes.get(c[5:], modes.get("tech", "push"))
        else:
            m = modes.get(c, "off")
        if MODES.index(m) > MODES.index(best):
            best = m
    return best
