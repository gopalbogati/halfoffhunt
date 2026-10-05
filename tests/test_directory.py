import unittest
import directory


class DirectoryTests(unittest.TestCase):
    def test_source_is_searchable_and_html_is_escaped(self):
        row = dict(name='A & B', categories=['Storage & hard drives'],
                   url='https://example.com/', note='Check <condition>', payout='Cash')
        output = directory.render('<!--SOURCE_FILTERS--><!--SOURCE_CARDS-->', [row])
        self.assertIn('data-tech="Storage &amp; hard drives"', output)
        self.assertIn('A &amp; B', output)
        self.assertIn('Check &lt;condition&gt;', output)
        self.assertIn('Cash', output)

    def test_non_https_sources_are_rejected(self):
        row = dict(name='Unsafe', categories=[], url='javascript:alert(1)', note='')
        with self.assertRaises(ValueError):
            directory.render('<!--SOURCE_CARDS-->', [row])
