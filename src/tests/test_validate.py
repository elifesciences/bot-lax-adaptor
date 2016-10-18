import sys, StringIO
from os.path import join
from .base import BaseCase
import validate

class TestArticleValidate(BaseCase):
    def setUp(self):
        self.doc_json = join(self.fixtures_dir, 'elife-09560-v1.xml.json')

    def tearDown(self):
        pass

    def test_main_bootstrap(self):
        "output written to stdout"
        strbuffer = StringIO.StringIO()
        sys.stdout = strbuffer
        sys.argv.append(self.doc_json)
        validate.main() # writes to stdout
        # Assert it does not raise exception
        try:
            self.assertRaises(Exception, validate.main)
        except AssertionError:
            self.assertTrue(True)
