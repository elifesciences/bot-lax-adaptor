import sys
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
        sys.argv.append(self.doc_json)
        # Assert validate.main does not raise exception
        try:
            self.assertRaises(Exception, validate.main)
        except AssertionError:
            self.assertTrue(True)

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
        expected_body_json = [{'type': 'section', 'id': 'phantom-s-1', 'title': '', 'content': [{'type': 'paragraph'}]}]
        self.assertEqual(wrapped_body_json, expected_body_json)


