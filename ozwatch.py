#!/usr/bin/env python3
"""OzBargain price-error / super-cheap deal watcher.

Polls OzBargain's public RSS feeds, keeps only live (non-expired) deals that look like
price errors, deep discounts, or very cheap/free items, writes a dashboard (deals.html)
and pops a macOS notification for each new hit.

  python3 ozwatch.py            # one pass
  python3 ozwatch.py --loop 120 # poll every 120s, keep dashboard fresh
  python3 ozwatch.py --loop 120 --serve   # also serve http://localhost:8765

Stdlib only. Tweak the CONFIG block below.
"""
import argparse, hashlib, html, json, os, re, subprocess, sys, threading, time
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# ---------------- CONFIG ----------------
FEEDS = [
    "https://www.ozbargain.com.au/deals/feed",
    "https://www.ozbargain.com.au/deals/feed?page=1",
    "https://www.ozbargain.com.au/deals/feed?page=2",
    "https://www.ozbargain.com.au/freebies/feed",
    "https://www.ozbargain.com.au/cat/dining-takeaway/feed",
    "https://www.ozbargain.com.au/cat/dining-takeaway/feed?page=1",
    "https://www.ozbargain.com.au/cat/groceries/feed",
    "https://www.ozbargain.com.au/cat/computing/feed",
    "https://www.ozbargain.com.au/cat/gaming/feed",
]
# Per-store OzBargain feeds for big stores: rotated, STORE_FEEDS_PER_RUN at a time, to stay polite
STORE_FEEDS = ["amazon.com.au", "jbhifi.com.au", "kmart.com.au", "bigw.com.au", "officeworks.com.au",
    "thegoodguys.com.au", "harveynorman.com.au", "ebay.com.au", "myer.com.au", "davidjones.com",
    "theiconic.com.au", "coles.com.au", "woolworths.com.au", "bunnings.com.au", "target.com.au",
    "costco.com.au", "aldi.com.au", "apple.com", "samsung.com", "dell.com", "lenovo.com",
    "chemistwarehouse.com.au", "priceline.com.au", "rebelsport.com.au", "dyson.com.au",
    "appliancesonline.com.au", "mwave.com.au", "scorptec.com.au", "pccasegear.com", "umart.com.au",
    "binglee.com.au", "kogan.com", "hp.com", "ebgames.com.au", "centrecom.com.au", "ple.com.au"]
STORE_FEEDS_PER_RUN = 4
ERROR_WORDS = re.compile(
    r"price[\s-]*error|pricing[\s-]*(error|mistake|glitch)|price[\s-]*mistake|glitch|"
    r"mispric|wrong price|error price|pricing bug|\bbug\b|too good|probably (an )?error|"
    r"lowest ever|clearance|stacks? with|stack(ed)? (with|coupon)", re.I)
STRONG_ERROR = re.compile(r"price[\s-]*error|pricing[\s-]*(error|mistake|glitch)|price[\s-]*mistake|glitch|mispric|wrong price|error price|pricing bug", re.I)
MIN_DISCOUNT_PCT = 60          # flag anything at least this % off (when Was/RRP is stated)
CHEAP_UNDER = 5.0              # flag any priced item at or under this ($)
MIN_VOTES_FOR_DISCOUNT = 0     # net votes needed for pure-discount hits (errors always shown)
BIG_STORES = ["Samsung", "Apple", "Dell", "Lenovo", "Chemist Warehouse", "Priceline", "rebel", "Dyson",
              "Appliances Online", "Mwave", "Scorptec", "PCCaseGear", "Umart", "Bing Lee", "Kogan", "Amazon AU", "JB Hi-Fi", "Kmart", "Big W", "BIG W", "Officeworks", "The Good Guys", "Harvey Norman",
              "Myer", "David Jones", "THE ICONIC", "The Iconic", "eBay", "Coles", "Woolworths", "Bunnings", "Target", "Costco", "Aldi", "ALDI"]
