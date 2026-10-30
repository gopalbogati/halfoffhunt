# Grocery coverage and reference review

The existing Python-generated static site is deployed by `.github/workflows/watch.yml` to the existing Cloudflare Pages project. Its product scanner supports Shopify feeds, not Costco or supermarket inventory APIs. The linked Tech/laptop search displayed zero matches on 30 October; the public catalogue contained 2,414 listings, all awaiting recheck at the time of inspection.

## Reference direction

OzBargain (https://www.ozbargain.com.au/) is useful for its category navigation and explicit merchant, fulfilment and expiry information. This update uses those information priorities without copying community posts, votes, branding or prices. Official retailer pages are the source of truth for local grocery offers. Existing tech, refurbished and other retailer directories remain available.

## Delivered

- `/groceries`: searchable official offer pages for Costco, Woolworths, Coles, ALDI and IGA, with category and shopping-method filters preserved in the URL.
- Separate Costco warehouse catalogues, automatically discovered from links on https://www.costco.com.au/warehouse-savings during site builds. Current catalogue seeds were obtained from that official page on 30 October 2026.
- Campaign start/end dates checked both at build time and in the browser. Expiry uses Australia/Sydney midnight after the last advertised day. Failed refreshes retain only unexpired catalogues and do not renew their check timestamps.
- Homepage grocery entry point and navigation links; laptop empty state points to broader tech and refurbished directories.
- No product price, stock level, store-specific pickup availability or discount percentage is inferred from catalogue links. These directories do not count towards the main 50%+ product grid.

## Sources

- https://www.costco.com.au/warehouse-savings
- https://www.woolworths.com.au/shop/browse/specials/half-price
- https://www.woolworths.com.au/shop/services/pickup
- https://www.coles.com.au/on-special
- https://www.coles.com.au/catalogues
- https://www.aldi.com.au/special-buys
- https://www.aldi.com.au/products/super-savers/k/1588161426952145
- https://www.iga.com.au/

## Validation and limits

56 Python tests and 3 JavaScript tests passed, including catalogue deduplication, untrusted-host rejection, invalid/future/expired dates and Sydney expiry boundaries. JavaScript syntax and static build passed. Browser pickup filtering returned only Woolworths and Coles. Grocery live SKU comparisons require a suitable retailer product feed or maintained, dated product records; this release supplies official offer discovery and current Costco catalogue links instead. Catalogue discovery depends on Costco retaining dated Joomag links and the existing deployment schedule executing.
