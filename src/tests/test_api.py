import json
from os.path import join
from . import base
import api, validate, utils, main as scraper, conf
from mock import patch
import os, shutil, tempfile
from flask_testing import TestCase

class One(base.BaseCase):
    def setUp(self):
        self.doc = join(self.fixtures_dir, 'elife-09560-v1.xml')
        self.small_doc = join(self.fixtures_dir, 'elife-16695-v1.xml')

    def tearDown(self):
        pass

    def test_schema_validates(self):
        self.assertTrue(api.validate_schema())

    '''
    # this approach has promise, but all the libraries in this domain are woefully
    # implemented and maintained. I've had to modify swagger-tester and swagger-parser
    # quite a bit aleady just to get this far. I need:
    # * the ability to override the test for certain cases.
    # * the ability to continue testing other paths/methods/parameters if any one fails
    # * the ability to setup and teardown state for any given test
    def test_foo(self):
        import conf
        from swagger_tester import swagger_test
        path = join(conf.PROJECT_DIR, 'schema', 'api.yaml')
        print 'path',path
        swagger_test(path, resolver=api.AsdfResolver('api'))
    '''


class FlaskTestCase(TestCase):
    maxDiff = None
    this_dir = os.path.realpath(os.path.dirname(__file__))
    fixtures_dir = join(this_dir, 'fixtures')
    render_templates = False

    def create_app(self):
        self.temp_dir = tempfile.mkdtemp(suffix='bot-lax-api-test')
        cxx = api.create_app({
            'DEBUG': True,
            'UPLOAD_FOLDER': self.temp_dir
        })
        return cxx.app

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

class Two(FlaskTestCase):
    def test_upload_valid_xml(self):
        "the response we expect when everything happens perfectly"
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        expected_lax_resp = {
            'status': conf.VALIDATED,
            'override': {},
            'ajson': base.load_ajson(xml_fixture + '.json')['article']
        }

        with patch('adaptor.call_lax', return_value=expected_lax_resp):
            resp = self.client.post('/xml', **{
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
        success, _ = validate.main(open(expected_ajson_path, 'rb'))
        self.assertTrue(success)

        # ensure ajson is successfully sent to lax
        self.assertEqual(resp.status_code, 200)

        del resp.json['ajson']['-meta'] # remove the -meta key from the response.
        self.assertEqual(resp.json, expected_lax_resp)

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
            resp = self.client.post('/xml', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': payload,
            })

        # success
        self.assertEqual(resp.status_code, 200)

        # remove the meta because we can't compare it
        del resp.json['ajson']['-meta']

        # response is exactly as we anticipated
        self.assertEqual(mock_lax_resp, resp.json)

    def test_bad_upload(self):
        "the response we expect when the xml fails to upload"
        pass

    def test_bad_scrape(self):
        "the response we expect the xml fails to scrape"
        pass

    def test_upload_invalid(self):
        "the response we expect when the scraped article-json is invalid"
        xml_fname = 'elife-00666-v1.xml.invalid'
        xml_upload_fname = 'elife-00666-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        resp = self.client.post('/xml', **{
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
            'code': 'invalid-article-json',
            'message': 'the generated article-json failed validation', # will probably change
            #'trace': '...', # stacktrace
        }
        resp = resp.json
        self.assertTrue(utils.partial_match(expected_resp, resp))
        self.assertTrue(resp['trace'].startswith("None is not of type u'string'")) # title is missing

    def test_upload_with_overrides(self):
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)
        xml_upload_fname = 'elife-16695-v1.xml'

        expected = {
            'title': 'foo',
            'statusDate': '2012-12-21T00:00:00Z'
        }
        serialized_overrides = scraper.serialize_overrides(expected)

        payload = {
            'xml': (open(xml_fixture, 'rb'), xml_upload_fname),
            'override': serialized_overrides,
        }
        resp = self.client.post('/xml', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': payload,
        })
        # overrides params can be sent
        self.assertEqual(resp.status_code, 200)

        # overrides have been written
        scraped_ajson = join(self.temp_dir, xml_upload_fname) + '.json'
        ajson = json.load(open(scraped_ajson, 'r'))
        for key, expected_val in expected.items():
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
        resp = self.client.post('/xml', **{
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

    def test_broken_glencoe_response(self):
        "the response we expect when the glencoe code fails"

        err_message = "informative error message"

        expected_resp = {
            'status': conf.ERROR,
            'code': 'error-scraping-xml',
            'message': err_message,
            #'trace': '...' # super long, can't predict, especially when mocking
        }
        with patch('glencoe.validate_gc_data', side_effect=AssertionError(err_message)):
            resp = self.client.post('/xml', **{
                'buffered': True,
                'content_type': 'multipart/form-data',
                'data': {
                    'xml': open(join(self.fixtures_dir, 'elife-00666-v1.xml'), 'rb'),
                },
            })

        self.assertEqual(resp.status_code, 400) # bad request
        self.assertTrue(utils.partial_match(expected_resp, resp.json))
        self.assertTrue(resp.json['trace'].startswith('Traceback (most'))
