import unittest
from affiliate_links import resolve,rewrite_html
class AffiliateTests(unittest.TestCase):
    def test_no_config_is_direct(self):
        self.assertEqual(resolve('https://shop.example/p'),'https://shop.example/p')
    def test_approved_exact_link_is_labelled(self):
        source='<a data-affiliate href="https://shop.example/p" rel="noopener">Shop</a>'
        result=rewrite_html(source,{'direct_links':{'https://shop.example/p':'https://network.example/approved?id=123'}})
        self.assertIn('Affiliate link',result)
        self.assertIn('sponsored',result)
        self.assertIn('https://network.example/approved?id=123',result)
    def test_unmarked_links_unchanged(self):
        source='<a href="https://shop.example/p">Policy</a>'
        self.assertEqual(rewrite_html(source,{'direct_links':{'https://shop.example/p':'https://network.example/id'}}),source)
    def test_placeholder_and_unsafe_link_rejected(self):
        for url in ['javascript:alert(1)','https://network.example/YOUR_ID','http://network.example/id','https://user:password@network.example/id']:
            with self.assertRaises(ValueError):resolve('https://shop.example/p',{}, {'https://shop.example/p':url})
    def test_similar_domain_does_not_match(self):
        self.assertEqual(resolve('https://shop.example.attacker.test/p',{'shop.example':'https://network.example/{url}'}),'https://shop.example.attacker.test/p')
