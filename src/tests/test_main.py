import os
import json
from os.path import join
import base
import main, utils, conf

class Cmd(base.BaseCase):
    def setUp(self):
        self.cwd = os.getcwd()
        os.chdir(conf.PROJECT_DIR)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_scraper_can_be_called(self):
        args = ['python', 'src/main.py', '-h']
        rc, stdout = utils.run_script(args)
        self.assertEqual(rc, 0)

    def test_scraper_can_scrape(self):
        "a basic scrape of xml can be done"
        args = ['python', 'src/main.py', 'src/tests/fixtures/elife-16695-v1.xml']
        rc, stdout = utils.run_script(args)
        self.assertEqual(rc, 0)
        expected_output = base.load_ajson(join(self.fixtures_dir, 'elife-16695-v1.xml.json'))
        actual_output = base.load_ajson(stdout, string=True)
        self.assertEqual(actual_output, expected_output)

    def test_scraper_can_scrape_with_overrides(self):
        "overrides must be passed in as pairs"
        args = [
            'python', 'src/main.py', 'src/tests/fixtures/elife-16695-v1.xml',
            '--override', 'title', '"foo"',
            '--override', 'abstract', '"bar"'
        ]
        rc, stdout = utils.run_script(args)
        self.assertEqual(rc, 0)

        expected_output = base.load_ajson(join(self.fixtures_dir, 'elife-16695-v1.xml.json'))
        expected_output['article']['title'] = 'foo'
        expected_output['article']['abstract'] = 'bar'

        actual_output = base.load_ajson(stdout, string=True)
        self.assertEqual(actual_output, expected_output)

    def test_scraper_fails_on_bad_overrides(self):
        "overrides must be passed in as pairs"
        args = [
            'python', 'src/main.py', 'src/tests/fixtures/elife-16695-v1.xml',
            '--override', 'title',
        ]
        rc, stdout = utils.run_script(args)
        self.assertEqual(rc, 2)


