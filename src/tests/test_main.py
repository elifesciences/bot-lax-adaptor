from unittest import mock
import pytest
import et3.render
from elifetools import parseJATS
from collections import OrderedDict
import time
import os
import json
from os.path import join
from tests import base
from src import main, utils, conf

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

def test_missing_var():
    with pytest.raises(KeyError):
        main.getvar('foo')({}, None)

def test_to_volume():
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
        actual = main.to_volume(year_volume_pair)
        assert expected == actual, "given %r, I expected %r but got %r" % (year_volume_pair, expected, actual)

def test_main_bootstrap_failure():
    "ensure a great big exception occurs when given invalid input"
    # TODO: lets make this behaviour a bit nicer
    with pytest.raises(Exception):
        main.main("not-a-file-like-object")

class ArticleScrape(base.BaseCase):
    def setUp(self):
        self.small_doc = join(self.fixtures_dir, 'elife-16695-v1.xml')

    def test_render_single(self):
        "ensure the scrape scrapes and has something resembling the correct structure"
        results = main.render_single(self.small_doc, version=1)
        self.assertTrue('article' in results)
        self.assertTrue('journal' in results)
        # NOTE! leave article validation to json schema

    def test_main_bootstrap(self):
        "json is written to stdout"
        results = main.main(self.small_doc) # writes article json to stdout
        results = json.loads(results)
        self.assertTrue('article' in results)
        self.assertTrue('journal' in results)

    def test_main_published_dummied_if_v2(self):
        # when version == 1, we just use the pubdate in the xml
        results = main.render_single(self.small_doc, version=1)
        self.assertEqual(results['article']['versionDate'], '2016-08-16T00:00:00Z')
        # when version > 1, we rely on lax to fill in the actual value,
        # passing an obviously false placeholder to avoid validation failure
        results = main.render_single(self.small_doc, version=2)
        self.assertEqual(results['article']['versionDate'], main.DUMMY_DATE)

def test_category_codes():
    cat_list = ['Immunology', 'Microbiology and Infectious Disease']
    expected = [{"id": "immunology", "name": "Immunology"},
                {"id": "microbiology-infectious-disease",
                 "name": "Microbiology and Infectious Disease"}]
    assert expected == main.category_codes(cat_list)

def test_related_article_to_related_articles():
    cases = [
        ([{'junk': 'not related'}], []),
        ([{'xlink_href': '10.7554/eLife.09561', 'related_article_type': 'article-reference', 'ext_link_type': 'doi'}], ['09561']),
        ([{'xlink_href': '10.7554/eLife.09560', 'related_article_type': 'article-reference', 'ext_link_type': 'doi'},
          {'xlink_href': '10.7554/eLife.09561', 'related_article_type': 'article-reference', 'ext_link_type': 'doi'}], ['09560', '09561']),
        ([{'xlink_href': 'foo', 'related_article_type': 'article-reference', 'ext_link_type': 'doi'}], [])
    ]
    for given, expected in cases:
        assert expected == main.related_article_to_related_articles(given)

def test_display_channel_to_article_type_fails():
    display_channel = ['']
    expected = None
    assert expected == main.display_channel_to_article_type(display_channel)

def test_discard_if_none_or_empty():
    cases = [
        (None, main.EXCLUDE_ME),
        ('not none', 'not none'),
        ([], main.EXCLUDE_ME),
        ({}, main.EXCLUDE_ME)
    ]
    for given, expected in cases:
        actual = main.discard_if_none_or_empty(given)
        assert expected == actual, "given %r I expected %r but got %r" % (given, expected, actual)

def test_licence_holder():
    cases = [
        ((None, 'CC-BY-4'), main.EXCLUDE_ME),
        (('John', 'CC-BY-4'), 'John'),
        (('John', 'CC0-1.0'), main.EXCLUDE_ME),
        (('Jane', 'cC0-2.foo'), main.EXCLUDE_ME)
    ]
    for given, expected in cases:
        actual = main.discard_if_none_or_cc0(given)
        assert expected == actual, "given %r I expected %r but got %r" % (given, expected, actual)

def test_base_url():
    given = 1234
    expected = 'https://cdn.elifesciences.org/articles/01234/'
    actual = main.base_url(given)
    assert expected == actual

def test_pdf_uri():
    given = (['research-article'], 1234, 1)
    expected = 'https://cdn.elifesciences.org/articles/01234/elife-01234-v1.pdf'
    actual = main.pdf_uri(given)
    assert expected == actual

def test_xml_uri():
    given = (1234, 1)
    expected = 'https://cdn.elifesciences.org/articles/01234/elife-01234-v1.xml'
    actual = main.xml_uri(given)
    assert expected == actual

