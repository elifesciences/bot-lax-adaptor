import sys, StringIO
import json
from os.path import join
from .base import BaseCase
import main

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

    def test_to_volume(self):
        this_year, first_year = 2016, 2011
        expected_default = this_year - first_year
        cases = ["", {}, None, []]
        for case in cases:
            self.assertEqual(main.to_volume(case), expected_default)

    def test_render_single(self):
        "ensure the scrape scrapes and has something resembling the correct structure"
        results = main.render_single(self.doc, version=1)
        self.assertTrue('article' in results)
        self.assertTrue('journal' in results)
        # NOTE! leave article validation to json schema
        # expected_article = json.load(
        # self.assertEqual(results.

    def test_main_bootstrap(self):
        "json is written to stdout"
        _orig = sys.stdout
        strbuffer = StringIO.StringIO()
        sys.stdout = strbuffer
        try:
            main.main(self.doc) # writes article json to stdout
            results = json.loads(strbuffer.getvalue())
            self.assertTrue('article' in results)
            self.assertTrue('journal' in results)
        finally:
            sys.stdout = _orig

    def test_main_bootstrap_failure(self):
        "ensure a great big exception occurs when given invalid input"
        # TODO: lets make this behaviour a bit nicer
        self.assertRaises(Exception, main.main, "aaaaaaaaaaaaaa")

    def test_main_published_excluded_if_v2(self):
        results = main.render_single(self.doc, version=1)
        self.assertTrue('published' in results['article'])
        results = main.render_single(self.doc, version=2)
        self.assertFalse('published' in results['article'])
