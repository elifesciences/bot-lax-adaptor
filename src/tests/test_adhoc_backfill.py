from datetime import datetime
from os.path import join

from unittest import mock

from src import conf, utils, adhoc_backfill as bfup
from .base import BaseCase
from src.utils import partial_match

class One(BaseCase):
    def setUp(self):
        self.big_doc = join(conf.XML_DIR, "elife-09560-v1.xml")
        self.small_doc = join(self.fixtures_dir, 'elife-16695-v1.xml')

    def tearDown(self):
        pass

    def test_request_valid_path(self):
        "sends article to lax given a path to an xml file"
        paths = [self.small_doc]

        expected_lax_response = {
            # "id": '09560',
            "id": "16695",
            "requested-action": 'ingest',
            "token": 'pants-party', # set by fs-adaptor
            "status": conf.INGESTED,
            "message": '...?',
            "datetime": utils.ymdhms(datetime.now())
        }
        expected = {'valid': [expected_lax_response], 'errors': [], 'invalid': []}

        with mock.patch('adaptor.call_lax', autospec=True, specset=True, return_value=expected_lax_response):
            actual = bfup.do_paths(paths)
            self.assertTrue(partial_match(expected, actual))

    def test_request_multiple_valid_paths(self):
        "sends multiple articles to lax given paths to xml files"
        paths = [self.small_doc] * 3 # send the same article three times

        expected_lax_response = {
            # "id": '09560',
            "id": "16695",
            "requested-action": 'ingest',
            "token": 'pants-party', # set by fs-adaptor
            "status": conf.INGESTED,
            "message": '...?',
            "datetime": utils.ymdhms(datetime.now())
        }
        expected = {'valid': [expected_lax_response] * 3, 'errors': [], 'invalid': []}

        with mock.patch('adaptor.call_lax', autospec=True, specset=True, return_value=expected_lax_response):
            actual = bfup.do_paths(paths)
            self.assertTrue(partial_match(expected, actual))

    def test_request_bad_paths(self):
        "obviously bad values are discarded immediately"
        paths = ['a', 'b', 'c', [], None, BaseCase]
        # invalids (above) never make it pass path extraction
        expected = {'valid': [], 'errors': [], 'invalid': []}
        actual = bfup.do_paths(paths)
        self.assertEqual(actual, expected)

    def test_request_bad_paths2(self):
        "unhandled path types are discarded, even if they call `mkreq` directly"
        class Bah(object):
            pass
        expected = None
        self.assertEqual(bfup.mkreq(Bah()), expected)

    def test_request_invalid_path(self):
        "something invalid that initially looks valid fails when we try to use it"
        paths = ['elife-09561-v1.xml'] # msid and version can be extracted, but it's not a path
        expected = {'valid': [], 'errors': [{'status': 'error', 'requested-action': 'ingest'}], 'invalid': []}
        actual = bfup.do_paths(paths)
        self.assertTrue(partial_match(expected, actual))

    def test_request_lax_style(self):
        "dictionaries of article information can be fed in"
        paths = [{
            'msid': 16695,
            'version': 1,
            'location': 'https://s3-external-1.amazonaws.com/elife-publishing-expanded/16695.1/9c2cabd8-a25a-4d76-9f30-1c729755480b/elife-16695-v1.xml',
        }]
        expected_lax_response = {
            "id": "16695",
            "requested-action": 'ingest',
            "token": 'pants-party',
            "status": conf.INGESTED,
            "message": '...?',
            "datetime": utils.ymdhms(datetime.now())
        }
        expected = {'valid': [expected_lax_response], 'errors': [], 'invalid': []}
        with mock.patch('adaptor.call_lax', autospec=True, specset=True, return_value=expected_lax_response):
            with mock.patch('adaptor.http_download', autospec=True, return_value=open(self.small_doc, 'r')):
                actual = bfup.do_paths(paths)
                self.assertTrue(partial_match(expected, actual))

    def test_request_lax_style_missing_location(self):
        paths = [{
            'msid': 16695,
            'version': 1,
            'location': 'no-location-stored' # could be anything really
        }]
        expected = {'valid': [], 'errors': [], 'invalid': []}
        actual = bfup.do_paths(paths)
        self.assertEqual(actual, expected)

class Two(BaseCase):
    def setUp(self):
        self.path = 'article-xml/articles/elife-09560-v1.xml'
        self.expected = [
            {
                "validate-only": False,
                "force": True,
                "token": "pants-party",
                "version": 1,
                "location": "file://" + join(conf.PROJECT_DIR, self.path),
                "action": "ingest",
                "id": "09560"
            }
        ]

    def tearDown(self):
        pass

    def test_bootstrap_read_paths(self):
        "a path can be read from stdin"
        given = [self.path, '--dry-run'] # order is important, dry-run comes last (like kwargs)
        self.assertEqual(bfup.main(given), self.expected)

    def test_bootstrap_read_multiple_paths(self):
        "many paths can be read from stdin, single line"
        given = [self.path, self.path, '--dry-run'] # order is important, dry-run comes last (like kwargs)
        self.assertEqual(bfup.main(given), self.expected * 2)

    def test_bootstrap_read_paths_from_stdin(self):
        "paths can be read from stdin, one per line"
        with mock.patch('src.adhoc_backfill.read_from_stdin', return_value=[self.path]):
            actual = bfup.main(['--dry-run'])
            self.assertEqual(actual, self.expected)

    def test_bootstrap_read_multiple_paths_from_stdin(self):
        "paths can be read from stdin, one per line"
        paths = "\n".join([self.path] * 3)
        expected = self.expected * 3
        with mock.patch('src.adhoc_backfill.read_from_stdin', return_value=paths.splitlines()):
            actual = bfup.main(['--dry-run'])
            self.assertEqual(actual, expected)

    def test_bootstrap_read_json_object_from_stdin(self):
        "json objects can be read from stdin as well, they must be line-delimited though"
        jsonobj = '''{"msid":16695,"version":1,"location":"https://s3-external-1.amazonaws.com/elife-publishing-expanded/16695.1/9c2cabd8-a25a-4d76-9f30-1c729755480b/elife-16695-v1.xml"}'''
        self.expected[0].update({
            'id': '16695',
            'location': 'https://s3-external-1.amazonaws.com/elife-publishing-expanded/16695.1/9c2cabd8-a25a-4d76-9f30-1c729755480b/elife-16695-v1.xml',
        })
        with mock.patch('src.adhoc_backfill.read_from_stdin', return_value=[jsonobj]):
            actual = bfup.main(['--dry-run'])
            self.assertEqual(actual, self.expected)

    def test_bootstrap_read_multiple_json_objects_from_stdin(self):
        "json objects can be read from stdin as well, they must be line-delimited though"
        jsonobj = '''{"msid":16695,"version":1,"location":"https://s3-external-1.amazonaws.com/elife-publishing-expanded/16695.1/9c2cabd8-a25a-4d76-9f30-1c729755480b/elife-16695-v1.xml"}
{"msid":1968,"version":1,"location":"no-location-stored"}'''
        self.expected[0].update({
            'location': u'https://s3-external-1.amazonaws.com/elife-publishing-expanded/16695.1/9c2cabd8-a25a-4d76-9f30-1c729755480b/elife-16695-v1.xml',
            'id': u'16695'
        })
        with mock.patch('src.adhoc_backfill.read_from_stdin', return_value=jsonobj.splitlines()):
            actual = bfup.main(['--dry-run'])
            self.assertEqual(actual, self.expected)
