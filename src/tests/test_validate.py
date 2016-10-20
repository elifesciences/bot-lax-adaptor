#import sys
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
        "output written to stdout"
        # article-json derived from xml can't pass validation
        # by attempting and failing we cover a lot of code
        self.assertRaises(jsonschema.ValidationError, validate.main, open(self.doc_json, 'r'))

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

    def test_fix_image_attributes_if_missing(self):
        body_json = [{'type': 'image'}]
        expected = [{'type': 'image', 'title': 'This a placeholder for a missing image title'}]
        self.assertEqual(validate.fix_image_attributes_if_missing(body_json), expected)

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

    def test_is_poa_not_poa(self):
        # For test coverage
        self.assertFalse(validate.is_poa({}))
