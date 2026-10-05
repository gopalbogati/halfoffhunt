"""Render discovery cards from the same source manifests used by the watcher."""
from html import escape
from urllib.parse import urlsplit


def render(template, sources):
    categories = list(dict.fromkeys(c for s in sources for c in s['categories']))
    buttons = ''.join(f'<button class="chip" data-tech="{escape(c)}" aria-pressed="{str(c == "All").lower()}">{escape(c)}</button>'
                      for c in ['All'] + categories)
    cards = []
    for source in sources:
        url = urlsplit(source['url'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError('Discovery sources must use public HTTPS URLs')
        categories = escape('|'.join(source['categories']))
        label = source.get('payout') or source.get('condition') or 'Official retailer'
        cards.append(f'<article class="store-tile" data-categories="{categories}">'
                     f'<p class="eyebrow">{escape(label)}</p><h2>{escape(source["name"])}</h2>'
                     f'<p>{escape(" · ".join(source["categories"]))}</p><p>{escape(source["note"])}</p>'
                     '<p class="small">Direct link · confirm prices and terms at destination</p>'
                     f'<a data-affiliate href="{escape(source["url"])}" target="_blank" rel="noopener noreferrer">'
                     f'Visit {escape(source["name"])} ↗</a></article>')
    return template.replace('<!--SOURCE_FILTERS-->', f'<div class="chips wrapchips" role="group" aria-label="Tech category">{buttons}</div>').replace(
        '<!--SOURCE_CARDS-->', '<div class="directory">' + ''.join(cards) + '</div>')
