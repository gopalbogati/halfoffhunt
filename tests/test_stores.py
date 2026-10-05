import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import stores

class ScannerTests(unittest.TestCase):
    def variant(self, price='50', was='100', available=True, **kw):
        return dict(price=price, compare_at_price=was, available=available, id=321, **kw)
    def test_stock_and_finite_prices(self):
        for variant in [self.variant(available=False), self.variant(price='NaN'), self.variant(was='inf'), self.variant(price='0'), {'price':'50','compare_at_price':'100'}]:
            self.assertIsNone(stores.best_variant({'variants':[variant]}))
    def test_normal_discount(self):
        self.assertEqual(stores.best_variant({'variants':[self.variant()]})[:3], (50,50,100))
    def test_unknown_currency_rejected(self):
        with patch('stores.store_currency', return_value=None):
            deals,status=stores.scan_store({'name':'Test','domain':'example.com'}, {}, 1)
        self.assertEqual(deals,[])
        self.assertEqual(status['status'],'unavailable')
    def test_variant_url_and_discount_floor(self):
        store={'name':'Test','domain':'example.com','collections':[],'cat':'Tech'}
        product={'id':1,'handle':'test','title':'Test','variants':[self.variant(price='49.1')]}
        with patch('stores.store_currency',return_value='AUD'), patch('stores.get_json',return_value={'products':[product]}):
            deals,status=stores.scan_store(store,{},100)
        self.assertEqual(deals[0]['url'],'https://example.com/products/test?variant=321')
        self.assertEqual(deals[0]['pct'],50)
        self.assertFalse(deals[0]['affiliate'])
        self.assertEqual(status['status'],'ok')
    def test_feed_failure_is_visible(self):
        store={'name':'Test','domain':'example.com','collections':[],'cat':'Tech'}
        with patch('stores.store_currency',return_value='AUD'), patch('stores.get_json',side_effect=ValueError('bad feed')):
            deals,status=stores.scan_store(store,{},100)
        self.assertEqual(status['status'],'partial')
    def test_total_failure_preserves_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            site=Path(tmp)/'site'; site.mkdir(); sentinel=site/'feed.xml'; sentinel.write_text('last good feed')
            with patch('stores.STATE',str(Path(tmp)/'state.json')), patch('stores.SITE',str(site)), patch('sys.argv',['stores.py']), patch('stores.scan_safely',return_value=([],{'store':'Test','status':'unavailable'})):
                with self.assertRaises(RuntimeError): stores.main()
            self.assertEqual(sentinel.read_text(),'last good feed')
            self.assertFalse((Path(tmp)/'state.json').exists())
    def test_failed_store_keeps_recent_price_without_refreshing_timestamp(self):
        old = {'id':'x:1','store':'Failed','checked_at':100,'price':50}
        merged = stores.merge_previous([], [{'store':'Failed','status':'partial'}], [old], 200)
        self.assertEqual(merged, [dict(old, stale=True)])

    def test_successful_empty_store_removes_old_products(self):
        old = {'id':'x:1','store':'Empty','checked_at':100}
        self.assertEqual(stores.merge_previous([], [{'store':'Empty','status':'ok'}], [old], 200), [])

    def test_stale_prices_expire_and_removed_stores_do_not_return(self):
        old = [{'id':'x:1','store':'Failed','checked_at':100}, {'id':'y:1','store':'Removed','checked_at':100}]
        self.assertEqual(stores.merge_previous([], [{'store':'Failed','status':'partial'}], old, 100 + 49*3600), [])
        self.assertEqual(stores.merge_previous([], [], old, 200), [])

    def test_fresh_product_replaces_cached_copy(self):
        old = {'id':'x:1','store':'Failed','checked_at':100,'price':50}
        new = dict(old, checked_at=200, price=40)
        self.assertEqual(stores.merge_previous([new], [{'store':'Failed','status':'partial'}], [old], 200), [new])

    def test_rechecked_full_price_product_is_not_restored_on_partial_scan(self):
        store={'name':'Test','domain':'example.com','collections':['sale','clearance'],'cat':'Tech'}
        product={'id':1,'handle':'test','title':'Test','variants':[self.variant(price='100')]}
        with patch('stores.store_currency',return_value='AUD'), patch('stores.get_json',side_effect=[{'products':[product]},ValueError('failure')]):
            deals,status=stores.scan_store(store,{},200)
        previous=[{'id':'example.com:1','store':'Test','checked_at':100,'price':50}]
        self.assertEqual(stores.merge_previous(deals,[status],previous,200),[])

    def test_failed_alert_post_reports_failure(self):
        with patch('stores.urllib.request.urlopen',side_effect=OSError('offline')):
            self.assertIs(stores.post('https://example.com',b'test'),False)

    def test_capped_or_failed_alerts_stay_pending(self):
        items=[{'id':str(i),'error':False,'pct':80} for i in range(8)]
        alerted={}
        with patch('stores.alert',side_effect=[False,True,True,True,True,True]):
            stores.send_alerts(items,alerted,100,False)
        self.assertEqual(set(alerted),{'1','2','3','4','5'})

    def test_partial_delivery_does_not_repeat_successful_phone_push(self):
        from types import SimpleNamespace
        sent=[]
        def deliver(req, **kwargs):
            sent.append(req.full_url)
            if req.full_url.endswith('/public-test') and sent.count(req.full_url)==1:
                raise OSError('public unavailable')
            return SimpleNamespace(read=lambda: b'ok')
        item=dict(id='one',title='Test',price=20,was=100,pct=80,error=False,store='Test',url='https://example.com')
        receipts=set()
        with patch.dict('os.environ',{'NTFY_TOPIC':'private-test','PUBLIC_NTFY_TOPIC':'public-test','TELEGRAM_BOT_TOKEN':''}), patch.object(stores,'SETTINGS',{'modes':{'store_deals':'push'}}), patch('stores.urllib.request.urlopen',side_effect=deliver):
            self.assertFalse(stores.alert(item,receipts))
            self.assertTrue(stores.alert(item,receipts))
        self.assertEqual(sent.count('https://ntfy.sh/private-test'),1)
        self.assertEqual(sent.count('https://ntfy.sh/public-test'),2)

    def test_missing_products_is_not_a_successful_empty_feed(self):
        store={'name':'Test','domain':'example.com','collections':[],'cat':'Tech'}
        with patch('stores.store_currency',return_value='AUD'), patch('stores.get_json',return_value={}):
            deals,status=stores.scan_store(store,{},100)
        self.assertNotEqual(status['status'],'ok')

    def test_rate_limit_stops_remaining_collections(self):
        from urllib.error import HTTPError
        store={'name':'Test','domain':'example.com','collections':['sale','clearance'],'cat':'Tech'}
        with patch('stores.store_currency',return_value='AUD'), patch('stores.get_json',side_effect=HTTPError('https://example.com',429,'rate limited',{},None)) as fetch:
            deals,status=stores.scan_store(store,{},100)
        self.assertEqual(fetch.call_count,1)
        self.assertEqual(status['reason'],'Rate limited by retailer')

    def test_affiliate_encoding(self):
        self.assertEqual(stores.affiliate('https://example.com/p?v=2','example.com',{'example.com':'https://aff.example/?u={url}'}),'https://aff.example/?u=https%3A%2F%2Fexample.com%2Fp%3Fv%3D2')

if __name__ == '__main__': unittest.main()
