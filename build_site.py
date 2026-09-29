#!/usr/bin/env python3
"""Render site_src/ into site/ using values from site_config.json ({{brand}} etc)."""
import json, os, shutil, hashlib
from datetime import date
from affiliate_links import rewrite_html
from pathlib import Path
from urllib.parse import quote
HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(HERE, "site_config.json")))
affiliates = json.loads(Path(HERE, "affiliates.json").read_text())
vals = {"brand": cfg["brand"], "tagline": cfg["tagline"], "site_url": cfg["site_url"].rstrip("/"),
        "ntfy": cfg.get("public_ntfy_topic", ""), "telegram_url": cfg.get("telegram_url", ""),
        "contact_email": cfg.get("contact_email", ""), "today": date.today().strftime("%-d %B %Y")}
vals["project_share_url"] = quote(vals["site_url"] + "/project.html", safe="")
src, out = os.path.join(HERE, "site_src"), os.path.join(HERE, "site")
os.makedirs(out, exist_ok=True)
for name in os.listdir(src):
    p = os.path.join(src, name)
    if name.endswith((".html", ".js", ".css", ".svg", ".txt", ".xml")):
        s = open(p).read()
        for k, v in vals.items():
            s = s.replace("{{" + k + "}}", v)
        if name.endswith(".html"):
            s = rewrite_html(s, affiliates)
            for asset in ("app.js", "tech.js", "share.js", "share-deal.js", "style.css"):
                digest = hashlib.sha256(open(os.path.join(src, asset), "rb").read()).hexdigest()[:12]
                s = s.replace(f'"{asset}"', f'"{asset}?v={digest}"')
        open(os.path.join(out, name), "w").write(s)
    else:
        shutil.copy(p, out)
open(os.path.join(out, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {vals['site_url']}/sitemap.xml\n")
import pages as P
CLEAN = "pages.dev" in vals["site_url"] or cfg.get("clean_urls", False)
def clean(p):
    return p[:-5] if CLEAN and p.endswith(".html") else p
pages = ["", "about.html", "privacy.html", "stores.html", "submit.html", "terms.html", "tech.html", "private-alerts.html", "refurbished.html", "project.html"] + P.build(out, cfg)
open(os.path.join(out, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
    "".join(f"<url><loc>{vals['site_url']}/{clean(p)}</loc></url>" for p in pages) + "</urlset>")

# Cloudflare Pages serves /x.html at /x and 308-redirects the .html form, so canonical
# addresses must be the extensionless ones there. GitHub Pages keeps .html.
if CLEAN:
    import re, glob
    for f in glob.glob(os.path.join(out, "**", "*.html"), recursive=True):
        t = open(f).read()
        t2 = re.sub(r'((?:rel="canonical" href|property="og:url" content)="[^"]*?)\.html"', r'\1"', t)
        if t2 != t:
            open(f, "w").write(t2)
# Cloudflare Web Analytics (cookieless). The token is public by design; it only identifies the site.
token = cfg.get("cf_analytics_token", "")
if token:
    import glob, re as _re
    beacon = ("<script defer src=\"https://static.cloudflareinsights.com/beacon.min.js\" "
              f"data-cf-beacon='{{\"token\": \"{token}\"}}'></script>")
    if not _re.fullmatch(r"[0-9a-f]{32}", token):
        raise SystemExit("cf_analytics_token must be 32 hex characters")
    for f in glob.glob(os.path.join(out, "**", "*.html"), recursive=True):
        t = open(f).read()
        if "cloudflareinsights" not in t and "</body>" in t:
            open(f, "w").write(t.replace("</body>", beacon + "</body>", 1))
open(os.path.join(out, ".nojekyll"), "w").close()
print("site built ->", out)
