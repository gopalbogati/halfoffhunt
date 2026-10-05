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

    def test_newer_partial_cache_recovers_only_failed_stores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);seed=root/'seed.gz';target=root/'deals.json'
            old=[{'id':'a','store':'Failed','checked_at':100},{'id':'b','store':'Completed','checked_at':100}]
            seed.write_bytes(gzip.compress(json.dumps({'updated':'1970-01-01T00:01:40+00:00','deals':old}).encode()))
            target.write_text(json.dumps({'updated':'1970-01-01T00:03:20+00:00','deals':[], 'sources':[{'store':'Failed','status':'partial'},{'store':'Completed','status':'ok'}]}))
            self.assertTrue(restore_catalogue.restore(seed,target,now=300))
            result=json.loads(target.read_text())
            self.assertEqual(result['deals'],[dict(old[0],stale=True)])
            self.assertEqual(result['updated'],'1970-01-01T00:03:20+00:00')

    def test_seed_is_applied_once_so_removed_products_stay_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);seed=root/'seed.gz';target=root/'deals.json';receipt=root/'receipt'
            seed.write_bytes(gzip.compress(json.dumps({'updated':'1970-01-01T00:01:40+00:00','deals':[{'id':'a','store':'Failed','checked_at':100}]}).encode()))
            self.assertTrue(restore_catalogue.restore(seed,target,now=200,receipt=receipt))
            target.write_text(json.dumps({'updated':'1970-01-01T00:03:20+00:00','deals':[], 'sources':[{'store':'Failed','status':'partial'}]}))
            self.assertFalse(restore_catalogue.restore(seed,target,now=300,receipt=receipt))
            self.assertEqual(json.loads(target.read_text())['deals'],[])

    def test_successful_empty_scan_consumes_seed_before_later_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);seed=root/'seed.gz';target=root/'deals.json';receipt=root/'receipt'
            seed.write_bytes(gzip.compress(json.dumps({'updated':'1970-01-01T00:01:40+00:00','deals':[{'id':'a','store':'Test','checked_at':100}]}).encode()))
            for status in ['ok','partial']:
                target.write_text(json.dumps({'updated':'1970-01-01T00:03:20+00:00','deals':[], 'sources':[{'store':'Test','status':status}]}))
                self.assertFalse(restore_catalogue.restore(seed,target,now=300,receipt=receipt))
                self.assertEqual(json.loads(target.read_text())['deals'],[])
