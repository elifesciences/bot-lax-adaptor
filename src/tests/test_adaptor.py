import re
from os.path import join
import unittest

from unittest.mock import patch

from . import base
from src import adaptor as adapt, adaptor, fs_adaptor, conf, utils

class Logic(base.BaseCase):
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
        self.assertEqual(len(self.out.errors), 1)
        self.assertTrue(self.out.errors[0]['message'].startswith("failed to render"))

    def test_http_download(self):
        # this needs to be an UTF-8 XML document
        # without a proper 'Content-Type: application/xml; encoding=utf-8'
        # header being attached to the response
        test_url = 'https://cdn.elifesciences.org/articles/18722/elife-18722-v2.xml'
        xml_text = adaptor.http_download(test_url)
        # this is a crappy quick regex to extract the XML tags we need
        titles_of_appendices = re.findall('<title>Appendix[^<]*</title>', xml_text)
        self.assertIn(u'<title>Appendix\xa01</title>', titles_of_appendices)


class Main(base.BaseCase):
    def setUp(self):
        self.ingest_dir = join(self.fixtures_dir, 'dir-ingest-small', 'v1')

        # a basic mock response from lax
        self.call_lax_resp = {
            'status': conf.VALIDATED,
            'message': 'mock',
            'token': 'a',
            'id': 'b',
        }

        # we're not testing the scraping here, we're testing the response from lax
        # by calling adaptor.main directly we're obliged to pass a directory by we
        # don't need to do any scraping.
        # the ingest_dir contains just one article and this patch return the ajson
        fixture = base.load_ajson(join(self.ingest_dir, 'elife-09560-v1.xml.json'))

        self.patchers = [
            # careful here: I was patching main.render_single with the fixture directly
            # and it ate 18GB of memory and crashed computer :(
            patch('src.main.render_single', lambda *args, **kwargs: fixture),
        ]
        [p.start() for p in self.patchers]

    def tearDown(self):
        [p.stop() for p in self.patchers]

    @patch('src.adaptor.call_lax', lambda *args, **kwargs: {'status': conf.INVALID, 'message': 'mock'})
    def test_invalid_ingest_publish(self):
        "ingest+publish actions handle 'invalid' responses"
        argstr = '--type fs --action ingest+publish --target %s' % self.ingest_dir
        adapt.main(*argstr.split())

    @patch('src.adaptor.call_lax', lambda *args, **kwargs: {'status': conf.ERROR, 'message': 'mock'})
    def test_error_ingest_publish(self):
        "ingest+publish actions handle 'error' responses"
        argstr = '--type fs --action ingest+publish --target %s' % self.ingest_dir
        adapt.main(*argstr.split())

    @patch('src.adaptor.call_lax', lambda *args, **kwargs: {'status': conf.VALIDATED, 'message': 'mock'})
    def test_validated_ingest_publish(self):
        "ingest+publish actions handle 'validated' responses"
        argstr = '--type fs --action ingest+publish --validate-only --target %s' % self.ingest_dir
        adapt.main(*argstr.split())

    def test_extra_response_data_from_lax(self):
        "ensure bot-lax handles anything extra that lax may return that would fail validation against the response schema"
        argstr = '--type fs --action ingest+publish --validate-only --target %s' % self.ingest_dir

        # have lax return something bogus
        self.call_lax_resp.update({'pants?': 'party!'})

        with patch('src.adaptor.call_lax', lambda *args, **kwargs: self.call_lax_resp):
            # .write is the 'success' method
            with patch('src.fs_adaptor.OutgoingQueue.write') as mock:
                adapt.main(*argstr.split())
                self.assertTrue(mock.called) # `assert_called` gone missing in 3?

class DoublePubGood(base.BaseCase):
    def test_already_published_response_means_aok(self):
        "bot-lax coerces already-published error responses to successful 'published' responses"
        lax_resp = {
            'status': conf.ERROR,
            'message': 'mock',
            'token': 'a',
            'id': 'b',

            'code': 'already-published'
        }

        # coercion happens
        resp = adapt.mkresponse(**lax_resp)
        self.assertEqual(resp['status'], conf.PUBLISHED)

        # coercion doesn't result in an invalid response
        utils.validate(resp, conf.RESPONSE_SCHEMA)