class ArticleScrape(base.BaseCase):
    def setUp(self):
        self.doc = join(self.fixtures_dir, 'elife-09560-v1.xml')
        self.small_doc = join(self.fixtures_dir, 'elife-16695-v1.xml')
        self.soup = main.to_soup(self.doc)

    def tearDown(self):
        pass

    def test_missing_var(self):
        self.assertRaises(KeyError, main.getvar('foo'), {}, None)

    def test_item_id(self):
        expected_item_id = '10.7554/eLife.09560'
        self.assertEqual(main.doi(self.soup), expected_item_id)

    def test_to_volume(self):
        cases = [
            (('2012-12-31', None), 1),
            (('2013-12-31', None), 2),
            (('2014-12-31', None), 3),
            (('2015-12-31', None), 4),
            (('2016-12-31', None), 5),
            (('2017-12-31', None), 6),
            (('2018-12-31', None), 7), # etc

            # various other empty values
            (('2016-12-31', ""), 5),
            (('2016-12-31', {}), 5),
            (('2016-12-31', []), 5),
        ]
        for year_volume_pair, expected in cases:
            got = main.to_volume(year_volume_pair)
            self.assertEqual(expected, got, "given %r, I expected %r got %r" % (year_volume_pair, expected, got))

    def test_render_single(self):
        "ensure the scrape scrapes and has something resembling the correct structure"
        results = main.render_single(self.doc, version=1)
        self.assertTrue('article' in results)
        self.assertTrue('journal' in results)
        # NOTE! leave article validation to json schema

    def test_main_bootstrap(self):
        "json is written to stdout"
        results = main.main(self.small_doc) # writes article json to stdout
        results = json.loads(results)
        self.assertTrue('article' in results)
        self.assertTrue('journal' in results)

    def test_main_bootstrap_failure(self):
        "ensure a great big exception occurs when given invalid input"
        # TODO: lets make this behaviour a bit nicer
        self.assertRaises(Exception, main.main, "aaaaaaaaaaaaaa")

    def test_main_published_dummied_if_v2(self):
        # when version == 1, we just use the pubdate in the xml
        results = main.render_single(self.small_doc, version=1)
        self.assertEqual(results['article']['versionDate'], '2016-08-16T00:00:00Z')
        # when version > 1, we rely on lax to fill in the actual value,
        # passing an obviously false placeholder to avoid validation failure
        results = main.render_single(self.small_doc, version=2)
        self.assertEqual(results['article']['versionDate'], main.DUMMY_DATE)

    def test_category_codes(self):
        cat_list = ['Immunology', 'Microbiology and Infectious Disease']
        expected = [{"id": "immunology", "name": "Immunology"},
                    {"id": "microbiology-infectious-disease",
                     "name": "Microbiology and Infectious Disease"}]
        self.assertEqual(main.category_codes(cat_list), expected)

    def test_check_authors(self):
        cases = [
            {"snippet": {"type": "research-article", "authors": [{"type": "person", "competingInterests": "A competing interest"}]}},
            {"snippet": {"type": "correction", "authors": [{"type": "person"}]}}
        ]
        for snippet in cases:
            self.assertEqual(main.check_authors(snippet), snippet)

    def test_check_authors_failure(self):
        snippet = {"snippet": {"type": "research-article", "authors": [{"type": "person"}]}}
        self.assertRaises(ValueError, main.check_authors, snippet)

    def test_related_article_to_related_articles_whem_empty(self):
        # For increased test coverage, test and empty list
        related_article_list = [{'junk': 'not related'}]
        expected = []
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

    def test_base_url(self):
        given = 1234
        expected = 'https://cdn.elifesciences.org/articles/01234/'
        self.assertEqual(expected, main.base_url(given))

    def test_pdf_uri(self):
        given = (['research-article'], 1234, 1)
        expected = 'https://cdn.elifesciences.org/articles/01234/elife-01234-v1.pdf'
        self.assertEqual(expected, main.pdf_uri(given))

    def test_pdf_uri_correction(self):
        given = (['Correction'], 1234, 1)
        expected = main.EXCLUDE_ME
        self.assertEqual(expected, main.pdf_uri(given))

    def test_pdf_uri_bad(self):
        cases = [
            ("asdf", "asdf", "asdf"),
        ]
        for given in cases:
            self.assertRaises(ValueError, main.pdf_uri, given)

    def test_fix_filenames(self):
        given = [
            {"type": "image", "image": {"uri": "foo"}},
            {"type": "image", "image": {"uri": "foo.bar"}}
        ]
        expected = [
            {"type": "image", "image": {"uri": "foo.tif"}},
            {"type": "image", "image": {"uri": "foo.bar"}}, # no clobbering
        ]
        self.assertEqual(main.fix_extensions(given), expected)

    def test_expand_uris(self):
        msid = 1234
        given = [
            {"uri": "foo.bar"},
            {"type": "image", "uri": "foo.bar"},
            {"uri": "www.foo.bar"},
            {"uri": "doi:10.7554/eLife.09560"},
            {"uri": "http://foo.bar/baz.bup"},
            {"uri": "https://foo.bar/baz.bup"},
            {"uri": "ftp://user:pass@foo.bar/baz.bup"},
            {"uri": "ftps://user:pass@foo.bar/baz.bup"},
        ]
        expected = [
            # filename => https://cdn.tld/path/filename
            {"uri": main.cdnlink(msid, "foo.bar")},
            {"type": "image", "uri": main.cdnlink(msid, "foo.bar")},
            # www => http://www.
            {"uri": "http://www.foo.bar"},
            # doi:... => https://doi.org/...
            {"uri": "https://doi.org/10.7554/eLife.09560"},
            # already-expanded uris are preserved
            {"uri": "http://foo.bar/baz.bup"},
            {"uri": "https://foo.bar/baz.bup"},
            {"uri": "ftp://user:pass@foo.bar/baz.bup"},
            {"uri": "ftps://user:pass@foo.bar/baz.bup"},
        ]
        self.assertEqual(main.expand_uris(msid, given), expected)

    def test_expand_image(self):
        msid = 1234
        given = [
            {"type": "video", "image": "https://foo.bar/baz.bup"},
            {"type": "image", "image": {"uri": "https://foo.bar/baz.bup"}},
        ]
        expected = [
            {"type": "video", "image": utils.pad_filename(msid, main.cdnlink(msid, "baz.bup"))},
            main.expand_iiif_uri(msid, {"type": "image", "image": {"uri": "https://foo.bar/baz.bup"}}, "image"),
        ]
        self.assertEqual(main.expand_image(msid, given), expected)

    def test_expand_placeholder(self):
        msid = 1234
        given = [
            {"type": "video", "placeholder": {"uri": "https://foo.bar/baz.bup"}},
        ]
        expected = [
            main.expand_iiif_uri(msid, {"type": "video", "placeholder": {"uri": "https://foo.bar/baz.bup"}}, "placeholder"),
        ]
        self.assertEqual(main.expand_placeholder(msid, given), expected)

    def test_isbn(self):
        cases = [
            # 10 digits => formatted 13 digits
            ("0198526636", "978-0-19-852663-6"),
            ("0-19-852663-6", "978-0-19-852663-6"),

            # 13 digits => formatted 13 digits
            ("9789241565059", "978-92-4-156505-9"),
            ("978 92 4 156505 9", "978-92-4-156505-9"),

            # arbitrary formatting => formatted 13 digits
            ("9-7-8-9-2-4-1-5-6-5-0-5-9", "978-92-4-156505-9"),
            ("9 7 8 9 2 4 1 5 6 5 0 5 9", "978-92-4-156505-9"),
            ("9--7:8.9|2-4|1|565|0--59", "978-92-4-156505-9"),
            ("ISBN: 9789241565059", "978-92-4-156505-9"),
            ("ISBN:9789241565059", "978-92-4-156505-9"),

            # handles the 'X' check digit
            ("184146208X", "978-1-84146-208-0"),
        ]
        for given, expected in cases:
            self.assertEqual(main.handle_isbn(given), expected)

    def test_mixed_citation(self):
        given = [{'article': {'authorLine': 'R Straussman et al', 'authors': [{'given': u'R', 'surname': u'Straussman'}, {'given': u'T', 'surname': u'Morikawa'}, {'given': u'K', 'surname': u'Shee'}, {'given': u'M', 'surname': u'Barzily-Rokni'}, {'given': u'ZR', 'surname': u'Qian'}, {'given': u'J', 'surname': u'Du'}, {'given': u'A', 'surname': u'Davis'}, {'given': u'MM', 'surname': u'Mongare'}, {'given': u'J', 'surname': u'Gould'}, {'given': u'DT', 'surname': u'Frederick'}, {'given': u'ZA', 'surname': u'Cooper'}, {'given': u'PB', 'surname': u'Chapman'}, {'given': u'DB', 'surname': u'Solit'}, {'given': u'A', 'surname': u'Ribas'}, {'given': u'RS', 'surname': u'Lo'}, {'given': u'KT', 'surname': u'Flaherty'}, {'given': u'S', 'surname': u'Ogino'}, {'given': u'JA', 'surname': u'Wargo'}, {'given': u'TR', 'surname': u'Golub'}], 'doi': u'10.1038/nature11183', 'pub-date': [2014, 2, 28], 'title': u'Tumour micro-environment elicits innate resistance to RAF inhibitors through HGF secretion'}, 'journal': {'volume': u'487', 'lpage': u'504', 'name': u'Nature', 'fpage': u'500'}}]

        expected = [{
            'type': 'external-article',
            'articleTitle': u'Tumour micro-environment elicits innate resistance to RAF inhibitors through HGF secretion',
            'journal': 'Nature',
            'authorLine': 'R Straussman et al',
            'uri': 'https://doi.org/10.1038/nature11183',
        }]
        self.assertEqual(expected, main.mixed_citation_to_related_articles(given))

    def test_serialize_bad_args(self):
        expected = dict([
            ('', 1),
            (('', ''), 2),
            (None, 3),
            ('|', 4),
        ])
        for bad_key, val in expected.items():
            self.assertRaises(AssertionError, main.serialize_overrides, {bad_key: val})

