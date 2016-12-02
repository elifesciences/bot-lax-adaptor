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

    def test_generate_section_id(self):
        # Reset counter before test is run
        validate.section_id_counter = None
        first_section_id = validate.generate_section_id()
        self.assertEqual(first_section_id, 'phantom-s-1')
        second_section_id = validate.generate_section_id()
        self.assertEqual(second_section_id, 'phantom-s-2')

    def test_wrap_body_in_section(self):
        # Reset counter before test is run
        validate.section_id_counter = None
        body_json = [{"type": "paragraph"}]
        wrapped_body_json = validate.wrap_body_in_section(body_json)
        expected_body_json = [{'type': 'section', 'id': 'phantom-s-1',
                               'title': 'Main text', 'content': [{'type': 'paragraph'}]}]
        self.assertEqual(wrapped_body_json, expected_body_json)

    def test_mathml_rewrite(self):
        # For coverage test for list items
        body_json = [{'type': 'list', 'items': [[
            {'type': 'mathml', 'id': 'equ1',
             'mathml': '<mml:mrow><mml:mi>C</mml:mi></mml:mrow>'}]]}]
        expected = [{'type': 'list', 'items': [[
            {'type': 'mathml', 'id': 'equ1',
             'mathml': '<math><mrow><mi>C</mi></mrow></math>'}]]}]
        self.assertEqual(validate.mathml_rewrite(body_json), expected)

    def test_fix_section_id_if_missing(self):
        # Reset counter before test is run
        validate.section_id_counter = None
        body_json = [{'type': 'section'}]
        expected = [{'type': 'section', 'id': 'phantom-s-1'}]
        self.assertEqual(validate.fix_section_id_if_missing(body_json), expected)

    def test_fix_box_title_if_missing(self):
        body_json = [{'type': 'box'}]
        expected = [{'type': 'box', 'title': 'Placeholder box title because we must have one'}]
        self.assertEqual(validate.fix_box_title_if_missing(body_json), expected)

    """
    def test_references_rewrite_missing_date(self):
        references_json = [{}]
        expected = [{'date': '1000'}]
        self.assertEqual(validate.references_rewrite(references_json), expected)
    """

    def test_references_rewrite_book_missing_author(self):
        references_json = [{'type': 'book', 'date': '2016'}]
        expected = [{'type': 'book',
                     'date': '2016',
                     'authors': [{
                         "type": "person",
                         "name": {
                             "preferred": "Person One",
                             "index": "One, Person"
                         }
                     }]}]
        self.assertEqual(validate.references_rewrite(references_json), expected)

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
