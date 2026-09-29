"""Static, crawlable pages built from site/data/deals.json:
 - featured strip + prerendered grid on the home page (JS takes over for filtering)
 - /sale/<category>.html and /sale/<store>.html landing pages with Product JSON-LD
"""
import html, json, os, re

CATS = ["Tech", "Shoes", "Fashion", "Home & Kitchen", "Beauty", "Outdoors", "Travel", "Marketplace"]
e = html.escape


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def aud(n):
    return f"${n:,.2f}".replace(".00", "")


BASE = ""   # set by build(); share links point back to this site


def share_attrs(d):
    from urllib.parse import urlencode
    url = f"{BASE}/?" + urlencode({"q": d["title"], "store": d["store"]})
    text = f'-{d["pct"]}%: {d["title"]} {aud(d["price"])} (was {aud(d["was"])}) at {d["store"]}'
    return f'data-share-url="{e(url)}" data-share-text="{e(text)}"'


def card(d, prefix=""):
    img = f'<img src="{e(d["img"])}" alt="{e(d["title"])}" loading="lazy" decoding="async">' if d.get("img") else ""
    brand = f'{e(d["brand"])} · ' if d.get("brand") and d["brand"] != d["store"] else ""
    flag = '<span class="flag">Possible error</span>' if d.get("error") else ""
    return (f'<article class="card{" error" if d.get("error") else ""}"><a class="deal-link" href="{e(d["url"])}" target="_blank" rel="noopener sponsored">'
            f'<div class="ph">{img}<span class="pct">-{d["pct"]}%</span>{flag}</div>'
            f'<div class="info"><div class="meta">{brand}{e(d["store"])}</div><div class="title">{e(d["title"])}</div>'
            f'<div class="prices"><span class="now">{aud(d["price"])}</span><span class="was">{aud(d["was"])}</span>'
            f'<span class="save">Save {aud(round(d["was"] - d["price"]))}</span></div></div></a>'
            f'<div class="card-actions"><button class="ghost" type="button" {share_attrs(d)}>Share</button></div></article>')


def top_picks(deals, n):
    """Best deal per store in turn, so one store can't fill the page."""
    lanes = {}
    for d in sorted(deals, key=lambda d: -d["pct"]):
        lanes.setdefault(d["store"], []).append(d)
    order = sorted(lanes.values(), key=lambda l: -l[0]["pct"])
    out, i = [], 0
    while len(out) < n and any(i < len(l) for l in order):
        out += [l[i] for l in order if i < len(l)]
        i += 1
    return out[:n]


def jsonld(deals, url, name):
    items = [{"@type": "ListItem", "position": i + 1, "item": {
        "@type": "Product", "name": d["title"], "image": d.get("img") or None,
        "brand": {"@type": "Brand", "name": d.get("brand") or d["store"]},
        "offers": {"@type": "Offer", "price": f'{d["price"]:.2f}', "priceCurrency": "AUD",
                   "availability": "https://schema.org/InStock", "url": d["url"],
                   "seller": {"@type": "Organization", "name": d["store"]}}}} for i, d in enumerate(deals[:30])]
    return ('<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@type": "ItemList", "name": name, "url": url, "itemListElement": items},
        separators=(",", ":")).replace("</", "<\\/") + "</script>")


PAGE = """<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{desc}"><link rel="canonical" href="{url}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:url" content="{url}"><meta property="og:type" content="website">{ogimg}
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../style.css">{ld}</head><body>
<header class="top slim"><div class="wrap nav"><a class="logo" href="../"><span class="mark">½</span>{brand}</a><nav><a href="../">All deals</a><a href="../#alerts">Get alerts</a></nav></div>
<div class="wrap hero"><p class="eyebrow">{count} live deals · updated every 30 minutes</p><h1>{h1}</h1><p class="lede">{lede}</p>
<p><a class="btn light" href="../?{q}">Filter &amp; search these deals</a></p></div></header>
<main class="wrap"><div class="grid" style="margin-top:24px">{cards}</div>{more}{links}</main>
<footer class="foot"><div class="wrap"><p>Prices come from each store's public product data and can change or sell out; the store's checkout price is final. Some links may be affiliate links. <a href="../about.html#disclosure">Disclosure</a> · <a href="../privacy.html">Privacy</a></p></div></footer>
<script src="../share-deal.js" defer></script></body></html>"""


