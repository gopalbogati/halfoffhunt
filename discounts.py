"""Render curated discount destinations; no inferred item prices or savings."""
import json
from html import escape as e
from pathlib import Path
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parent

def render(template):
    sources = sum([json.loads((ROOT / p).read_text())['sources'] for p in ['grocery_sources.json','retailer_sources.json']], [])
    payload = json.loads((ROOT / 'discount_links.json').read_text())
    rows = payload['links']
    known = {s['id']: s for s in sources}
    for row in rows:
        u = urlsplit(row['url'])
        if row['retailer_id'] not in known or u.scheme != 'https' or not u.hostname or u.username or u.password:
            raise ValueError('Invalid discount source')
    cards = []
    for source in sources:
        links = [r for r in rows if r['retailer_id'] == source['id']]
        items = []
        for r in links:
            items.append(f'<li data-types="{e(json.dumps(r["types"]))}" data-kind="{e(r["kind"])}"><a href="{e(r["url"])}" target="_blank" rel="noopener noreferrer"><span>{e(r["label"])}</span><span aria-hidden="true">↗</span></a><small>{e(r["kind"])}</small></li>')
        cards.append(f'<article class="discount-store" data-store="{e(source["name"])}"><div class="retailer-heading"><div><p class="eyebrow">{e(source["category"])}</p><h2>{e(source["name"])}</h2></div></div><ul>{"".join(items)}</ul><p class="small">{e(source["note"])}</p></article>')
    def options(values):
        return ''.join(f'<option>{e(v)}</option>' for v in sorted(set(values)))
    return (template.replace('<!--DISCOUNT_CARDS-->', ''.join(cards))
            .replace('<!--ITEM_TYPES-->', options(t for r in rows for t in r['types']))
            .replace('<!--OFFER_TYPES-->', options(r['kind'] for r in rows))
            .replace('<!--RETAILERS-->', options(s['name'] for s in sources))
            .replace('{{discount_count}}', str(len(rows))))
