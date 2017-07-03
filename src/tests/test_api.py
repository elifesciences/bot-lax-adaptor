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
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        expected_lax_resp = {
            'status': conf.VALIDATED,
            'requested-action': conf.INGEST,
            'force': True,
            'dry-run': True,
            'datetime': '2017-06-30T07:37:07Z',
            'token': 'pants',
            'id': '16695',
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

    def test_bad_upload(self):
        "xml fails to upload"
        pass

    def test_bad_scrape(self):
        "article json fails to scrape xml"
        pass

    def test_upload_invalid(self):
        "article json fails to validate"
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
            'status': 'invalid',
            'xml': xml_upload_fname,
            'code': 'invalid-article-json',
            #'trace': '...', # stacktrace
            'json': xml_upload_fname + '.json',
            #'message': '' # will probably change
        }
        resp = resp.json
        self.assertTrue(utils.partial_match(expected_resp, resp))

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

class Three(FlaskTestCase):
    def test_response(self):
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)
        xml_upload_fname = 'elife-16695-v1.xml'

        override = {
            'title': 'foo',
            'statusDate': '2012-12-21T00:00:00Z'
        }
        payload = {
            'xml': (open(xml_fixture, 'rb'), xml_upload_fname),
            'override': scraper.serialize_overrides(override),
        }
        resp = self.client.post('/xml', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': payload,
        })
        # successfully did everything
        self.assertEqual(resp.status_code, 200)

        # remove the meta because we can't compare it
        del resp.json['ajson']['-meta']

        # wrangle the fixture :(
        expected_ajson = base.load_ajson(xml_fixture + '.json')['article']
        for key, val in override.items():
            expected_ajson[key] = val

        # resp, ll:
        # {u'status': u'validated', 'ajson': ..., u'code': None, u'requested-action': u'ingest', u'validate-only?': True, u'forced?': True, u'datetime': u'2017-07-03T08:07:10Z', u'token': u'2cae8aa0-e274-4890-8d96-d6eb2a54a908', u'override': {u'statusDate': u'2012-12-21T00:00:00Z', u'title': u'foo'}, u'message': u'(dry-run)', u'id': 16695}

        expected_response = {
            'requested-action': 'ingest',
            'force': True,
            'dry-run': True,
            'status': conf.VALIDATED,
            'ajson': expected_ajson, # with overrides, with -meta excluded
            'override': override, # the map of given overrides
        }
        self.assertTrue(utils.partial_match(expected_response, resp.json))
