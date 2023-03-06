import json
import os
from os.path import join
import shutil
import tempfile
from flask_testing import TestCase
from unittest.mock import patch
from . import base
from src import api, validate, utils, main as scraper, conf

class FlaskTestCase(TestCase):
    maxDiff = None
    this_dir = os.path.realpath(os.path.dirname(__file__))
    fixtures_dir = join(this_dir, 'fixtures')
    render_templates = False

    def create_app(self):
        self.temp_dir = tempfile.mkdtemp(suffix='-bot-lax-api-test')
        return api.create_app({
            'DEBUG': True,
            'UPLOAD_FOLDER': self.temp_dir
        })

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

class Http(FlaskTestCase):

    def test_bad_request_missing_msid_version(self):
        "both msid and version are required parameters"
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)
        with patch('adaptor.call_lax'):
            resp = self.client.post('/xml', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': {
                    'xml': (open(xml_fixture, 'rb'), xml_fname),
                }
            })
        self.assertEqual(resp.status_code, 400)

    def test_bad_request_missing_msid(self):
        "both msid and version are required parameters"
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)
        with patch('adaptor.call_lax'):
            resp = self.client.post('/xml?version=1', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': {
                    'xml': (open(xml_fixture, 'rb'), xml_fname),
                }
            })
        self.assertEqual(resp.status_code, 400)

    def test_bad_request_missing_version(self):
        "both msid and version are required parameters"
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)
        with patch('adaptor.call_lax'):
            resp = self.client.post('/xml?id=16695', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': {
                    'xml': (open(xml_fixture, 'rb'), xml_fname),
                }
            })
        self.assertEqual(resp.status_code, 400)

    def test_bad_request_missing_body(self):
        "both msid and version are required parameters"
        with patch('adaptor.call_lax'):
            resp = self.client.post('/xml?id=16695&version=1')
        self.assertEqual(resp.status_code, 400)

