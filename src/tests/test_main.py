import json
from os.path import join
from .base import BaseCase
import main

class ArticleScrape(BaseCase):
    def setUp(self):
        self.doc = join(self.fixtures_dir, 'elife-09560-v1.xml')
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

    '''
    def test_clean_if_none(self):
        snippet = {'abstract': None}
        expected = {}
        self.assertEqual(main.clean_if_none(snippet), expected)

    def test_clean_if_empty(self):
        snippet = {'researchOrganisms': []}
        expected = {}
        self.assertEqual(main.clean_if_empty(snippet), expected)
    '''

    def test_display_channel_to_article_type_fails(self):
        display_channel = ['']
        expected = None
        self.assertEqual(main.display_channel_to_article_type(display_channel), expected)

    def test_discard_if_none_or_empty(self):
        cases = [
            (None, main.EXCLUDE_ME),
            ('not none', 'not none'),
            ([], main.EXCLUDE_ME),
            ({}, main.EXCLUDE_ME)
        ]
        for given, expected in cases:
            actual = main.discard_if_none_or_empty(given)
            self.assertEqual(actual, expected, "given %r I expected %r but got %r" % (given, expected, actual))

    def test_licence_holder(self):
        cases = [
            ((None, 'CC-BY-4'), main.EXCLUDE_ME),
            (('John', 'CC-BY-4'), 'John'),
            (('John', 'CC0-1.0'), main.EXCLUDE_ME),
            (('Jane', 'cC0-2.pants'), main.EXCLUDE_ME)
        ]
        for given, expected in cases:
            actual = main.discard_if_none_or_cc0(given)
            self.assertEqual(actual, expected, "given %r I expected %r but got %r" % (given, expected, actual))

    def test_pdf_uri(self):
        given = ('research-article', 1234, 1)
        #expected = 'https://cdn.elifesciences.org/articles/01234/elife-01234-v1.pdf'
        expected = 'https://publishing-cdn.elifesciences.org/01234/elife-01234-v1.pdf'
        self.assertEqual(expected, main.pdf_uri(given))

    def test_pdf_uri_bad(self):
        cases = [
            ("asdf", "asdf", "asdf"),
        ]
        for given in cases:
            self.assertRaises(ValueError, main.pdf_uri, given)

    def test_fix_filenames(self):
        given = [
            {"type": "image", "uri": "foo"},
            {"type": "image", "uri": "foo.bar"}
        ]
        expected = [
            {"type": "image", "uri": "foo.jpg"},
            {"type": "image", "uri": "foo.bar"}, # no clobbering
        ]
        self.assertEqual(main.fix_extensions(given), expected)

    def test_expand_uris(self):
        msid = 1234
        given = [
            {"uri": "foo.bar"},
            {"uri": "http://foo.bar/baz.bup"},
            {"uri": "https://foo.bar/baz.bup"},
        ]
        expected = [
            {"uri": main.cdnlink(msid, "foo.bar"), "filename": "foo.bar"},
            # already-expanded uris are preserved
            {"uri": "http://foo.bar/baz.bup"},
            {"uri": "https://foo.bar/baz.bup"},
        ]
        self.assertEqual(main.expand_uris(msid, given), expected)


class KitchenSink(BaseCase):
    def setUp(self):
        self.doc = join(self.fixtures_dir, 'elife-00666-v1.xml')
        self.soup = main.to_soup(self.doc)

    def test_video(self):
        result = main.render_single(self.doc, version=1)
        media = result['article']['body'][1]['content'][5]['content'][1]

        def tod(d):
            return json.loads(json.dumps(d))

        expected_media = {
            "type": "video",
            "doi": "https://doi.org/10.7554/eLife.00666.016",
            "id": "video1",
            "label": "Video 1.",
            "title": "\n                                A descirption of the eLife editorial process.\n                            ",
            "sources": [],
            "sourceData": [{
                "doi": "https://doi.org/10.7554/eLife.00666.036",
                "id": "video1sdata1",
                "label": u"Video 1\u2014Source data 1.",
                "title": "Title of the source code.",
                "mediaType": "application/xml",
                "caption": [
                    {
                        "type": "paragraph",
                        "text": "Legend of the source code.",
                    },
                ],
                "uri": main.cdnlink("00666", "elife-00666-video4-data1.xlsx"),
                "filename": "elife-00666-video4-data1.xlsx"
            }]
        }
        self.assertEqual(tod(media), tod(expected_media))
