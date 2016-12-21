import os, shutil, tempfile
from os.path import join
from flask_testing import TestCase

class Web(TestCase):
    maxDiff = None
    this_dir = os.path.realpath(os.path.dirname(__file__))
    fixtures_dir = join(this_dir, 'fixtures')

    render_templates = False

    # http://blog.paulopoiati.com/2013/02/22/testing-flash-messages-in-flask/
    def assert_flashes(self, expected_message, expected_category='message'):
        with self.client.session_transaction() as session:
            try:
                # multiple requests with no rendering means flash messages accumulate
                # take the last message in the list
                flash = session['_flashes'][-1]
                category, message = flash
            except KeyError:
                raise AssertionError('nothing flashed')

            if callable(expected_message):
                assert expected_message(message), "flash %r failed predicate: %r" % (flash, expected_message)
            else:
                assert message, "non-nil message expected"
            assert expected_category == category

    def create_app(self):
        import web
        self.temp_dir = tempfile.mkdtemp(suffix='bot-lax-test')
        assert self.temp_dir.startswith('/tmp/'), '!!!'
        web.app.config.update(**{
            'TESTING': True, # necessary?
            'SECRET_KEY': os.urandom(24), # necessary for uploads apparently
            'UPLOAD_FOLDER': self.temp_dir
        })
        return web.app

    def tearDown(self):
        print 'removing', self.temp_dir
        shutil.rmtree(self.temp_dir)

    def test_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_upload_valid(self):
        xml_fname = 'elife-16695-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        self.client.post('/upload/', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': {
                'xml': (open(xml_fixture, 'r'), xml_fname),
            }
        })
        expected_path = join(self.temp_dir, xml_fname)
        self.assertTrue(os.path.exists(expected_path))
        self.assertTrue(os.path.isfile(expected_path))
        self.assert_flashes(lambda message: message.startswith('valid'))

    def test_upload_invalid(self):
        xml_fname = 'elife-00666-v1.xml'
        xml_fixture = join(self.fixtures_dir, xml_fname)

        self.client.post('/upload/', **{
            'buffered': True,
            'content_type': 'multipart/form-data',
            'data': {
                # data, filename
                'xml': (open(xml_fixture, 'r'), xml_fname),
            }
        })
        expected_path = join(self.temp_dir, xml_fname)
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