class Two(FlaskTestCase):
    def test_upload_valid_xml(self):
        "the response we expect when everything happens perfectly"
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        expected_lax_resp = {
            'status': conf.VALIDATED,
            'override': {},
            'ajson': base.load_ajson(xml_fixture + '.json')['article'],
            'message': None # this should trigger an error when logged naively by api.py but doesn't...
        }

        with patch('adaptor.call_lax', return_value=expected_lax_resp):
            resp = self.client.post('/xml?id=16695&version=1', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': {
                    'xml': (open(xml_fixture, 'rb'), xml_fname),
                }
            })

        # ensure xml uploaded
        expected_xml_path = join(self.temp_dir, xml_fname)
        self.assertTrue(os.path.exists(expected_xml_path), "uploaded xml cannot be found")

        # ensure ajson scraped
        expected_ajson_path = join(self.temp_dir, xml_fname) + '.json'
        self.assertTrue(os.path.exists(expected_ajson_path), "scraped ajson not found")

        # ensure scraped ajson is identical to what we're expecting
        expected_ajson = base.load_ajson(join(self.fixtures_dir, 'elife-16695-v1.xml.json'))
        actual_ajson = base.load_ajson(expected_ajson_path)
        self.assertEqual(actual_ajson, expected_ajson)

        # ensure ajson validated
        success, _ = validate.main(open(expected_ajson_path, 'r', encoding='utf-8'))
        self.assertTrue(success)

        # ensure ajson is successfully sent to lax
        self.assertEqual(resp.status_code, 200)

        resp_json = resp.get_json()
        del resp_json['ajson']['-meta'] # remove the -meta key from the response.
        self.assertEqual(expected_lax_resp, resp_json)

    def test_upload_valid_xml_overrides(self):
        "the response we expect when everything happens perfectly with overrides"
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)
        xml_upload_fname = 'elife-16695-v1.xml'

        # make the request with some overrides
        override = {
            'title': 'foo',
            'statusDate': '2012-12-21T00:00:00Z'
        }
        payload = {
            'xml': (open(xml_fixture, 'rb'), xml_upload_fname),
            'override': scraper.serialize_overrides(override),
        }

        # this is the article-json we expect in the response including overridden values
        expected_ajson = base.load_ajson(xml_fixture + '.json')
        expected_ajson = scraper.manual_overrides({'override': override}, expected_ajson)
        expected_ajson = expected_ajson['article'] # user doesn't ever see journal or snippet structs

        mock_lax_resp = {
            'status': conf.VALIDATED,
            'override': override,
            'ajson': expected_ajson,
        }
        with patch('adaptor.call_lax', return_value=mock_lax_resp):
            resp = self.client.post('/xml?id=16695&version=1', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': payload,
            })

        # success
        self.assertEqual(resp.status_code, 200)

        # remove the meta because we can't compare it
        resp_json = resp.get_json()
        del resp_json['ajson']['-meta']

        # response is exactly as we anticipated
        self.assertEqual(mock_lax_resp, resp_json)

    def test_bad_upload_ext(self):
        "the response we expect when the xml fails to upload"
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        bad_ext = '.pants'
        resp = self.client.post('/xml?id=16695&version=1', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': {
                'xml': (open(xml_fixture, 'rb'), xml_fname + bad_ext),
            }
        })

        expected_lax_resp = {
            'status': conf.ERROR,
            'code': conf.BAD_UPLOAD,
            # 'message': '...', # we just care that a message exists
            # 'trace': '...', # same again, just that a trace exists
        }
        self.assertEqual(resp.status_code, 400)

        self.assertTrue(utils.partial_match(expected_lax_resp, resp.json))
        self.assertTrue(resp.json['trace'].startswith('Traceback (most recent call last):'))
        self.assertTrue(resp.json['message']) # one exists and isn't empty

    def test_bad_upload_filename(self):
        "the response we expect when the xml fails to upload"
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        # msid doesn't match
        # filename doesn't match pattern 'elife-msid-vN.xml'
        bad_path = '/var/www/html/_default/cms/cms-0.9.40-alpha/ecs_includes/packageCreator/19942-v1.xml'
        resp = self.client.post('/xml?id=16695&version=1', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': {
                'xml': (open(xml_fixture, 'rb'), bad_path),
            }
        })

        expected_lax_resp = {
            'status': conf.ERROR,
            'code': conf.BAD_SCRAPE,
            # 'message': '...', # we just care that a message exists
            # 'trace': '...', # same again, just that a trace exists
        }
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(utils.partial_match(expected_lax_resp, resp.json))
        self.assertTrue(resp.json['trace'].startswith('Traceback (most recent call last):'))
        # self.assertTrue(resp.json['message']) # one exists and isn't empty
        self.assertTrue(resp.json['message'].startswith('not enough values to unpack')) # todo: gotta fix this filename parsing

    def test_bad_scrape(self):
        "the response we expect the xml fails to scrape"
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        with patch('main.main', side_effect=AssertionError('meow')):
            resp = self.client.post('/xml?id=16695&version=1', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': {
                    'xml': open(xml_fixture, 'rb'),
                }
            })

        expected_lax_resp = {
            'status': conf.ERROR,
            'code': conf.BAD_SCRAPE,
            # 'message': '...', # we just care that a message exists
            # 'trace': '...', # same again, just that a trace exists
        }
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(utils.partial_match(expected_lax_resp, resp.json))
        self.assertTrue(resp.json['trace'].startswith('Traceback (most recent call last):'))
        self.assertTrue(resp.json['message']) # one exists and isn't empty

    def test_bad_overrides(self):
        "ensure a number of bad cases for overrides fail"
        cases = [
            "title", # no pipe
            "title|", # pipe, but no value
            "title|bar", # invalid value (should be json: "bar")
            "|bar", # invalid key
        ]
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        for override in cases:
            with open(xml_fixture, 'rb') as fh:
                resp = self.client.post('/xml?id=16695&version=1', **{
                    'buffered': True,
                    'content_type': 'multipart/form-data',
                    'data': {
                        'xml': fh,
                        'override': [override],
                    }
                })

                expected_resp = {
                    'status': conf.ERROR,
                    'code': conf.BAD_OVERRIDES,
                    # 'message': '...',
                    # 'trace': '...',
                }

            self.assertEqual(resp.status_code, 400)
            self.assertTrue(utils.partial_match(expected_resp, resp.json))
            self.assertTrue(resp.json['trace'].startswith('Traceback (most recent call last):'))
            self.assertTrue(resp.json['message']) # one exists and isn't empty

    # this test is taking a long time ...
    def test_upload_invalid(self):
        "the response we expect when the scraped article-json is invalid"
        xml_fname = 'elife-16695-v1.xml.invalid'
        xml_upload_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        with patch('adaptor.call_lax', side_effect=AssertionError("test shouldn't make it this far!")):
            resp = self.client.post('/xml?id=16695&version=1', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': {
                    'xml': (open(xml_fixture, 'rb'), xml_upload_fname),
                }
            })
        self.assertEqual(resp.status_code, 400) # bad request data

        # ensure xml uploaded
        expected_path = join(self.temp_dir, xml_upload_fname)
        self.assertTrue(os.path.exists(expected_path))

        # ensure ajson scraped
        expected_ajson = join(self.temp_dir, xml_upload_fname) + '.json'
        self.assertTrue(os.path.exists(expected_ajson))

        expected_resp = {
            'status': conf.INVALID,
            'code': conf.ERROR_INVALID,
            # 'message': '...', # will probably change
            # 'trace': '...', # stacktrace
        }
        self.assertTrue(utils.partial_match(expected_resp, resp.json))
        self.assertTrue(resp.json['message'])
        # title is missing
        self.assertTrue(resp.json['trace'].startswith("None is not of type 'string'"), "actual trace: %s" % resp.json['trace'])

    def test_upload_with_overrides(self):
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)
        xml_upload_fname = 'elife-16695-v1.xml'

        override = {
            'title': 'foo',
            'statusDate': '2012-12-21T00:00:00Z'
        }
        serialized_overrides = scraper.serialize_overrides(override)

        payload = {
            'xml': (open(xml_fixture, 'rb'), xml_upload_fname),
            'override': serialized_overrides,
        }

        mock_lax_resp = {
            u'status': u'validated',
            u'force': True,
            u'dry-run': True,
            u'id': 16695,
            u'datetime': u'2017-07-04T07:37:24Z'
        }
        with patch('adaptor.call_lax', return_value=mock_lax_resp):
            resp = self.client.post('/xml?id=16695&version=1', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': payload,
            })
        # overrides params can be sent
        self.assertEqual(resp.status_code, 200)

        # overrides have been written
        scraped_ajson = join(self.temp_dir, xml_upload_fname) + '.json'
        ajson = json.load(open(scraped_ajson, 'r'))
        for key, expected_val in override.items():
            self.assertEqual(ajson['article'][key], expected_val)

    def test_upload_with_complex_overrides(self):
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)
        xml_upload_fname = 'elife-16695-v1.xml'

        expected = dict([
            ('title', '        '),
            ('elocationid', None),
            ('abstract', [1, [2, [3]]]),
            ('version', {'foo': 'bar'}),
        ])
        serialized_overrides = scraper.serialize_overrides(expected)

        payload = {
            'xml': (open(xml_fixture, 'rb'), xml_upload_fname),
            'override': serialized_overrides,
        }

        mock_lax_resp = {
            u'status': u'validated',
            u'force': True,
            u'dry-run': True,
            u'id': 16695,
            u'datetime': u'2017-07-04T07:37:24Z'
        }
        with patch('adaptor.call_lax', return_value=mock_lax_resp):
            resp = self.client.post('/xml?id=16695&version=1', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': payload,
            })
        # bad request (something failed validation)
        self.assertEqual(resp.status_code, 400)

        # ensure overrides survived transport and were written to article-json
        scraped_ajson = join(self.temp_dir, xml_upload_fname) + '.json'
        ajson = json.load(open(scraped_ajson, 'r'))
        for key, expected_val in expected.items():
            self.assertEqual(ajson['article'][key], expected_val)

    @patch('conf.API_PRE_VALIDATE', False)
    def test_bad_request_prevalidate_off(self):
        "local validation is skipped in favour of validation lax-side"
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        mock_lax_resp = {
            'status': conf.INVALID,
            'force': True,
            'dry-run': True,
            'id': 16695,
            'datetime': '2017-07-04T07:37:24Z'
        }
        with patch('adaptor.call_lax', return_value=mock_lax_resp): # don't call lax
            with patch('validate.main', side_effect=Exception("should not be called")):
                resp = self.client.post('/xml?id=16695&version=1', **{
                    'buffered': True,
                    'content_type': 'multipart/form-data',
                    'data': {
                        'xml': (open(xml_fixture, 'rb'), xml_fname),
                    }
                })
        self.assertEqual(resp.status_code, 400) # bad request

    def test_broken_glencoe_response(self):
        "the response we expect when the glencoe code fails"

        err_message = "informative error message"

        expected_resp = {
            'status': conf.ERROR,
            'code': conf.BAD_SCRAPE,
            'message': err_message,
            # 'trace': '...' # super long, can't predict, especially when mocking
        }
        with patch('glencoe.metadata', side_effect=AssertionError(err_message)):
            resp = self.client.post('/xml?id=36409&version=2', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': {
                    'xml': open(join(self.fixtures_dir, 'elife-36409-v2.xml'), 'rb'),
                },
            })

        self.assertEqual(resp.status_code, 400) # bad request
        self.assertTrue(utils.partial_match(expected_resp, resp.json))
        self.assertTrue(resp.json['trace'].startswith('Traceback (most'))

    def test_upload_xml_no_iiif_deposit(self):
        "api returns valid article-json with valid values for image widths and heights when iiif returns a 404"
        xml_fname = 'elife-24271-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        expected_lax_resp = {
            'status': conf.VALIDATED,
            'override': {},
            'ajson': base.load_ajson(xml_fixture + '.json')['article'],
            'message': None # this should trigger an error when logged naively by api.py but doesn't...
        }

        # don't call lax
        with patch('adaptor.call_lax', return_value=expected_lax_resp):
            # also, don't call iiif
            no_iiif_info = {}
            with patch('iiif.iiif_info', return_value=no_iiif_info): # another?
                resp = self.client.post('/xml?id=24271&version=1', **{
                    'buffered': True,
                    'content_type': 'multipart/form-data',
                    'data': {
                        'xml': (open(xml_fixture, 'rb'), xml_fname),
                    }
                })

        # ensure ajson validated
        expected_ajson_path = join(self.temp_dir, xml_fname) + '.json'
        success, _ = validate.main(open(expected_ajson_path, 'r', encoding='utf-8'))
        self.assertTrue(success)
        self.assertEqual(resp.status_code, 200)

def test_listfiles():
    expected = (
        ['bar.xml', 'foo.json'],
        ['/tmp/bar.xml', '/tmp/foo.json'])
    fixture = [
        '/tmp/foo.json',
        '/tmp/bar.xml'
    ]
    with patch('os.listdir', return_value=fixture):
        with patch('os.path.isfile', return_value=True):
            assert api.listfiles("/tmp") == expected

def test_listfiles__with_exts():
    expected_json = (['foo.json'],['/tmp/foo.json'])
    expected_xml =  (['bar.xml'],['/tmp/bar.xml'])
    fixture = [
        '/tmp/foo.json',
        '/tmp/bar.xml'
    ]
    with patch('os.listdir', return_value=fixture):
        with patch('os.path.isfile', return_value=True):
            assert api.listfiles("/tmp", ext_list=['.json']) == expected_json
            assert api.listfiles("/tmp", ext_list=['.xml']) == expected_xml
    
