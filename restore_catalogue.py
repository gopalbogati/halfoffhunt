"""Bootstrap a lost Actions cache from a short-lived, public-only recovery scan."""
import gzip
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path


def restore(seed, target, now=None, receipt=None):
    now = time.time() if now is None else now
    try:
        raw = seed.read_bytes()
        fingerprint = hashlib.sha256(raw).hexdigest()
        if receipt and receipt.exists() and receipt.read_text() == fingerprint and target.exists():
            return False
        data = json.loads(gzip.decompress(raw))
        timestamp = datetime.fromisoformat(data['updated']).timestamp()
        if not 0 <= now - timestamp <= 48 * 3600 or not data['deals']:
            return False
        try:
            existing = json.loads(target.read_text())
            if datetime.fromisoformat(existing['updated']).timestamp() >= timestamp:
                failed = {s['store'] for s in existing.get('sources', []) if s['status'] != 'ok'}
                seen = {d['id'] for d in existing['deals']}
                missing = [dict(d, stale=True) for d in data['deals'] if d.get('store') in failed and d['id'] not in seen
                           and 0 <= now - d.get('checked_at', 0) <= 48 * 3600]
                if not missing:
                    return False
                existing['deals'] += missing
                existing['count'] = len(existing['deals'])
                existing['stale_count'] = sum(bool(d.get('stale')) for d in existing['deals'])
                existing['degraded'] = True
                data = existing
        except (OSError, ValueError, KeyError):
            pass
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, separators=(',', ':')))
        if receipt:
            receipt.write_text(fingerprint)
        return True
    except (OSError, ValueError, KeyError):
        return False


if __name__ == '__main__':
    root = Path(__file__).parent
    restored = restore(root / 'recovery' / 'deals.json.gz', root / 'site' / 'data' / 'deals.json', receipt=root / 'recovery_receipt.txt')
    print('Recovered recent public catalogue' if restored else 'Keeping existing catalogue; no newer unexpired recovery scan')