def build(site, cfg):
    path = os.path.join(site, "data", "deals.json")
    if not os.path.exists(path):
        return []
    data = json.load(open(path))
    deals = data["deals"]
    base = cfg["site_url"].rstrip("/")
    global BASE
    BASE = base
    brand = e(cfg["brand"])
    os.makedirs(os.path.join(site, "sale"), exist_ok=True)
    made = []

    groups = [("cat", c, [d for d in deals if d["cat"] == c]) for c in CATS]
    groups += [("store", s, [d for d in deals if d["store"] == s]) for s in sorted({d["store"] for d in deals})]
    cat_links = " ".join(f'<a class="chip" href="{slug(c)}.html">{e(c)}</a>' for k, c, l in groups if k == "cat" and l)
    store_links = " ".join(f'<a class="chip" href="{slug(s)}.html">{e(s)}</a>' for k, s, l in groups if k == "store" and l)
    for kind, name, items in groups:
        if not items:
            continue
        items = top_picks(items, len(items)) if kind == "cat" else sorted(items, key=lambda d: -d["pct"])
        fn = f"sale/{slug(name)}.html"
        url = f"{base}/{fn}"
        best = items[0]["pct"]
        if kind == "cat":
            title = f"{name} sale: 50%+ off in Australia right now | {cfg['brand']}"
            h1 = f"{e(name)} at half price or less"
            lede = f"{len(items)} in-stock {e(name.lower())} deals at 50% off or more from Australian stores, up to {best}% off. Checked every 30 minutes."
            q = "cat=" + name.replace("&", "%26").replace(" ", "+")
        else:
            title = f"{name} sale: {len(items)} items 50%+ off | {cfg['brand']}"
            h1 = f"{e(name)} sale, 50%+ off"
            lede = f"{len(items)} in-stock items at {e(name)} marked down 50% or more, up to {best}% off. Prices checked every 30 minutes."
            q = "store=" + name.replace("&", "%26").replace(" ", "+")
        more = (f'<div class="more"><a class="btn" href="../?{q}">See all {len(items)} deals</a></div>' if len(items) > 60 else "")
        links = (f'<section class="browse"><h2>Browse by category</h2><div class="chips wrapchips">{cat_links}</div>'
                 f'<h2>Browse by store</h2><div class="chips wrapchips">{store_links}</div></section>')
        ogimg = f'<meta property="og:image" content="{e(items[0]["img"])}">' if items[0].get("img") else ""
        page = PAGE.format(title=e(title), desc=e(lede), url=url, brand=brand, h1=h1, lede=lede, q=q, ogimg=ogimg,
                           count=len(items), cards="".join(card(d) for d in items[:60]), more=more, links=links,
                           ld=jsonld(items, url, title))
        open(os.path.join(site, fn), "w").write(page)
        made.append(fn)

    # home page: featured strip, category tiles, prerendered first grid
    idx = os.path.join(site, "index.html")
    s = open(idx).read()
    feat = top_picks([d for d in deals if d["price"] >= 20 and not d["error"] and d["cat"] != "Marketplace"], 8)
    tiles = []
    for k, c, l in groups:
        if k != "cat" or not l:
            continue
        pic = next((d["img"] for d in top_picks(l, 5) if d.get("img")), "")
        tiles.append(f'<a class="tile" href="sale/{slug(c)}.html"><span class="tile-img" style="background-image:url(\'{e(pic)}\')"></span>'
                     f'<b>{e(c)}</b><small>{len(l)} deals · up to {max(d["pct"] for d in l)}% off</small></a>')
    s = s.replace("<!--FEATURED-->", "".join(card(d) for d in feat))
    s = s.replace("<!--TILES-->", "".join(tiles))
    s = s.replace("<!--GRID-->", "".join(card(d) for d in top_picks(deals, 24)))
    s = s.replace("<!--LD-->", jsonld(feat, base + "/", cfg["brand"] + " top deals"))
    open(idx, "w").write(s)
    return made