WATCH_KEYWORDS = []            # e.g. ["laptop", "rtx", "lego", "dyson"] - always flag these
FOOD_MODE = True               # food & drink alerts, filtered to MY_STATE
MY_STATE = "NSW"               # Sydney
OTHER_STATES = [x for x in ("NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT") if x != MY_STATE]
FOOD_MAX_PRICE = 3.0           # a meal/drink at or under this counts as a steal
FOOD_MIN_PCT = 50              # or this % off / half price / 2-for-1
FOOD_WORDS = re.compile(
    r"\b(coffee|burger|pizza|pie|pies|sausage|hotdog|hot dog|snag|taco|burrito|nuggets?|fries|chips|chicken|"
    r"ice ?cream|gelato|donut|doughnut|cake|cookie|sushi|ramen|noodles?|pho|kebab|wrap|sandwich|breakfast|lunch|"
    r"dinner|meal|feast|combo|dessert|smoothie|bubble tea|boba|milkshake|beer|wine|cocktail|drink|tea|bakery|"
    r"cafe|caf\u00e9|restaurant|maccas|mcdonald'?s|kfc|domino'?s|hungry jack'?s|guzman|gyg|grill'?d|subway|"
    r"oporto|nando'?s|zambrero|red rooster|krispy|starbucks|chatime|gong cha|4 ?fingers|betty'?s|schnitzel|"
    r"wagyu|steak|brekkie|gozleme|dumpling|bbq|curry|grocer(y|ies)|coles|woolworths|aldi|iga|harris farm)\b", re.I)
KEEP_DAYS = 3                  # drop stored deals older than this
NOTIFY = False                 # no macOS in the cloud
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")  # phone push via ntfy.sh - subscribe to this topic in the ntfy app
NTFY_SERVER = "https://ntfy.sh"
NTFY_MIN_SCORE = 40            # only push the good stuff (errors, 40%+ off...); macOS alerts stay at everything
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state.json")
OUT = os.path.join(HERE, "deals.html")
ALERTS_ONLY = False
ALERT_STATE = os.path.join(HERE, "private_alert_state.json")
TECH_CONFIG = json.loads(Path(HERE, "tech_watch.json").read_text())
# ----------------------------------------

NS = {"ozb": "https://www.ozbargain.com.au", "media": "http://search.yahoo.com/mrss/"}
UA = {"User-Agent": "Mozilla/5.0 (ozwatch personal deal watcher)"}
MONEY = r"\$\s?([\d,]+(?:\.\d{1,2})?)"


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def parse_feed(raw):
    root = ET.fromstring(raw)
    for it in root.iter("item"):
        meta = it.find("ozb:meta", NS)
        m = meta.attrib if meta is not None else {}
        cats = [c.text for c in it.findall("category") if c.text]
        yield {
            "id": (it.findtext("guid") or "").split(" ")[0],
            "title": html.unescape(it.findtext("title") or ""),
            "link": it.findtext("link"),
            "goto": m.get("link"),
            "store_url": m.get("url"),
            "image": m.get("image"),
            "expiry": m.get("expiry"),
            "votes_pos": int(m.get("votes-pos", 0) or 0),
            "votes_neg": int(m.get("votes-neg", 0) or 0),
            "comments": int(m.get("comment-count", 0) or 0),
            "clicks": int(m.get("click-count", 0) or 0),
            "pub": it.findtext("pubDate"),
            "cats": cats,
        }


def money(s):
    return float(s.replace(",", ""))


def price_info(title):
    """Return (price, was) best guess from an OzBargain title."""
    t = title
    was = None
    m = re.search(r"\((?:was|rrp|usually|reg\.?|orig(?:inally)?)[^$)]*" + MONEY, t, re.I) or \
        re.search(r"\b(?:was|rrp)\s*" + MONEY, t, re.I)
    if m:
        was = money(m.group(1))
    prices = [money(x) for x in re.findall(MONEY, t)]
    price = None
    if prices:
        first = re.search(MONEY, t)
        price = money(first.group(1))
    if re.search(r"\bfree\b|\$0\b", t, re.I) and price is None:
        price = 0.0
    return price, was


def is_expired(d, now):
    if re.search(r"\bexpired\b", d["title"], re.I):
        return True
    if d.get("expiry"):
        try:
            expiry = datetime.fromisoformat(d["expiry"])
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < now:
                return True
        except ValueError:
            pass
    return False


