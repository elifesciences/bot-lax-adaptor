from StringIO import StringIO
#import sys
import json
from os.path import join
from .base import BaseCase
import validate
import jsonschema

class TestArticleValidate(BaseCase):
    def setUp(self):
        self.doc_json = join(self.fixtures_dir, 'elife-09560-v1.xml.json')

    def tearDown(self):
        pass

    def test_main_bootstrap(self):
        "valid output is returned"
        results = validate.main(open(self.doc_json, 'r'))
        self.assertTrue(isinstance(results, dict))

    def test_main_bootstrap_fails(self):
        "invalid output raises a validation error"
        data = json.load(open(self.doc_json, 'r'))
        data['article']['type'] = 'unknown type that will cause a failure'
        strbuffer = StringIO(json.dumps(data))
        strbuffer.name = self.doc_json
        self.assertRaises(jsonschema.ValidationError, validate.main, strbuffer)

    def test_add_placeholders_for_validation(self):
        article = {'article': {'id': 12345, 'version': 2}}
        expected = {
            'article': {
                '-patched': True,
                'id': 12345,
                'version': 2,
                'stage': 'published',
                'versionDate': '2099-01-01T00:00:00Z',
                'statusDate': '2099-01-01T00:00:00Z',
            }}
        validate.add_placeholders_for_validation(article)
        self.assertEqual(article, expected)

    def test_is_poa_not_poa(self):
        # For test coverage
        self.assertFalse(validate.is_poa({}))
