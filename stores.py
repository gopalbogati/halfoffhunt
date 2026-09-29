#!/usr/bin/env python3
"""Scan Australian retailers' public sale feeds and build the public deals site data.

Reads stores.json, keeps in-stock AUD items at MIN_PCT% off or more, and writes
  site/data/deals.json   (the website reads this)
  site/feed.xml          (RSS for followers / social schedulers)
New big hits (ALERT_PCT%+ or a likely price error) are pushed to:
  NTFY_TOPIC            private phone alerts (GitHub secret)
  PUBLIC_NTFY_TOPIC     optional public follower channel
  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID   optional Telegram channel

  python3 stores.py                  # scan now
  python3 stores.py --if-due 25      # only if the last scan was 25+ minutes ago
Stdlib only.
"""
import argparse, html, json, math, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
STATE = os.path.join(HERE, "stores_state.json")
CONFIG = json.load(open(os.path.join(HERE, "site_config.json")))
MIN_PCT = CONFIG.get("min_pct", 50)          # listed on the site
ALERT_PCT = CONFIG.get("alert_pct", 70)      # pushed as an alert
ERROR_PCT = 90                               # "possible price error" badge (with was >= $100)
MAX_ALERTS_PER_RUN = 6
MAX_PAGES = 4                                # x250 products per collection
PER_STORE_CAP = 150
UA = {"User-Agent": "Mozilla/5.0 (compatible; deal-index; +https://github.com/)"}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def store_currency(domain):
    try:
        return get_json(f"https://{domain}/cart.js").get("currency")
    except Exception:
        return None


def affiliate(url, domain, affs):
    tpl = affs.get(domain) or affs.get(domain.removeprefix("www."))
    if not tpl:
        return url
    return tpl.replace("{url}", urllib.parse.quote(url, safe="")).replace("{raw_url}", url)


