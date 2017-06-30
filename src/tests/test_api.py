from os.path import join
from . import base
import api, validate, utils

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

class Two(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


import os, shutil, tempfile
from flask_testing import TestCase

class Web(TestCase):
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

    def test_upload_valid_xml(self):
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        resp = self.client.post('/xml', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': {
                'xml': (open(xml_fixture, 'r'), xml_fname),
            }
        })
        self.assertEqual(resp.status_code, 200)

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

        # ensure ajson validates
        success, _ = validate.main(open(expected_ajson_path, 'r'))
        self.assertTrue(success)

    def test_upload_invalid(self):
        xml_fname = 'elife-00666-v1.xml.invalid'
        xml_upload_fname = 'elife-00666-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        resp = self.client.post('/xml', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': {
                'xml': (open(xml_fixture, 'r'), xml_upload_fname),
            }
        })
        self.assertEqual(resp.status_code, 400) # bad data

        # ensure xml uploaded
        expected_path = join(self.temp_dir, 'elife-00666-v1.xml')
        self.assertTrue(os.path.exists(expected_path))

        # ensure ajson scraped
        expected_ajson = join(self.fixtures_dir, 'elife-00666-v1.xml.json')
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
