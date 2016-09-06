import os
from os.path import join
from unittest import TestCase
import main

class BaseCase(TestCase):
    maxDiff = None
    this_dir = os.path.realpath(os.path.dirname(__file__))
    fixtures_dir = join(this_dir, 'fixtures')

class TestArticleScrape(BaseCase):
    def setUp(self):
        self.doc = join(self.fixtures_dir, 'elife-09560-v1.xml')
        self.doc_json = join(self.fixtures_dir, 'elife-09560-v1.json')
        self.soup = main.to_soup(self.doc)

    def tearDown(self):
        pass

    def test_item_id(self):
        expected_item_id = '10.7554/eLife.09560'
        self.assertEqual(main.doi(self.soup), expected_item_id)

    def test_basic_scrape(self):
        "ensure the scrape scrapes and has something resembling the correct structure"
        results = main.render_single(self.doc)
        self.assertTrue(results.has_key('article'))
        self.assertTrue(results.has_key('journal'))
        # NOTE! leave article validation to json schema
        #expected_article = json.load(
        #self.assertEqual(results.
