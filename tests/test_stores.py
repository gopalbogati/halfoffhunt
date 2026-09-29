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
            with patch('stores.STATE',str(Path(tmp)/'state.json')), patch('stores.SITE',str(site)), patch('sys.argv',['stores.py']), patch('stores.scan_safely',return_value=([],{'status':'unavailable'})):
                with self.assertRaises(RuntimeError): stores.main()
            self.assertEqual(sentinel.read_text(),'last good feed')
            self.assertFalse((Path(tmp)/'state.json').exists())
    def test_affiliate_encoding(self):
        self.assertEqual(stores.affiliate('https://example.com/p?v=2','example.com',{'example.com':'https://aff.example/?u={url}'}),'https://aff.example/?u=https%3A%2F%2Fexample.com%2Fp%3Fv%3D2')

if __name__ == '__main__': unittest.main()
