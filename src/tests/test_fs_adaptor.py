import os
from os.path import join
from .base import BaseCase
import utils #, adapt
import adapt, conf, fs_adaptor
from jsonschema import ValidationError

class FS(BaseCase):
    def setUp(self):
        self.ingest_dir = join(self.fixtures_dir, 'dir-ingest', 'v1')
        self.num_ingest_dir = len(os.listdir(self.ingest_dir))
        spanner = 1
        self.num_ingest_dir_xml = self.num_ingest_dir - spanner
    
    def test_incoming(self):
        "the number of messages to be ingested match the number of xml files in directory to be ingested"
        inst = fs_adaptor.IncomingQueue(self.ingest_dir, 'ingest')
        self.assertEqual(self.num_ingest_dir_xml, len(list(inst)))

    def test_incoming_messages(self):
        "each message generated is a valid request"
        inst = fs_adaptor.IncomingQueue(self.ingest_dir, 'ingest')
        map(utils.validate_request, list(inst)) # raises ValidationException if invalid

    def test_fs_incoming_never_generates_invalid_requests(self):
        "invalid requests never generate a message"
        inst = fs_adaptor.IncomingQueue(self.ingest_dir, action='pants-party')
        self.assertRaises(ValidationError, list, inst)

    def test_fs_outgoing_valid(self):
        "valid responses can be written without errors"
        inc = fs_adaptor.IncomingQueue(self.ingest_dir, 'ingest')
        out = fs_adaptor.OutgoingQueue()

        valid_request = list(inc)[0]
        valid_response = adapt.mkresponse(conf.INGESTED, "dummy-ingested-message", request=valid_request)
        valid_response_json = utils.json_dumps(valid_response)
        out.write(valid_response_json)
        self.assertEqual(len(out.valids), 1)
        self.assertEqual(len(out.invalids), 0)
        self.assertEqual(len(out.errors), 0)

    def test_fs_outgoing_invalid(self):
        inc = fs_adaptor.IncomingQueue(self.ingest_dir, conf.PUBLISH)
        out = fs_adaptor.OutgoingQueue()
        
        valid_request = list(inc)[0]
        valid_response = adapt.mkresponse(conf.PUBLISHED, "dummy-published-message", request=valid_request)
        valid_response_json = utils.json_dumps(valid_response)
        out.write(valid_response_json)
        self.assertEqual(len(out.valids), 1)
        self.assertEqual(len(out.invalids), 0)
        self.assertEqual(len(out.errors), 0)

    def test_fs_outgoing_dump(self):
        "purely for code coverage"
        out = fs_adaptor.OutgoingQueue()
        out.dump()
        out.close()
