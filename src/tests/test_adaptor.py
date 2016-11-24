import os, json
from os.path import join
from .base import BaseCase
import adaptor as adapt, fs_adaptor, conf
#from adaptor import read_from_fs, do
import adaptor
import unittest
from mock import patch

def requires_lax(fn):
    try:
        adapt.find_lax()
        return fn
    except AssertionError:
        return unittest.skip("missing lax")(fn)

class Ingest(BaseCase):
    def setUp(self):
        self.ingest_dir = join(self.fixtures_dir, 'dir-ingest', 'v1')
        self.num_ingest_dir = len(os.listdir(self.ingest_dir))
        spanner = 1
        self.num_ingest_dir_xml = self.num_ingest_dir - spanner

    def tearDown(self):
        pass

    '''
    @requires_lax # requires lax IN A CERTAIN STATE :( disabling for now
    def test_adaptor_v1(self):
        inc, out = read_from_fs(self.ingest_dir)
        do(inc, out)
        self.assertEqual(len(out.invalids), 0)
        self.assertEqual(len(out.errors), 0)
        self.assertEqual(len(out.valids), self.num_ingest_dir_xml)
    '''

class Adapt(BaseCase):
    def setUp(self):
        self.ingest_dir = join(self.fixtures_dir, 'dir-ingest')
        self.ingest_v1_dir = join(self.ingest_dir, 'v1')
        self.out = fs_adaptor.OutgoingQueue()

        self.inc = fs_adaptor.IncomingQueue(self.ingest_v1_dir, conf.INGEST)
        # 09560, artificially promoted to top of stack
        self.valid_request = list(self.inc)[0]

    def tearDown(self):
        pass

    def test_handler_bad_json(self):
        "bad json request generates an error"
        adapt.handler("pants-party", self.out)
        self.assertEqual(len(self.out.errors), 1)

    def test_handler_good_json_but_invalid(self):
        "good json but invalid request generates an error"
        adapt.handler('{"I-hope-you-have-a-very": "pants-party"}', self.out)
        self.assertEqual(len(self.out.errors), 1)

    def test_handler_bad_bad_data(self):
        "something about the data causes an unhandled exception that generate an error"
        adapt.handler(lambda x: x, self.out)
        self.assertEqual(len(self.out.errors), 1)
        self.assertTrue(self.out.errors[0]["message"].startswith("unhandled error"))

    def test_handler_bad_location(self):
        "location with missing file generates an error"
        self.valid_request['location'] = 'file://' + join(conf.PROJECT_DIR, 'does-not-exist.xml')
        adapt.handler(self.valid_request, self.out)
        self.assertEqual(len(self.out.errors), 1)
        self.assertTrue(self.out.errors[0]['message'].startswith("failed to download"))

    def test_handler_bad_location_outside_project_root(self):
        "file at location may exist but is outside of project dir"
        self.valid_request['location'] = 'file:///dev/null'
        adapt.handler(self.valid_request, self.out)
        self.assertEqual(len(self.out.errors), 1)
        self.assertTrue(self.out.errors[0]['message'].startswith("refusing to download"))

    def test_handler_bad_render(self):
        "article xml fails to convert empty article to article-json"
        self.valid_request['location'] = 'file://' + join(self.ingest_dir, 'bad', 'empty.xml')
        adapt.handler(self.valid_request, self.out)
        self.assertEqual(len(self.out.errors), 1)
        self.assertTrue(self.out.errors[0]['message'].startswith("failed to render"))

    @unittest.skip("huh - can't seem to break rendering with truncated files")
    def test_handler_bad_render2(self):
        "article xml fails to convert truncated xml to article-json"
        self.valid_request['location'] = 'file://' + join(self.ingest_dir, 'bad', 'truncated.xml')
        adapt.handler(self.valid_request, self.out)
        self.out.dump()
        self.assertEqual(len(self.out.errors), 1)
        self.assertTrue(self.out.errors[0]['message'].startswith("failed to render"))

    @patch('conf.DEBUG', True)
    @patch('adaptor.call_lax', lambda *args, **kwargs: {'status': conf.INVALID, 'message': 'mock'})
    def test_bootstrap(self):
        v3_dir = join(self.ingest_dir, 'v3')
        argstr = '--type fs --action ingest+publish --target %s' % v3_dir
        args = ['adaptor.py']
        args.extend(argstr.split())
        with patch('sys.argv', args):
            adapt.bootstrap()

    # what a hack this test is!
    @patch('conf.SEND_LAX_PATCHED_AJSON', True)
    def test_patched_data(self):
        "we can optionally send lax the patched version of the article-json"
        expected = {'-patched': True}

        def call_lax(*args, **kwargs):
            art = json.loads(kwargs['article_json'])['article']
            for key, val in expected.items():
                self.assertEqual(art[key], val)
            return {'status': conf.INGESTED, 'message': 'mock'}
        with patch('adaptor.call_lax', call_lax):
            adaptor.do(*adaptor.read_from_fs(join(self.ingest_dir, 'v3')))
