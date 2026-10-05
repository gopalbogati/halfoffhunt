import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import ozwatch


def deal(i=1,title='Laptop Intel Core Ultra 7 32GB $999 @ Amazon AU'):
    return dict(id=f'https://www.ozbargain.com.au/node/{i}',title=title,link=f'https://www.ozbargain.com.au/node/{i}',cats=['Computing'],votes_pos=5,votes_neg=0,comments=0,expiry=None)

class TechTests(unittest.TestCase):
    def test_rotation_covers_every_store_without_clock_dependence(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ozwatch,'FEED_CURSOR',str(Path(tmp)/'cursor.json')):
            seen=[]
            for _ in range((len(ozwatch.STORE_FEEDS)+3)//4):seen.extend(ozwatch.rotated_stores())
            self.assertEqual(seen,ozwatch.STORE_FEEDS)
    def test_laptop_below_fifty_percent_matches(self):
        score,reasons=ozwatch.classify(deal())
        self.assertGreaterEqual(score,40)
        self.assertIn('Tech: Laptops',reasons)
    def test_console_and_accessory_separated(self):
        self.assertEqual(ozwatch.tech_matches('Sony PS5 Slim Disc Console $699',699,5),['PS5 consoles'])
        self.assertNotIn('PS5 consoles',ozwatch.tech_matches('PS5 DualSense Controller $89',89,20))
        self.assertNotIn('PS5 consoles',ozwatch.tech_matches('PS5 Game Collectors Edition $300',300,20))
    def test_laptop_stand_and_low_votes_excluded(self):
        self.assertEqual(ozwatch.tech_matches('Laptop stand $299',299,10),[])
        self.assertEqual(ozwatch.tech_matches('ThinkPad Laptop $999',999,2),[])
    def test_used_condition_and_budget_laptop(self):
        self.assertEqual(ozwatch.condition_label('[Refurb] ThinkPad T480 $149'),'Refurbished / ex-lease')
        self.assertEqual(ozwatch.condition_label('Preowned PS5 Console $499'),'Second-hand / preowned')
        self.assertEqual(ozwatch.condition_label('Open-box iPad $399'),'Open-box / ex-demo')
        self.assertEqual(ozwatch.condition_label('Laptop $999'),'Condition not stated')
        self.assertIn('Laptops',ozwatch.tech_matches('[Refurb] ThinkPad $149',149,5))
    def test_storage_and_desktop_coverage(self):
        self.assertIn('Storage & hard drives',ozwatch.tech_matches('WD Elements 8TB External Hard Drive $199',199,5))
        self.assertIn('Desktop PCs',ozwatch.tech_matches('Mini PC Intel N100 16GB $249',249,5))
        self.assertNotIn('Storage & hard drives',ozwatch.tech_matches('USB HDD enclosure $39',39,5))

    def test_ps5_games_are_separate_from_accessories(self):
        matches=ozwatch.tech_matches('[PS5] Astro Bot Game $9',9,5)
        self.assertIn('PS5 games',matches)
        self.assertNotIn('Gaming accessories',matches)
        self.assertNotIn('PS5 games',ozwatch.tech_matches('PS5 DualSense Controller $89',89,5))

    def test_trade_in_offer_can_match_without_purchase_price(self):
        matches=ozwatch.tech_matches('Bonus trade-in credit for iPhone and Samsung phones',None,5)
        self.assertIn('Trade-in & buyback',matches)
        self.assertEqual(ozwatch.tech_matches('Trade-in paperback books',None,5),[])

    def test_expiry_handles_naive_dates(self):
        self.assertTrue(ozwatch.is_expired(dict(title='PS5',expiry='2020-01-01T00:00:00'),datetime.now(timezone.utc)))
    def test_alert_mode_caches_no_content_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            history=Path(tmp)/'history.json'
            history.write_text(json.dumps({ozwatch.alert_key('baseline'):ozwatch.time.time()}))
            capture=io.StringIO()
            with patch.object(ozwatch,'ALERTS_ONLY',True),patch.object(ozwatch,'ALERT_STATE',str(history)),patch.object(ozwatch,'FEEDS',['example']),patch.object(ozwatch,'rotated_stores',return_value=[]),patch.object(ozwatch,'fetch',return_value=b'feed'),patch.object(ozwatch,'parse_feed',side_effect=lambda _: [deal()]),patch.object(ozwatch,'push') as push,patch.object(ozwatch,'write_html') as write,patch.object(ozwatch,'save_state') as save,contextlib.redirect_stdout(capture):
                first=ozwatch.run_once();second=ozwatch.run_once()
            self.assertEqual(first['notifications'],1)
            self.assertEqual(second['notifications'],0)
            self.assertEqual(push.call_count,1)
            write.assert_not_called();save.assert_not_called()
            self.assertNotIn('Laptop',history.read_text()+capture.getvalue())
            self.assertNotIn('amazon',history.read_text().lower())
            self.assertTrue(all(len(k)==64 for k in json.loads(history.read_text())))
    def test_first_run_silent_and_alert_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            history=Path(tmp)/'history.json'
            with patch.object(ozwatch,'ALERTS_ONLY',True),patch.object(ozwatch,'ALERT_STATE',str(history)),patch.object(ozwatch,'FEEDS',['example']),patch.object(ozwatch,'rotated_stores',return_value=[]),patch.object(ozwatch,'fetch',return_value=b'feed'),patch.object(ozwatch,'parse_feed',side_effect=lambda _: [deal(i) for i in range(10)]),patch.object(ozwatch,'push') as push,contextlib.redirect_stdout(io.StringIO()):
                result=ozwatch.run_once()
                self.assertEqual(result['notifications'],0)
                self.assertEqual(push.call_count,0)
                history.write_text(json.dumps({ozwatch.alert_key('baseline'):ozwatch.time.time()}))
                result=ozwatch.run_once()
                self.assertEqual(result['notifications'],6)
    def test_feed_failure_does_not_overwrite_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            history=Path(tmp)/'history.json';history.write_text('{}')
            with patch.object(ozwatch,'ALERTS_ONLY',True),patch.object(ozwatch,'ALERT_STATE',str(history)),patch.object(ozwatch,'FEEDS',['example']),patch.object(ozwatch,'rotated_stores',return_value=[]),patch.object(ozwatch,'fetch',side_effect=OSError('unavailable')):
                with self.assertRaises(RuntimeError):ozwatch.run_once()
            self.assertEqual(history.read_text(),'{}')

    def test_failed_phone_delivery_is_retried_next_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            history=Path(tmp)/'history.json'
            history.write_text(json.dumps({ozwatch.alert_key('baseline'):ozwatch.time.time()}))
            with patch.object(ozwatch,'ALERTS_ONLY',True), patch.object(ozwatch,'ALERT_STATE',str(history)), patch.object(ozwatch,'FEEDS',['example']), patch.object(ozwatch,'rotated_stores',return_value=[]), patch.object(ozwatch,'fetch',return_value=b'feed'), patch.object(ozwatch,'parse_feed',side_effect=lambda _: [deal()]), patch.object(ozwatch,'NTFY_TOPIC','test-topic'), patch('ozwatch.urllib.request.urlopen',side_effect=OSError('delivery failed')), contextlib.redirect_stdout(io.StringIO()):
                ozwatch.run_once()
            self.assertNotIn(ozwatch.alert_key(deal()['id']),json.loads(history.read_text()))

if __name__=='__main__':unittest.main()
