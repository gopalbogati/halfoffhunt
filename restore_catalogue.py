"""Bootstrap a lost Actions cache from a short-lived, public-only recovery scan."""
import gzip
import json
import time
from datetime import datetime
from pathlib import Path


def restore(seed, target, now=None):
    now = time.time() if now is None else now
    try:
        data = json.loads(gzip.decompress(seed.read_bytes()))
        timestamp = datetime.fromisoformat(data['updated']).timestamp()
        if not 0 <= now - timestamp <= 48 * 3600 or not data['deals']:
            return False
        try:
            existing = json.loads(target.read_text())
            if datetime.fromisoformat(existing['updated']).timestamp() >= timestamp:
                return False
        except (OSError, ValueError, KeyError):
            pass
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, separators=(',', ':')))
        return True
    except (OSError, ValueError, KeyError):
        return False


if __name__ == '__main__':
    root = Path(__file__).parent
    restored = restore(root / 'recovery' / 'deals.json.gz', root / 'site' / 'data' / 'deals.json')
    print('Recovered recent public catalogue' if restored else 'Keeping existing catalogue; no newer unexpired recovery scan')
