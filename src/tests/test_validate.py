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
                               'title': '', 'content': [{'type': 'paragraph'}]}]
        self.assertEqual(wrapped_body_json, expected_body_json)

    def test_video_rewrite(self):
        body_json = [{'type': 'video', 'uri': 'video.mov'}]
        expected = [{'width': 640,
                     'image': 'https://example.org/video.mov',
                     'height': 480, 'sources':
                     [{'mediaType': 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"',
                       'uri': 'https://example.org/video.mov'}],
                     'type': 'video'}]
        self.assertEqual(validate.video_rewrite(body_json), expected)

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

    def test_references_rewrite_missing_date(self):
        references_json = [{}]
        expected = [{'date': '1000'}]
        self.assertEqual(validate.references_rewrite(references_json), expected)

    def test_references_rewrite_journal_missing_pages(self):
        references_json = [{'type': 'journal',
                            'articleTitle': '',
                            'journal': '',
                            'date': '2016',
                            'authors': ''}]
        expected = [{'type': 'journal',
                     'articleTitle': '',
                     'journal': '',
                     'date': '2016',
                     'authors': '',
                     'pages': 'placeholderforrefwithnopages'}]
        self.assertEqual(validate.references_rewrite(references_json), expected)

    def test_references_rewrite_book_missing_data(self):
        references_json = [{'type': 'book',
                            'date': '2016',
                            'authors': ''}]
        expected = [{'type': 'book',
                     'date': '2016',
                     'authors': '',
                     'publisher': {'name': ['This is a placeholder book publisher name for ref that does not have one']},
                     'bookTitle': 'Placeholder book title for book or book-chapter missing one'
                     }]
        self.assertEqual(validate.references_rewrite(references_json), expected)

    def test_references_rewrite_thesis_missing_author(self):
        references_json = [{'type': 'thesis', 'date': '2016'}]
        expected = [{'type': 'thesis',
                     'date': '2016',
                     'author': {
                         "type": "person",
                         "name": {
                             "preferred": "Person One",
                             "index": "One, Person"
                         }
                     }}]
        self.assertEqual(validate.references_rewrite(references_json), expected)

    def test_is_poa_not_poa(self):
        # For test coverage
        self.assertFalse(validate.is_poa({}))
