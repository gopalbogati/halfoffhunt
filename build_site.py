#!/usr/bin/env python3
"""Render site_src/ into site/ using values from site_config.json ({{brand}} etc)."""
import json, os, shutil, hashlib
from datetime import date
HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(HERE, "site_config.json")))
vals = {"brand": cfg["brand"], "tagline": cfg["tagline"], "site_url": cfg["site_url"].rstrip("/"),
        "ntfy": cfg.get("public_ntfy_topic", ""), "telegram_url": cfg.get("telegram_url", ""),
        "today": date.today().strftime("%-d %B %Y")}
src, out = os.path.join(HERE, "site_src"), os.path.join(HERE, "site")
os.makedirs(out, exist_ok=True)
for name in os.listdir(src):
    p = os.path.join(src, name)
    if name.endswith((".html", ".js", ".css", ".svg", ".txt", ".xml")):
        s = open(p).read()
        for k, v in vals.items():
            s = s.replace("{{" + k + "}}", v)
        if name.endswith(".html"):
            for asset in ("app.js", "style.css"):
                digest = hashlib.sha256(open(os.path.join(src, asset), "rb").read()).hexdigest()[:12]
                s = s.replace(f'"{asset}"', f'"{asset}?v={digest}"')
        open(os.path.join(out, name), "w").write(s)
    else:
        shutil.copy(p, out)
open(os.path.join(out, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {vals['site_url']}/sitemap.xml\n")
pages = ["", "about.html", "privacy.html", "stores.html", "submit.html", "terms.html"]
open(os.path.join(out, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
    "".join(f"<url><loc>{vals['site_url']}/{p}</loc></url>" for p in pages) + "</urlset>")
open(os.path.join(out, ".nojekyll"), "w").close()
print("site built ->", out)
