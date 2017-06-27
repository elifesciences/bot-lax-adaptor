
from os.path import join
from .base import BaseCase
import api

class One(BaseCase):
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

class Two(BaseCase):
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

    def test_upload_valid(self):
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
        expected_path = join(self.temp_dir, xml_fname)
        self.assertTrue(os.path.exists(expected_path), "uploaded xml cannot be found")
        self.assertTrue(os.path.isfile(expected_path), "uploaded xml is not a file??")

'''
    def test_upload_invalid(self):
        xml_fname = 'elife-00666-v1-invalid.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        self.client.post('/upload/', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': {
                # data, filename
                'xml': (open(xml_fixture, 'r'), 'elife-00666-v1.xml'),
            }
        })
        expected_path = join(self.temp_dir, 'elife-00666-v1.xml')
        self.assertTrue(os.path.exists(expected_path))
        self.assertTrue(os.path.isfile(expected_path))
        self.assert_flashes(lambda message: message.startswith('invalid'))

    def test_generate_file(self):
        # upload file
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)
        self.client.post('/upload/', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': {
                'xml': (open(xml_fixture, 'r'), xml_fname),
            }
        })
        #expected_path = join(self.temp_dir, xml_fname)
        # re-generate
        self.client.post('/generate/' + xml_fname, **{
            'data': {
                'filename': xml_fname,
            }
        })
        self.assert_flashes(lambda message: message.startswith('regenerated'))

    def test_validate_non_json_file(self):
        # upload file
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)
        self.client.post('/upload/', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': {
                'xml': (open(xml_fixture, 'r'), xml_fname),
            }
        })
        #expected_path = join(self.temp_dir, xml_fname)
        # re-generate
        self.client.post('/validate/' + xml_fname, **{
            'data': {
                'filename': xml_fname,
            }
        })
        self.assert_flashes(lambda message: message.startswith('not validated'))

    def test_validate_json_file(self):
        # upload file
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)
        self.client.post('/upload/', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': {
                'xml': (open(xml_fixture, 'r'), xml_fname),
            }
        })

        json_fname = xml_fname + '.json'
        self.client.post('/validate/' + json_fname, **{
            'data': {
                'filename': json_fname,
            }
        })
        self.assert_flashes(lambda message: message.startswith('valid'))

'''
