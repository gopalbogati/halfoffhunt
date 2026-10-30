import unittest
from datetime import datetime, timezone
from grocery import parse_costco, active

class GroceryTests(unittest.TestCase):
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)
    url = 'https://viewer.joomag.com/in-warehouse-savings-26-10-26-22-11-26/0314771001791333283'
    def test_current_catalogues_deduplicate(self):
        items = parse_costco(f'<a href="{self.url}">one</a><a href="{self.url}">two</a>', self.now)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['ends_at'], '2026-11-23T00:00:00+11:00')
        self.assertEqual(items[0]['checked_at'], self.now.isoformat())
    def test_expired_future_bad_dates_and_untrusted_hosts_excluded(self):
        urls = [self.url.replace('26-10-26-22-11-26', '01-09-26-30-09-26'),
                self.url.replace('26-10-26-22-11-26', '01-12-26-30-12-26'),
                self.url.replace('26-10-26', '99-10-26'),
                self.url.replace('viewer.joomag.com', 'viewer.joomag.com.evil.example'),
                self.url.replace('https:', 'http:')]
        self.assertEqual(parse_costco(''.join(f'<a href="{u}">offer</a>' for u in urls), self.now), [])
    def test_expiry_boundary(self):
        item = parse_costco(f'<a href="{self.url}">offer</a>', self.now)[0]
        self.assertFalse(active(item, datetime(2026, 11, 22, 13, tzinfo=timezone.utc)))
        self.assertTrue(active(item, datetime(2026, 11, 22, 12, 59, tzinfo=timezone.utc)))
    def test_missing_dates_fail_closed(self):
        self.assertFalse(active({}, self.now))

if __name__ == '__main__':
    unittest.main()