def best_variant(p):
    """Pick the variant to advertise. Guards against add-on variants (e.g. a $20 accessory
    sitting under a $499 'was' price) by using the median discount when variants disagree."""
    cands = []
    for v in p.get("variants", []):
        try:
            price, was = float(v["price"]), float(v.get("compare_at_price") or 0)
        except (TypeError, ValueError):
            continue
        if v.get("available") is not True or not all(map(math.isfinite, (price, was))) or price <= 0:
            continue
        pct = (1 - price / was) * 100 if was > price else 0
        cands.append((pct, price, was, v))
    if not cands:
        return None
    cands.sort(key=lambda c: c[0])
    median = cands[len(cands) // 2]
    best = cands[-1]
    if len(cands) > 1 and best[0] - median[0] > 25:
        best = median
    return best if best[0] > 0 else None


def scan_store(s, affs, now):
    cur = store_currency(s["domain"])
    if cur != "AUD":
        print(f"  - skip {s['name']}: prices in {cur}", file=sys.stderr)
        return [], {"store": s["name"], "status": "unavailable", "reason": "AUD currency not confirmed", "count": 0}
    paths = [f"collections/{c}/products.json" for c in s["collections"]] or ["products.json"]
    seen, out, failures = set(), [], 0
    for path in paths:
        for page in range(1, MAX_PAGES + 1):
            try:
                prods = get_json(f"https://{s['domain']}/{path}?limit=250&page={page}").get("products", [])
            except Exception as e:
                failures += 1
                print(f"  ! {s['name']} {path} p{page}: {e}", file=sys.stderr)
                break
            if not prods:
                break
            for p in prods:
                if p["id"] in seen:
                    continue
                seen.add(p["id"])
                b = best_variant(p)
                if not b or b[0] < MIN_PCT:
                    continue
                pct, price, was, v = b
                url = f"https://{s['domain']}/products/{p['handle']}"
                if v.get("id"):
                    url += "?variant=" + str(v["id"])
                img = (p.get("images") or [{}])[0].get("src", "")
                if img:
                    img += ("&" if "?" in img else "?") + "width=500"
                out.append({
                    "id": f"{s['domain']}:{p['id']}",
                    "title": html.unescape(p["title"]).strip(),
                    "brand": (p.get("vendor") or "").strip(),
                    "store": s["name"], "domain": s["domain"], "cat": s["cat"],
                    "type": p.get("product_type") or "",
                    "price": round(price, 2), "was": round(was, 2), "pct": math.floor(pct + 1e-9),
                    "checked_at": now, "affiliate": affiliate(url, s["domain"], affs) != url,
                    "original_url": url,
                    "error": pct >= ERROR_PCT and was >= 100 and not s.get("no_error_flag"),
                    "url": affiliate(url, s["domain"], affs), "img": img,
                    "variant": v.get("title") if v.get("title") not in (None, "Default Title") else "",
                })
            if len(prods) < 250:
                break
            time.sleep(0.4)
    out.sort(key=lambda d: -d["pct"])
    return out[:PER_STORE_CAP], {"store": s["name"], "status": "partial" if failures else "ok", "count": min(len(out), PER_STORE_CAP), "checked_at": now}


def scan_safely(store, affs, now):
    try:
        return scan_store(store, affs, now)
    except Exception as exc:
        print(f"  ! {store['name']}: {exc}", file=sys.stderr)
        return [], {"store": store["name"], "status": "unavailable", "reason": "Feed could not be processed", "count": 0}


def post(url, data, headers=None):
    try:
        req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST")
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print("  ! alert:", e, file=sys.stderr)


def alert(d):
    head = ("POSSIBLE PRICE ERROR: " if d["error"] else "") + f"{d['pct']}% off at {d['store']}"
    body = f"{d['title']} - ${d['price']:,.2f} (was ${d['was']:,.2f})"
    for topic in filter(None, [os.environ.get("NTFY_TOPIC"), os.environ.get("PUBLIC_NTFY_TOPIC") or CONFIG.get("public_ntfy_topic")]):
        post(f"https://ntfy.sh/{topic}", body.encode(), {
            "Title": head.encode("ascii", "ignore").decode(), "Click": d["url"],
            "Priority": "5" if d["error"] else "4", "Tags": "rotating_light" if d["error"] else "tag"})
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if tok and chat:
        msg = f"<b>{html.escape(head)}</b>\n{html.escape(body)}\n<a href=\"{html.escape(d['url'])}\">View deal</a>"
        if CONFIG.get("affiliate_disclosure_in_posts") and d.get("affiliate", False):
            msg += "\n#ad"
        post(f"https://api.telegram.org/bot{tok}/sendMessage", urllib.parse.urlencode(
            {"chat_id": chat, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": "false"}).encode())


def write_feed(deals, now):
    base = CONFIG["site_url"].rstrip("/")
    items = []
    for d in sorted(deals, key=lambda d: -d["first_seen"])[:100]:
        items.append(f"""<item><title>{html.escape(f"{d['pct']}% off: {d['title']} ${d['price']:,.2f} (was ${d['was']:,.2f}) @ {d['store']}")}</title>
<link>{html.escape(d['url'])}</link><guid isPermaLink="false">{html.escape(d['id'])}</guid>
<category>{html.escape(d['cat'])}</category>
<pubDate>{datetime.fromtimestamp(d['first_seen'], timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate></item>""")
    xml = f"""<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel>
<title>{html.escape(CONFIG['brand'])}</title><link>{base}/</link>
<description>{html.escape(CONFIG['tagline'])}</description><language>en-au</language>
{''.join(items)}</channel></rss>"""
    open(os.path.join(SITE, "feed.xml"), "w").write(xml)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--if-due", type=int, default=0, help="minutes between scans")
    a = ap.parse_args()
    try:
        state = json.load(open(STATE))
    except Exception:
        state = {"last": 0, "first_seen": {}, "alerted": {}}
    if a.if_due and time.time() - state["last"] < a.if_due * 60:
        print("stores: not due yet"); return
    try:
        affs = json.load(open(os.path.join(HERE, "affiliates.json"))).get("templates", {})
    except Exception:
        affs = {}
    stores = json.load(open(os.path.join(HERE, "stores.json")))["stores"]
    now = time.time()
    deals, ok = [], 0
    statuses = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = pool.map(lambda s: scan_safely(s, affs, now), stores)
        for s, (got, status) in zip(stores, results):
            statuses.append(status)
            ok += status["status"] == "ok"
            deals += got
            print(f"  {s['name']}: {len(got)} ({status['status']})")
    # A network-wide failure must not replace the last good publication with empty data.
    if not any(s["status"] == "ok" for s in statuses):
        raise RuntimeError("No complete store scans; keeping the last published data")
    fs, al = state["first_seen"], state["alerted"]
    first_run = not fs
    fresh = []
    for d in deals:
        d["first_seen"] = fs.setdefault(d["id"], now)
        if (d["pct"] >= ALERT_PCT or d["error"]) and d["id"] not in al:
            al[d["id"]] = now
            fresh.append(d)
    if not first_run:   # best few only, so followers aren't flooded
        for d in sorted(fresh, key=lambda d: (-d["error"], -d["pct"]))[:MAX_ALERTS_PER_RUN]:
            alert(d)
    live = {d["id"] for d in deals}
    state["first_seen"] = {k: v for k, v in fs.items() if k in live or now - v < 14 * 86400}
    state["alerted"] = {k: v for k, v in al.items() if now - v < 14 * 86400}
    state["last"] = now
    deals.sort(key=lambda d: (-d["error"], -d["pct"]))
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    json.dump({"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "stores": sorted({s["name"] for s in stores}), "sources": statuses, "count": len(deals), "deals": deals},
              open(os.path.join(SITE, "data", "deals.json"), "w"), separators=(",", ":"))
    write_feed(deals, now)
    json.dump(state, open(STATE, "w"))
    open(os.path.join(HERE, ".scanned"), "w").close()   # tells the workflow to redeploy the site
    print(f"stores: {len(deals)} deals at {MIN_PCT}%+ off from {ok}/{len(stores)} stores")


if __name__ == "__main__":
    main()
