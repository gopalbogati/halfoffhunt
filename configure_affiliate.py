#!/usr/bin/env python3
"""Save a network-generated affiliate URL for an approved destination."""
import argparse,json
from pathlib import Path
from affiliate_links import safe_https,resolve


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination',required=True,help='Original retailer HTTPS URL on the site')
    p.add_argument('--affiliate-url',required=True,help='Complete link copied from your approved network account; no API secrets')
    p.add_argument('--confirm-approved',action='store_true',help='Confirm this retailer and promotional placement are approved for your account')
    a=p.parse_args()
    if not a.confirm_approved:p.error('Only add links after retailer/network approval; pass --confirm-approved when approved')
    if not safe_https(a.destination):p.error('Destination must be an HTTPS URL')
    try:resolve(a.destination,{}, {a.destination:a.affiliate_url})
    except ValueError as e:p.error(str(e))
    path=Path(__file__).with_name('affiliates.json')
    config=json.loads(path.read_text());config.setdefault('direct_links',{})[a.destination]=a.affiliate_url
    path.write_text(json.dumps(config,indent=2)+'\n')
    print('Saved. Build, review the labelled link, then commit and deploy. No account approval or commission is guaranteed by this command.')
if __name__=='__main__':main()
