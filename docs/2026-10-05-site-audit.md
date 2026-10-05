# Half Off Hunt repair and coverage audit

## Observed fault

- Live homepage returned HTTP 200 on 5 October 2026. The outage was an empty catalogue, not a confirmed DNS/hosting outage.
- Public data updated 4 October 22:00 UTC contained zero deals. Only Hydro Flask completed; 32 of 33 sources were unavailable or incomplete.
- GitHub run https://github.com/gopalbogati/halfoffhunt/actions/runs/37238283020 succeeded despite that loss of coverage. Run https://github.com/gopalbogati/halfoffhunt/actions/runs/37226008350 failed during retailer scanning.
- Retailer product endpoints returned widespread HTTP 429 from GitHub runners. The existing guard required only one complete source, allowing one empty source to wipe all previous listings.
- The private RSS step reported 13/13 feeds read, 310 items, 65 matches and one notification considered. This proves feed processing, not delivery to the handset.
- A diagnostic retailer scan from the owner's computer (outgoing alerts disabled) recovered 2,542 listings, including 195 Tech listings, from 31/33 complete scans.

## Implemented approach

Keep the existing static Cloudflare site and private phone alert channel. Preserve recently checked failed-source prices with explicit stale labels and a 48-hour limit. Never retain products observed at full price or sold out. Publish frontend repairs even during scanner failures. Seed the erased cache using a compressed, timestamped public recovery scan.

Use official retailer and quote-service links for broader coverage without presenting invented prices. Generate directories from manifests, and add explicit private matching rules for games, desktop PCs, hard drives and trade-ins. An authorised retailer/API feed would be the next step for automatic public inventories from these new retailers; an aggressive cross-site scraper would inherit the current availability problem.

## Source references

- https://www.computeralliance.com.au/see-more/specials/
- https://www.jw.com.au/ex-demo
- https://www.msy.com.au/
- https://www.mightyape.com.au/ma/shop/category/games/playstation/ps5/ps5-games/
- https://store.playstation.com/en-au/category/4cbf39e2-5749-4970-ba81-93a489e4570c/1
- https://www.ple.com.au/Categories/724/Hard-Drives-and-SSDs-External
- https://www.apple.com/au/shop/trade-in
- https://www.jbhifi.com.au/pages/tradein
- https://mobilemonster.com.au/sell-your-device
- https://www.cashconverters.com.au/sell

These links were researched on 5 October 2026. They do not establish that a retailer always offers the lowest price. Buyback prices require individual device and condition quotes.

## Operational limits

GitHub scheduled runs were observed several hours apart. Offsetting the cron expression reduces top-of-hour contention but does not provide a timing guarantee. Retailer throttling remains an external dependency; cached prices expire and official discovery links remain usable. No new paid service, account, automatic device sale, social post or public republication of private community content is part of this change.
