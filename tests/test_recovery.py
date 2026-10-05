import gzip
import json
import tempfile
import unittest
from pathlib import Path
import restore_catalogue


class RecoveryTests(unittest.TestCase):
    def test_fresh_recovery_replaces_empty_or_older_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / 'recovery.json.gz'
            seed.write_bytes(gzip.compress(json.dumps({'updated':'1970-01-01T00:01:40+00:00', 'deals':[{'id':'x','checked_at':100}]}).encode()))
            target = root / 'deals.json'
            target.write_text(json.dumps({'updated':'1970-01-01T00:00:50+00:00','deals':[]}))
            self.assertTrue(restore_catalogue.restore(seed, target, now=200))
            self.assertEqual(json.loads(target.read_text())['deals'][0]['checked_at'],100)

    def test_expired_seed_cannot_replace_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);seed=root/'seed.gz';target=root/'deals.json'
            seed.write_bytes(gzip.compress(json.dumps({'updated':'1970-01-01T00:01:40+00:00','deals':[{'id':'x','checked_at':100}]}).encode()))
            target.write_text('existing')
            self.assertFalse(restore_catalogue.restore(seed,target,now=100+49*3600))
            self.assertEqual(target.read_text(),'existing')

    def test_newer_cache_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);seed=root/'seed.gz';target=root/'deals.json'
            seed.write_bytes(gzip.compress(json.dumps({'updated':'1970-01-01T00:01:40+00:00','deals':[{'id':'x','checked_at':100}]}).encode()))
            target.write_text(json.dumps({'updated':'1970-01-01T00:03:20+00:00','deals':[]}))
            before=target.read_text()
            self.assertFalse(restore_catalogue.restore(seed,target,now=300))
            self.assertEqual(target.read_text(),before)