def food_score(d, price, was, pct):
    t = d["title"]
    is_food = "Dining & Takeaway" in d["cats"] or "Groceries" in d["cats"] or FOOD_WORDS.search(t)
    if not is_food:
        return 0, []
    tags = re.match(r"\s*((?:\[[^\]]+\]\s*)+)", t)
    tagtxt = tags.group(1).upper() if tags else ""
    if any(re.search(rf"\b{st}\b", tagtxt) for st in OTHER_STATES) and MY_STATE not in tagtxt:
        return 0, []
    if re.search(r"melbourne|brisbane|perth|adelaide|canberra|hobart|darwin|gold coast|victoria|queensland", t, re.I) and not re.search("sydney", t, re.I):
        return 0, []
    sc, rs = 0, []
    if re.search(r"\bfree\b", t, re.I) and not re.search(r"free (delivery|shipping|postage|c&c|pickup|returns)|delivery free", t, re.I):
        sc += 60; rs.append("FREE FOOD")
    if re.search(r"half[\s-]?price|1/2 price|\b2[\s-]?(for|4)[\s-]?1\b|buy one get one|\bbogo\b", t, re.I):
        sc += 45; rs.append("2-for-1 / half price")
    if pct and pct >= FOOD_MIN_PCT:
        sc += pct * 0.6; rs.append(f"{pct}% off food")
    if price is not None and 0 < price <= FOOD_MAX_PRICE and not re.search(r"cashback|voucher|gift ?card", t, re.I):
        sc += 40; rs.append(f"food under ${FOOD_MAX_PRICE:g}")
    if sc and MY_STATE in tagtxt:
        sc += 10; rs.append("Sydney/NSW")
    if sc:
        rs.insert(0, "FOOD")
    return sc, rs


def tech_matches(title, price, votes):
    """Personal interests, not a claim of historical-low pricing or verified value."""
    if price is None or votes < TECH_CONFIG.get("minimum_votes", 3):
        return []
    matches = []
    for rule in TECH_CONFIG["rules"]:
        if (price >= rule.get("minimum_price", 0)
                and re.search(rule["pattern"], title, re.I)
                and not (rule.get("exclude") and re.search(rule["exclude"], title, re.I))):
            matches.append(rule["name"])
    # An expensive console is classified once, not also as an accessory.
    if "PS5 consoles" in matches and "Gaming accessories" in matches:
        matches.remove("Gaming accessories")
    return matches


def alert_key(deal_id):
    return hashlib.sha256(deal_id.encode()).hexdigest()


def load_alert_history():
    try:
        data = json.loads(Path(ALERT_STATE).read_text())
        return {k:v for k,v in data.items() if isinstance(k,str) and len(k)==64 and isinstance(v,(int,float))}
    except (OSError, ValueError, AttributeError):
        return {}


def classify(d):
    """Return (score, reasons) - 0 score means not interesting."""
    t = d["title"]
    price, was = price_info(t)
    d["price"], d["was"] = price, was
    tg = re.match(r"\s*((?:\[[^\]]+\]\s*)+)", t)
    tg = tg.group(1).upper() if tg else ""
    if any(re.search(rf"\b{st}\b", tg) for st in OTHER_STATES) and MY_STATE not in tg:
        return 0, []   # state-locked deal for somewhere other than Sydney
    reasons, score = [], 0
    if STRONG_ERROR.search(t):
        reasons.append("PRICE ERROR"); score += 100
    elif ERROR_WORDS.search(t):
        reasons.append("glitchy/clearance wording"); score += 15
    pct = None
    if price is not None and was and was > price:
        pct = round((1 - price / was) * 100)
        d["pct"] = pct
        if pct >= MIN_DISCOUNT_PCT and (d["votes_pos"] - d["votes_neg"]) >= MIN_VOTES_FOR_DISCOUNT:
            reasons.append(f"{pct}% off"); score += pct
    if price is not None and 0 < price <= CHEAP_UNDER and not re.search(r"cashback|bonus|gift ?card|voucher|\boff\b", t, re.I):
        reasons.append(f"under ${CHEAP_UNDER:g}"); score += 25
    if price == 0.0 or re.search(r"\bfree(bie)?\b", t, re.I):
        if not re.search(r"free (delivery|shipping|postage|c&c|pickup|returns)|\+ free", t, re.I) or price == 0.0:
            if not re.match(r"\s*\[(" + "|".join(OTHER_STATES) + r")", t, re.I):
                reasons.append("FREE"); score += 8
    if FOOD_MODE:
        fs, fr = food_score(d, price, was, pct)
        if fs:
            score += fs; reasons += fr
    store = re.search(r"@\s*([^@]+)$", t)
    if store and reasons and any(b.lower() in store.group(1).lower() for b in BIG_STORES):
        reasons.append("big store"); score += 20
    for category in tech_matches(t, price, d["votes_pos"] - d["votes_neg"]):
        reasons.append("Tech: " + category)
        score += 40
    for k in WATCH_KEYWORDS:
        if k.lower() in t.lower():
            reasons.append(f"watch: {k}"); score += 40
    score += min(d["votes_pos"], 60) * 0.5   # crowd validation
    if score < 20 and not reasons:
        return 0, []
    if not reasons:
        return 0, []
    return score, reasons


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(s):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f)
    os.replace(tmp, STATE)


