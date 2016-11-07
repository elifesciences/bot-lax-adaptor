import json
from os.path import join
from .base import BaseCase
import main

class ArticleScrape(BaseCase):
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

    def test_main_bootstrap(self):
        "json is written to stdout"
        results = main.main(self.doc) # writes article json to stdout
        results = json.loads(results)
        self.assertTrue('article' in results)
        self.assertTrue('journal' in results)

    def test_main_bootstrap_failure(self):
        "ensure a great big exception occurs when given invalid input"
        # TODO: lets make this behaviour a bit nicer
        self.assertRaises(Exception, main.main, "aaaaaaaaaaaaaa")

    def test_main_published_excluded_if_v2(self):
        results = main.render_single(self.doc, version=1)
        self.assertTrue('versionDate' in results['article'])
        results = main.render_single(self.doc, version=2)
        self.assertFalse('versionDate' in results['article'])

    def test_category_codes(self):
        cat_list = ['Immunology', 'Microbiology and Infectious Disease']
        expected = [{"id": "immunology", "name": "Immunology"},
                    {"id": "microbiology-infectious-disease",
                     "name": "Microbiology and Infectious Disease"}]
        self.assertEqual(main.category_codes(cat_list), expected)

    def test_note(self):
        # For test coverage
        msg = 'message'
        self.assertIsNotNone(main.note(msg))

    def test_todo(self):
        # For test coverage
        msg = 'message'
        self.assertIsNotNone(main.todo(msg))

    def test_nonxml(self):
        # For test coverage
        msg = 'message'
        self.assertIsNotNone(main.nonxml(msg))

    def test_related_article_to_related_articles_whem_empty(self):
        # For increased test coverage, test and empty list
        related_article_list = [{'junk': 'not related'}]
        expected = None
        self.assertEqual(main.related_article_to_related_articles(related_article_list), expected)

    def test_abstract_to_impact_statement(self):
        snippet = {'abstract': {'content': [
            {'type': 'paragraph', 'text': 'abstract with no DOI'}]}}
        expected = {'impactStatement': 'abstract with no DOI'}
        self.assertEqual(main.abstract_to_impact_statement(snippet), expected)

    def test_clean_if_none(self):
        snippet = {'abstract': None}
        expected = {}
        self.assertEqual(main.clean_if_none(snippet), expected)

    def test_clean_if_empty(self):
        snippet = {'researchOrganisms': []}
        expected = {}
        self.assertEqual(main.clean_if_empty(snippet), expected)

    def test_authors_rewrite(self):
        authors = [{'phoneNumbers': ['(+1) 800-555-5555']}]
        expected = [{'phoneNumbers': ['+18005555555']}]
        self.assertEqual(main.authors_rewrite(authors), expected)

    def test_display_channel_to_article_type_fails(self):
        display_channel = ['']
        expected = None
        self.assertEqual(main.display_channel_to_article_type(display_channel), expected)

    def test_licence_holder(self):
        cases = [
            ((None, 'CC-BY-4'), main.EXCLUDE_ME),
            (('John', 'CC-BY-4'), 'John'),
            (('John', 'CC-0'), main.EXCLUDE_ME),
            (('John', 'cC-0'), main.EXCLUDE_ME)
        ]
        for given, expected in cases:
            actual = main.discard_if_none_or_cc0(given)
            self.assertEqual(actual, expected, "given %r I expected %r but got %r" % (given, expected, actual))