def test_pdf_uri_correction():
    given = (['Correction'], 1234, 1)
    expected = main.EXCLUDE_ME
    actual = main.pdf_uri(given)
    assert expected == actual

def test_pdf_uri_retraction():
    given = (['Retraction'], 1234, 1)
    expected = main.EXCLUDE_ME
    actual = main.pdf_uri(given)
    assert expected == actual

def test_pdf_uri_bad():
    cases = [
        ("asdf", "asdf", "asdf"),
    ]
    for given in cases:
        with pytest.raises(ValueError):
            main.pdf_uri(given)

def test_fix_filenames():
    given = [
        {"type": "image", "image": {"uri": "foo"}},
        {"type": "image", "image": {"uri": "foo.bar"}}
    ]
    expected = [
        {"type": "image", "image": {"uri": "foo.tif"}},
        {"type": "image", "image": {"uri": "foo.bar"}}, # no clobbering
    ]
    actual = main.fix_extensions(given)
    assert expected == actual

def test_expand_uris():
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
    actual = main.expand_uris(msid, given)
    assert expected == actual

def test_expand_image():
    msid = 1234
    given = [
        {"type": "video", "image": "https://foo.bar/baz.bup"},
        {"type": "image", "image": {"uri": "https://foo.bar/baz.bup"}},
    ]
    expected = [
        {"type": "video", "image": utils.pad_filename(msid, main.cdnlink(msid, "baz.bup"))},
        main.expand_iiif_uri(msid, {"type": "image", "image": {"uri": "https://foo.bar/baz.bup"}}, "image"),
    ]
    actual = main.expand_image(msid, given)
    assert expected == actual

def test_expand_placeholder():
    msid = 1234
    given = [
        {"type": "video", "placeholder": {"uri": "https://foo.bar/baz.bup"}},
    ]
    expected = [
        main.expand_iiif_uri(msid, {"type": "video", "placeholder": {"uri": "https://foo.bar/baz.bup"}}, "placeholder"),
    ]
    actual = main.expand_placeholder(msid, given)
    assert expected == actual