def push(title, body, url, urgent):
    if not NTFY_TOPIC:
        return
    try:
        req = urllib.request.Request(
            f"{NTFY_SERVER}/{NTFY_TOPIC}", data=body.encode("utf-8"), method="POST",
            headers={"Title": title.encode("ascii", "ignore").decode(), "Click": url,
                     "Priority": "5" if urgent else "3", "Tags": "rotating_light" if urgent else "moneybag"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print("  ! ntfy:", e, file=sys.stderr)


def notify(title, body, url):
    if not NOTIFY or sys.platform != "darwin":
        return
    esc = lambda x: x.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.run(["osascript", "-e",
                    f'display notification "{esc(body)[:180]}" with title "{esc(title)[:80]}"'],
                   capture_output=True)


def run_once(first_run_silent=False):
    now = datetime.now(timezone.utc).astimezone()
    history = load_alert_history() if ALERTS_ONLY else {}
    state = {} if ALERTS_ONLY else load_state()
    seen_any = bool(history) if ALERTS_ONLY else bool(state)
    found, feeds_ok = 0, 0
    slot = int(time.time() // 300)
    picks = [STORE_FEEDS[(slot * STORE_FEEDS_PER_RUN + i) % len(STORE_FEEDS)] for i in range(STORE_FEEDS_PER_RUN)]
    for url in FEEDS + [f"https://www.ozbargain.com.au/deals/{d}/feed" for d in picks]:
        try:
            items = list(parse_feed(fetch(url)))
            feeds_ok += 1
            for d in items:
                if not d["id"]:
                    continue
                old = state.get(d["id"])
                d["seen"] = old["seen"] if old else time.time()
                d["expired"] = is_expired(d, now)
                d["score"], d["reasons"] = classify(d)
                d["notified"] = alert_key(d["id"]) in history if ALERTS_ONLY else (old.get("notified", False) if old else False)
                state[d["id"]] = d
                found += 1
        except Exception as e:
            print(f"  ! {url}: {e}", file=sys.stderr)
    if not feeds_ok:
        raise RuntimeError("No RSS feeds could be read; keeping previous state and sending no new alerts")
    # refresh expiry against clock, prune
    cutoff = time.time() - KEEP_DAYS * 86400
    for k in list(state):
        v = state[k]
        if v["seen"] < cutoff:
            del state[k]; continue
        v["expired"] = is_expired(v, now)
    # notify new live hits
    sent = 0
    for v in sorted(state.values(), key=lambda v: -v["score"]):
        if v["score"] and not v["expired"] and not v["notified"]:
            if seen_any and sent >= TECH_CONFIG.get("max_alerts_per_run", 6):
                continue
            v["notified"] = True
            history[alert_key(v["id"])] = time.time()
            if seen_any:  # don't spam on very first run
                notify("OzBargain: " + ", ".join(v["reasons"][:2]), v["title"], v["link"])
                if v["score"] >= NTFY_MIN_SCORE:
                    push("OzBargain: " + ", ".join(v["reasons"][:2]), v["title"], v["link"],
                         any("ERROR" in r for r in v["reasons"]))
                sent += 1
                if not ALERTS_ONLY:
                    print("NEW:", v["reasons"], v["title"])
    if ALERTS_ONLY:
        history = {k:v for k,v in history.items() if time.time() - v < 14 * 86400}
        Path(ALERT_STATE + ".tmp").write_text(json.dumps(history))
        os.replace(ALERT_STATE + ".tmp", ALERT_STATE)
    else:
        save_state(state)
        write_html(state, now)
    # OzBargain content stays private (their terms restrict commercial reuse); remove any old public copy
    try:
        os.remove(os.path.join(HERE, "site", "data", "ozb.json"))
    except FileNotFoundError:
        pass
    live = [v for v in state.values() if v["score"] and not v["expired"]]
    print(f"[{now:%H:%M:%S}] {feeds_ok}/{len(FEEDS) + len(picks)} feeds read; {found} items; {len(live)} matches; {sent} new notifications considered")
    return {"feeds_ok": feeds_ok, "items": found, "matches": len(live), "notifications": sent}


CSS = """
:root{--bg:#f6f5f1;--card:#fff;--ink:#1c1b18;--mut:#6b675e;--line:#e6e2d8;--err:#c8102e;--ok:#0b7a4b;--acc:#ff6a00}
@media(prefers-color-scheme:dark){:root{--bg:#141412;--card:#1e1d1a;--ink:#f1efe8;--mut:#9b978c;--line:#2e2c27;--err:#ff5470;--ok:#3ddc97;--acc:#ff8a3d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,Segoe UI,Roboto,sans-serif}
header{padding:28px 20px 8px;max-width:1100px;margin:auto}h1{margin:0;font-size:26px;letter-spacing:-.02em}
.sub{color:var(--mut);margin-top:4px;font-size:13px}
.bar{max-width:1100px;margin:14px auto 0;padding:0 20px;display:flex;gap:8px;flex-wrap:wrap}
.chip{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:6px 12px;border-radius:99px;font-size:13px;cursor:pointer}
.chip.on{background:var(--ink);color:var(--bg)}
main{max-width:1100px;margin:16px auto 60px;padding:0 20px;display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.card.err{border-color:var(--err);box-shadow:0 0 0 1px var(--err)}
.img{height:150px;background:#fff center/contain no-repeat;border-bottom:1px solid var(--line)}
.body{padding:12px 14px 14px;display:flex;flex-direction:column;gap:8px;flex:1}
.tags{display:flex;gap:6px;flex-wrap:wrap}
.tag{font-size:11px;font-weight:700;padding:2px 8px;border-radius:99px;background:var(--line);text-transform:uppercase;letter-spacing:.03em}
.tag.e{background:var(--err);color:#fff}.tag.n{background:var(--acc);color:#fff}.tag.d{background:var(--ok);color:#fff}
.t{font-weight:600;text-decoration:none;color:var(--ink)}.t:hover{text-decoration:underline}
.price{font-size:22px;font-weight:800}.was{color:var(--mut);text-decoration:line-through;font-size:14px;margin-left:6px}
.meta{color:var(--mut);font-size:12px;margin-top:auto;display:flex;gap:10px;flex-wrap:wrap}
.btns{display:flex;gap:8px}.btns a{flex:1;text-align:center;padding:8px;border-radius:9px;font-weight:600;font-size:13px;text-decoration:none;border:1px solid var(--line);color:var(--ink)}
.btns a.go{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.empty{grid-column:1/-1;text-align:center;color:var(--mut);padding:60px 0}
"""

JS = """
const chips=[...document.querySelectorAll('.chip')];
chips.forEach(c=>c.onclick=()=>{chips.forEach(x=>x.classList.remove('on'));c.classList.add('on');
const f=c.dataset.f;document.querySelectorAll('.card').forEach(k=>{k.style.display=(f==='all'||k.dataset.k.includes(f))?'':'none'})});
"""


def ago(ts):
    s = int(time.time() - ts)
    return f"{s//60}m ago" if s < 3600 else f"{s//3600}h ago" if s < 86400 else f"{s//86400}d ago"


def write_html(state, now):
    hits = [v for v in state.values() if v["score"] and not v["expired"]]
    hits.sort(key=lambda v: (-v["score"]))
    cards = []
    for v in hits:
        kinds = []
        if any("ERROR" in r for r in v["reasons"]): kinds.append("error")
        if any("FREE" in r for r in v["reasons"]): kinds.append("free")
        if any("off" in r for r in v["reasons"]): kinds.append("deep")
        if any("under" in r for r in v["reasons"]): kinds.append("cheap")
        if any("watch" in r for r in v["reasons"]): kinds.append("watch")
        if any(r.startswith("Tech:") for r in v["reasons"]): kinds.append("tech")
        if "FOOD" in v["reasons"]: kinds.append("food")
        tags = "".join(
            f'<span class="tag {"e" if "ERROR" in r else "d" if ("off" in r or "FREE" in r or r == "FOOD") else ""}">{html.escape(r)}</span>'
            for r in v["reasons"])
        if time.time() - v["seen"] < 1800:
            tags = '<span class="tag n">new</span>' + tags
        price = ""
        if v.get("price") is not None:
            price = f'<div class="price">${v["price"]:,.2f}' + (f'<span class="was">${v["was"]:,.2f}</span>' if v.get("was") else "") + "</div>"
        exp = ""
        if v.get("expiry"):
            exp = f'<span>ends {v["expiry"][:10]}</span>'
        img = f'style="background-image:url({html.escape(v["image"])})"' if v.get("image") else ""
        cards.append(f'''<div class="card {"err" if "error" in kinds else ""}" data-k="{" ".join(kinds)}">
<div class="img" {img}></div><div class="body"><div class="tags">{tags}</div>
<a class="t" href="{html.escape(v["link"])}" target="_blank">{html.escape(v["title"])}</a>{price}
<div class="meta"><span>▲ {v["votes_pos"]}{f" ▼ {v['votes_neg']}" if v["votes_neg"] else ""}</span><span>💬 {v["comments"]}</span><span>seen {ago(v["seen"])}</span>{exp}</div>
<div class="btns"><a class="go" href="{html.escape(v.get("goto") or v["link"])}" target="_blank">Go to deal</a><a href="{html.escape(v["link"])}" target="_blank">Check comments</a></div>
</div></div>''')
    body = "".join(cards) or '<div class="empty">No live hits right now. Watching…</div>'
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="60"><title>OzBargain Watcher</title><style>{CSS}</style></head><body>
<header><h1>OzBargain error &amp; steal watcher</h1>
<div class="sub">{len(hits)} live, non-expired hits · updated {now:%a %H:%M:%S} · page refreshes every 60s · ALWAYS read the comments: errors get cancelled and "expired" flags lag</div></header>
<div class="bar"><button class="chip on" data-f="all">All</button><button class="chip" data-f="error">Price errors</button>
<button class="chip" data-f="free">Free</button><button class="chip" data-f="deep">{MIN_DISCOUNT_PCT}%+ off</button>
<button class="chip" data-f="cheap">Under ${CHEAP_UNDER:g}</button><button class="chip" data-f="food">🍔 Food ({MY_STATE})</button><button class="chip" data-f="watch">My keywords</button><button class="chip" data-f="tech">Laptops, PS5 &amp; tech</button></div>
<main>{body}</main><script>{JS}</script></body></html>'''
    with open(OUT, "w") as f:
        f.write(page)


def serve(port):
    os.chdir(HERE)
    class H(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/", "/deals.html"):
                self.send_error(404)
                return
            self.path = "/deals.html"
            return super().do_GET()
        def do_HEAD(self):
            self.send_error(405)
        def log_message(self, *a): pass
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--alerts-only", action="store_true", help="send personal notifications without saving RSS content or a dashboard")
    ap.add_argument("--loop", type=int, default=0, help="poll interval seconds (0 = once)")
    ap.add_argument("--serve", action="store_true", help="serve dashboard on localhost:8765")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    ALERTS_ONLY = a.alerts_only
    if a.serve and a.alerts_only:
        ap.error("--serve needs local dashboard mode; omit --alerts-only")
    if a.serve:
        threading.Thread(target=serve, args=(a.port,), daemon=True).start()
        print(f"Dashboard: http://localhost:{a.port}")
    run_once()
    while a.loop:
        time.sleep(max(a.loop, 300))
        run_once()
