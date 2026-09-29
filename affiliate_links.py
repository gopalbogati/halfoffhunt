"""Resolve only owner-configured affiliate links; never invent referral IDs."""
import html
import re
from urllib.parse import urlsplit, quote


def safe_https(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username and not parsed.password and not any(c.isspace() for c in value)
    except (TypeError, ValueError):
        return False


def resolve(url, templates=None, direct_links=None):
    if not safe_https(url):
        return url
    domain = urlsplit(url).hostname.lower()
    target = (direct_links or {}).get(url)
    if not target:
        templates = templates or {}
        template = templates.get(domain) or templates.get(domain.removeprefix('www.'))
        if not template:
            return url
        target = template.replace('{url}', quote(url, safe='')).replace('{raw_url}', url)
    if not safe_https(target) or re.search(r'\{[^}]*\}|YOUR_ID|YOUR_TAG|MERCHANT_ID|REPLACE_ME', target, re.I):
        raise ValueError('Affiliate link must be a complete HTTPS link generated for your approved account')
    return target


def rewrite_html(source, config):
    """Only retailer anchors explicitly marked data-affiliate can be rewritten."""
    def replace(match):
        attrs, label = match.group(1), match.group(2)
        if not re.search(r'\bdata-affiliate(?:\s|=|$)',attrs):
            return match.group(0)
        href = re.search(r'href="([^"]+)"', attrs)
        if not href:
            return match.group(0)
        original = html.unescape(href.group(1))
        target = resolve(original,config.get('templates'),config.get('direct_links'))
        if target == original:
            return match.group(0)
        attrs = attrs[:href.start(1)] + html.escape(target,quote=True) + attrs[href.end(1):]
        attrs = re.sub(r'\srel="[^"]*"','',attrs)
        return '<a'+attrs+' rel="noopener noreferrer sponsored">'+label+' <span class="affiliate-label">(Affiliate link)</span></a>'
    return re.sub(r'<a(\s[^>]*?)>(.*?)</a>',replace,source,flags=re.S)