def test_isbn():
    cases = [
        (None, None),

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
        actual = main.handle_isbn(given)
        assert expected == actual

def test_mixed_citation():
    given = [{'article': {'authorLine': 'R Straussman et al', 'authors': [{'given': 'R', 'surname': 'Straussman'}, {'given': 'T', 'surname': 'Morikawa'}, {'given': 'K', 'surname': 'Shee'}, {'given': 'M', 'surname': 'Barzily-Rokni'}, {'given': 'ZR', 'surname': 'Qian'}, {'given': 'J', 'surname': 'Du'}, {'given': 'A', 'surname': 'Davis'}, {'given': 'MM', 'surname': 'Mongare'}, {'given': 'J', 'surname': 'Gould'}, {'given': 'DT', 'surname': 'Frederick'}, {'given': 'ZA', 'surname': 'Cooper'}, {'given': 'PB', 'surname': 'Chapman'}, {'given': 'DB', 'surname': 'Solit'}, {'given': 'A', 'surname': 'Ribas'}, {'given': 'RS', 'surname': 'Lo'}, {'given': 'KT', 'surname': 'Flaherty'}, {'given': 'S', 'surname': 'Ogino'}, {'given': 'JA', 'surname': 'Wargo'}, {'given': 'TR', 'surname': 'Golub'}], 'doi': '10.1038/nature11183', 'pub-date': [2014, 2, 28], 'title': 'Tumour micro-environment elicits innate resistance to RAF inhibitors through HGF secretion'}, 'journal': {'volume': '487', 'lpage': '504', 'name': 'Nature', 'fpage': '500'}}]

    expected = [{
        'type': 'external-article',
        'articleTitle': 'Tumour micro-environment elicits innate resistance to RAF inhibitors through HGF secretion',
        'journal': 'Nature',
        'authorLine': 'R Straussman et al',
        'uri': 'https://doi.org/10.1038/nature11183',
    }]
    actual = main.mixed_citation_to_related_articles(given)
    assert expected == actual

def test_serialize_bad_args():
    expected = dict([
        ('', 1),
        (('', ''), 2),
        (None, 3),
        ('|', 4),
    ])
    for bad_key, val in expected.items():
        with pytest.raises(AssertionError):
            main.serialize_overrides({bad_key: val})

def test_expand_location__absolute_uris():
    "an absolute URI that doesn't need expanding won't be expanded"
    uri = expected = 'https://s3-external-1.amazonaws.com/elife-publishing-expanded/25605.3/b8bd7e0b-a259-4d60-9ab2-c8ea9ecc31dc/elife-25605-v3.xml'
    actual = main.expand_location(uri)
    assert actual == expected

def test_preprint_events__empty_cases():
    "`preprint_events` filters bad values and returns `None` if final result is empty"
    cases = [
        (None, None),
        ({}, None),
        ([], None),
        ("", None),
        ([{}], None),
        ([{'event_type': 'foo'}], None)
    ]
    for given, expected in cases:
        assert expected == main.preprint_events(given)

def test_preprint_events():
    "`preprint_events` returns a list of preprints filtered from the `pub_history` results"
    timeobj = time.gmtime()
    cases = [
        # only type=preprint are returned
        ([{"event_type": "preprint"}, {}], [{"event_type": "preprint"}]),

        # expected structs are passed through as-is
        ([{"event_type": "preprint",
           "uri": "http://foo.bar",
           "date": timeobj}],
         [{"event_type": "preprint",
           "uri": "http://foo.bar",
           "date": timeobj}])
    ]
    for given, expected in cases:
        assert expected == main.preprint_events(given)

def test_to_preprint__empty_cases():
    "`to_preprint` returns `None` for bad/empty cases"
    cases = [
        (None, None),
        ([], None),
        ({}, None),
        ("", None)
    ]
    for given, expected in cases:
        assert expected == main.to_preprint(given)

def test_to_preprint():
    "`to_preprint` takes the raw data from `pub_history` and converts it to a API RAML valid format"
    given = OrderedDict([
        ("event_type", "preprint"),
        ("event_desc", "This manuscript was published as a preprint at bioRxiv."),
        ("event_desc_html", "This manuscript was published as a preprint at bioRxiv."),
        ("uri", "https://www.biorxiv.org/content/10.1101/2019.08.22.6666666v1"),
        ("day", "15"),
        ("month", "02"),
        ("year", "2019"),
        ("date", time.struct_time((2019, 2, 15, 0, 0, 0, 4, 46, 0))),
        ("iso-8601-date", "2019-02-15"),
    ])

    expected = {
        "status": "preprint",
        "description": "This manuscript was published as a preprint at bioRxiv.",
        "uri": "https://www.biorxiv.org/content/10.1101/2019.08.22.6666666v1",
        "date": '2019-02-15T00:00:00Z'}
    assert expected == main.to_preprint(given)

def test_reviewed_preprint_events():
    cases = [
        (None, []),
        ({}, []),
        ([], []),
        ('', []),
        ([None], []),
        ([{}], []),
        ([{'foo': 'bar'}], []),

        ([OrderedDict([
            ("event_type", "reviewed-preprint"),
            ("event_desc", "This manuscript was published as a reviewed preprint."),
            ("event_desc_html", "This manuscript was published as a reviewed preprint."),
            ("uri", "https://doi.org/10.7554/eLife.1234567890.1"),
            ("day", "15"),
            ("month", "04"),
            ("year", "2023"),
            ("date", time.struct_time((2023, 4, 15, 0, 0, 0, 4, 46, 0))),
            ("iso-8601-date", "2023-04-15")])],
         [{'status': 'reviewed-preprint',
           'description': "This manuscript was published as a reviewed preprint.",
           'uri': "https://doi.org/10.7554/eLife.1234567890.1",
           'date': '2023-04-15T00:00:00Z'}]),
    ]
    for given, expected in cases:
        assert expected == main.reviewed_preprint_events(given)

def test_sent_for_peer_review():
    desc = {'sent-for-peer-review': main.SNIPPET['-history']['sent-for-peer-review']}
    desc['sent-for-peer-review'][0] = lambda v: v # patch the call to `main.jats`
    cases = [
        # empty values are elided
        (None, [{}]),
        ("", [{}]),

        # time structs are handled
        (time.struct_time((2023, 12, 31, 1, 2, 3, 4, 56, 7)),
         [{'sent-for-peer-review': '2023-12-31T01:02:03Z'}])
    ]
    for given, expected in cases:
        assert expected == list(et3.render.render(desc, [given]))

def test_elife_assessment():
    expected = [
        {'elifeAssessment':
         {'content': [
             {'text': 'This is an eLife assessment, which is a summary of the peer reviews provided by the BRE. It will only contain one or more paragraphs, no figures, tables or videos. It might say something like, "with respect to blah blah, this study is <b>noteworthy</b> backed up by data that is <b>compelling</b>, however the model design for blah is <b>flawed</b> and the evidence <b>incomplete</b>.', 'type': 'paragraph'}],
          'doi': '10.7554/eLife.1234567890.4.sa0',
          'id': 'sa0',
          'significance': ['noteworthy', 'flawed'],
          'strength': ['compelling', 'incomplete'],
          'title': 'eLife assessment'}}]
    soup = parseJATS.parse_xml(base.read_fixture("xml-snippets/elife-1234567890-v2.elife-assessment.xml"))
    description = {'elifeAssessment': main.VOR['elifeAssessment']}
    actual = list(main.render(description, [soup]))
    assert expected == actual

def test_recommendations_for_authors():
    expected = [
        {'recommendationsForAuthors':
         {'content': [{'text': 'Recommendations for edits to the initial preprint, based on the reviewers\' comments.',
                       'type': 'paragraph'}],
          'doi': '10.7554/eLife.1234567890.4.sa4',
          'id': 'sa4',
          'title': 'Recommendations for authors'}}]
    soup = parseJATS.parse_xml(base.read_fixture("xml-snippets/elife-1234567890-v2.recommendations-for-authors.xml"))
    description = {'recommendationsForAuthors': main.VOR['recommendationsForAuthors']}
    actual = list(main.render(description, [soup]))
    assert expected == actual

def test_public_reviews():
    expected = json.loads(base.read_fixture("xml-snippets/elife-1234567890-v2.public-reviews.json"))
    soup = parseJATS.parse_xml(base.read_fixture("xml-snippets/elife-1234567890-v2.public-reviews.xml"))
    description = {'publicReviews': main.VOR['publicReviews']}
    actual = list(main.render(description, [soup]))
    assert expected == actual

def test_doi_version():
    "the doi 'version' field is extracted from XML as expected"
    xml = """<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD with MathML3 v1.2 20190208//EN
" "JATS-archivearticle1-mathml3.dtd">
<article article-type="research-article" dtd-version="1.2" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:ali
="http://www.niso.org/schemas/ali/1.0/">
    <front>
        <article-meta>
            <article-id pub-id-type="doi" specific-use="version">10.7554/eLife.1234567890.4</article-id>
        </article-meta>
    </front>
</article>"""
    soup = main.to_soup(xml)
    expected = {'doiVersion': '10.7554/eLife.1234567890.4'}
    description = utils.subdict(main.SNIPPET, ['doiVersion'])
    actual = next(main.render(description, [soup]))
    assert expected == actual

def test_doi_version__missing():
    "missing values are not rendered"
    soup = main.to_soup("")
    description = utils.subdict(main.SNIPPET, ['doiVersion'])
    expected = {}
    actual = next(main.render(description, [soup]))
    assert expected == actual

def test_related_article_to_reviewed_preprint():
    expected = [
        OrderedDict([('authorLine', 'Zhipeng Wang, Cheng Jin ... Wei Song'),
                     ('doi', '10.1101/2022.12.20.521179'),
                     ('id', '85380'),
                     ('pdf',
                      'https://github.com/elifesciences/enhanced-preprints-data/raw/master/data/85380/v2/85380-v2.pdf'),
                     ('published', '2023-03-24T03:00:00Z'),
                     ('reviewedDate', '2023-03-24T03:00:00Z'),
                     ('stage', 'published'),
                     ('status', 'reviewed'),
                     ('statusDate', '2023-06-28T03:00:00Z'),
                     ('subjects',
                      [OrderedDict([('id', 'developmental-biology'),
                                    ('name', 'Developmental Biology')])]),
                     ('title',
                      'Identification of quiescent FOXC2<sup>+</sup> spermatogonial '
                      'stem cells in adult mammals'),
                     ('versionDate', '2023-06-28T03:00:00Z'),
                     ('type', 'reviewed-preprint')])]

    rpp_snippet = {
        "id": "85380",
        "doi": "10.1101/2022.12.20.521179",
        "pdf": "https://github.com/elifesciences/enhanced-preprints-data/raw/master/data/85380/v2/85380-v2.pdf",
        "status": "reviewed",
        "authorLine": "Zhipeng Wang, Cheng Jin ... Wei Song",
        "title": "Identification of quiescent FOXC2<sup>+</sup> spermatogonial stem cells in adult mammals",
        "published": "2023-03-24T03:00:00Z",
        "reviewedDate": "2023-03-24T03:00:00Z",
        "versionDate": "2023-06-28T03:00:00Z",
        "statusDate": "2023-06-28T03:00:00Z",
        "stage": "published",
        "subjects": [
            {
                "id": "developmental-biology",
                "name": "Developmental Biology"
            }
        ],
        "indexContent": "foo"
    }

    with open(base.fixture_path("article-with-reviewed-preprint-relations.xml")) as fixture:
        soup = parseJATS.parse_xml(fixture.read())

    mock_response = mock.Mock
    mock_response.status_code = 200
    mock_response.json = lambda: rpp_snippet
    with mock.patch('utils.requests_get', return_value=mock_response):
        actual = main.related_article_to_reviewed_preprint(soup)
    assert actual == expected
