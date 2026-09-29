# Half Off Hunt

An Australian deal index: in-stock items at **50% off or more** from popular Australian online stores, checked every 30 minutes and published as a static website with phone alerts and an RSS feed.

**Live site:** https://gopalbogati.github.io/halfoffhunt/

## What runs

| Piece | File | Schedule | Output |
|---|---|---|---|
| Retailer sale scan | `stores.py` + `stores.json` | every 30 min | `site/data/deals.json`, `site/feed.xml`, alerts |
| Website | `site_src/` rendered by `build_site.py` | on each scan | GitHub Pages |
| Personal OzBargain watcher | `ozwatch.py` | every 5 min | private phone alerts only (not published) |

Everything runs on GitHub Actions (`.github/workflows/watch.yml`). Python standard library only.

## How a deal qualifies

- in stock, priced in AUD (stores that report another currency are skipped automatically)
- 50%+ below the store's own compare-at ("was") price
- products whose variants disagree wildly (e.g. a $20 accessory under a $499 "was" price) use the median variant, not the outlier
- **Possible pricing error** badge: 90%+ off an item that was $100+, except on stores marked `no_error_flag` (marketplaces with inflated RRPs)

## Configuration

- `site_config.json`: brand name, tagline, site URL, listing threshold, alert threshold, public alert topic, Telegram link
- `stores.json`: stores to scan and which sale collections to read
- `affiliates.json`: affiliate deep-link templates per store domain; links everywhere are rewritten on the next scan

## Secrets (repo Settings → Secrets → Actions)

| Secret | Purpose |
|---|---|
| `NTFY_TOPIC` | owner's private phone alerts |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | optional public Telegram channel |

## Adding a store

Most Australian Shopify stores expose `https://STORE/collections/sale/products.json`. Add an entry to `stores.json` with the sale collection handle (or `[]` to scan the catalogue), then run `python3 stores.py` locally to check it.
