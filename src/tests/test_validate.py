from __future__ import absolute_import
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import json
from os.path import join
from .base import BaseCase
from src import validate
import jsonschema


class TestArticleValidate(BaseCase):
    def setUp(self):
        self.doc_json = join(self.fixtures_dir, 'elife-09560-v1.xml.json')

    def tearDown(self):
        pass

    def test_main_bootstrap(self):
        "valid output is returned"
        valid, results = validate.main(open(self.doc_json, 'r'))
        self.assertTrue(isinstance(results, dict))
        self.assertTrue(isinstance(valid, bool))

    def test_main_bootstrap_fails(self):
        "invalid output raises a validation error"
        data = json.load(open(self.doc_json, 'r'))
        data['article']['type'] = 'unknown type that will cause a failure'
        strbuffer = StringIO(json.dumps(data))
        strbuffer.name = self.doc_json
        self.assertRaises(jsonschema.ValidationError, validate.main, strbuffer)

    def test_is_poa_not_poa(self):
        # For test coverage
        self.assertFalse(validate.is_poa({}))


class TestValidateStructuredAbstract(BaseCase):
    def setUp(self):
        self.doc_json = join(self.fixtures_dir, 'elife-99999-v1.xml.json')

    def test_main_valid(self):
        "valid output is returned"
        valid, results = validate.main(open(self.doc_json, 'r'))
        self.assertTrue(valid)
