from os.path import join
from .base import BaseCase
import conf, api

class One(BaseCase):
    def setUp(self):
        self.doc = join(self.fixtures_dir, 'elife-09560-v1.xml')
        self.small_doc = join(self.fixtures_dir, 'elife-16695-v1.xml')

    def tearDown(self):
        pass

    def test_schema_validates(self):
        spec = conf.API_SCHEMA
        self.assertTrue(api.validates(spec))
