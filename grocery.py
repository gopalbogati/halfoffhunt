"""Build an honest grocery directory and discover dated Costco catalogues.

No product prices, pickup stock or discounts are inferred from catalogue links.
Failed refreshes retain only unexpired catalogues with their original timestamp.
"""
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            self.urls.append(html.unescape(attrs['href']))


def active(c, now):
    try:
        return datetime.fromisoformat(c['starts_at']) <= now < datetime.fromisoformat(c['ends_at'])
    except (KeyError, ValueError, TypeError):
        return False


def parse_costco(page, now):
    parser = Links()
    parser.feed(page)
    out = {}
    for url in parser.urls:
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'viewer.joomag.com':
            continue
        match = re.search(r'/(spring-savings|in-warehouse-savings)-(\d{2}-\d{2}-\d{2})-(\d{2}-\d{2}-\d{2})/', parsed.path)
        if not match:
            continue
        try:
            start, end = [datetime.strptime(x, '%d-%m-%y') for x in match.groups()[1:]]
        except ValueError:
            continue
        # Australia-wide campaign: expire conservatively at end of day in Sydney.
        from zoneinfo import ZoneInfo
        from datetime import timedelta
        tz = ZoneInfo('Australia/Sydney')
        item = {'id': parsed.path.rstrip('/').split('/')[-1], 'store':'costco',
                'title': match[1].replace('-', ' ').title(), 'url':url,
                'starts_at':start.replace(tzinfo=tz).isoformat(),
                'ends_at':(end + timedelta(days=1)).replace(tzinfo=tz).isoformat(),
                'date_label':f'{start:%d %b} – {end:%d %b %Y}',
                'checked_at':now.isoformat(), 'stale':False}
        if active(item, now):
            out[url] = item
    return list(out.values())


def build(out, refresh=True):
    out = Path(out)
    now = datetime.now(timezone.utc)
    seed = ROOT / 'grocery_catalogues.json'
    cache = out / 'data/groceries.json'
    previous = json.loads(seed.read_text()).get('catalogues', []) if seed.exists() else []
    if cache.exists():
        try:
            previous = json.loads(cache.read_text()).get('catalogues', previous)
        except (ValueError, OSError):
            pass
    catalogues = [dict(c, stale=True) for c in previous if active(c, now)]
    status = 'unavailable'
    if refresh:
        try:
            req = Request('https://www.costco.com.au/warehouse-savings', headers={'User-Agent':'HalfOffHunt/1.0 (+https://halfoffhunt.pages.dev)'})
            with urlopen(req, timeout=15) as response:
                found = parse_costco(response.read(4_000_000).decode('utf-8'), now)
            if found:
                catalogues, status = found, 'ok'
            else:
                status = 'no-current-catalogues'
        except (OSError, ValueError):
            pass
    sources = json.loads((ROOT / 'grocery_sources.json').read_text())['sources']
    sources += json.loads((ROOT / 'retailer_sources.json').read_text())['sources']
    data = {'sources': sources, 'catalogues':catalogues, 'catalogue_status':status,
            'generated_at':now.isoformat()}
    (out / 'data').mkdir(parents=True, exist_ok=True)
    (out / 'data/groceries.json').write_text(json.dumps(data, indent=2) + '\n')
    return data

if __name__ == '__main__':
    build(ROOT / 'site')