class KitchenSink(base.BaseCase):
    def setUp(self):
        self.doc = join(self.fixtures_dir, 'elife-00666-v1.xml')
        self.soup = main.to_soup(self.doc)

    def test_figure_and_video(self):
        result = main.render_single(self.doc, version=1)
        figure = result['article']['body'][1]['content'][4]['content'][2]
        media = result['article']['body'][1]['content'][5]['content'][1]

        def tod(d):
            return json.loads(json.dumps(d))

        expected_figure = {
            'type': 'figure',
            'assets': [{
                'attribution': ['For the purpose having a example of how to tag a separate license for an item, we have indicated in the XML and display this is a\n                                        copyrighted figure; however it is not.'],
                'doi': '10.7554/eLife.00666.007',
                'id': 'fig1',
                'image': {
                    'alt': '',
                    'size': {
                        'height': None,
                        'width': None,
                    },
                    'source': {
                        'filename': 'elife-00666-fig1.jpg',
                        'mediaType': 'image/jpeg',
                        'uri': 'https://prod--cdn-iiif.elifesciences.org/lax:00666/elife-00666-fig1.tif/full/full/0/default.jpg'
                    },
                    'uri': 'https://prod--cdn-iiif.elifesciences.org/lax:00666/elife-00666-fig1.tif'},
                'label': 'Figure 1',
                'title': 'Single figure: The header of an eLife article example on the HTML page. In the PDf this is represented as a single column.',
                'type': 'image',
            }]
        }

        self.assertEqual(tod(expected_figure), tod(figure))

        expected_media = {
            'type': 'figure',
            'assets': [{
                "type": "video",
                "doi": "10.7554/eLife.00666.016",
                "id": "video1",
                "label": "Video 1",
                "title": "\n                                A description of the eLife editorial process.\n                            ",
                "placeholder": {
                    "alt": "",
                    "size": {
                        "height": None,
                        "width": None,
                    },
                    "source": {
                        "filename": "elife-00666-video1.jpg",
                        "mediaType": "image/jpeg",
                        "uri": "https://prod--cdn-iiif.elifesciences.org/lax:00666/elife-00666-video1.jpg/full/full/0/default.jpg"
                    },
                    "uri": "https://prod--cdn-iiif.elifesciences.org/lax:00666/elife-00666-video1.jpg"
                },
                "sourceData": [{
                    "doi": "10.7554/eLife.00666.037",
                    "id": "video1sdata1",
                    "label": u"Video 1\u2014Source data 1",
                    "title": "Title of the source code.",
                    "mediaType": "application/xlsx",
                    "caption": [
                        {
                            "type": "paragraph",
                            "text": "Legend of the source code.",
                        },
                    ],
                    "uri": main.cdnlink("00666", "elife-00666-video1-data1.xlsx"),
                    "filename": "elife-00666-video1-data1.xlsx"
                }],
                "image": main.cdnlink("00666", "elife-00666-video1.jpg"),
                "height": 720,
                "width": 1280,
                'sources': [{'mediaType': 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"',
                             'uri': 'https://static-movie-usa.glencoesoftware.com/mp4/10.7554/657/f42a609b0e61fc41798dcba3cc0c87598bd2cf9f/elife-00666-video1.mp4'},
                            {'mediaType': 'video/ogg; codecs="theora, vorbis"',
                             'uri': 'https://static-movie-usa.glencoesoftware.com/ogv/10.7554/657/f42a609b0e61fc41798dcba3cc0c87598bd2cf9f/elife-00666-video1.ogv'},
                            {'mediaType': 'video/webm; codecs="vp8.0, vorbis"',
                             'uri': 'https://static-movie-usa.glencoesoftware.com/webm/10.7554/657/f42a609b0e61fc41798dcba3cc0c87598bd2cf9f/elife-00666-video1.webm'}]
            }]
        }
        self.assertEqual(tod(expected_media), tod(media))

    def test_patched_data_present(self):
        """an indication article-json contains patched values is present.
        rendered article-json contains patched values to allow it to validate
        prior to lax filling in the blanks."""
        result = main.render_single(self.doc, version=1)
        self.assertTrue('patched' in result['article']['-meta'])
