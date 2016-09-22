import os
from os.path import join
from .base import BaseCase
import utils #, adapt
import fs_adaptor
from jsonschema import ValidationError

class FS(BaseCase):
    def setUp(self):
        self.ingest_dir = join(self.fixtures_dir, 'dir-ingest', 'v1')
    
    def test_incoming(self):
        inst = fs_adaptor.IncomingQueue(self.ingest_dir, 'ingest')
        spanner = 1
        self.assertEqual(len(os.listdir(self.ingest_dir)) - spanner, len(list(inst)))

    def test_incoming_messages(self):
        inst = fs_adaptor.IncomingQueue(self.ingest_dir, 'ingest')
        map(utils.validate_request, list(inst)) # raises exceptions if invalid
        
    def test_fs_incoming_never_generates_invalid_requests(self):
        inst = fs_adaptor.IncomingQueue(self.ingest_dir, action='pants-party')
        self.assertRaises(ValidationError, list, inst)
        inst.close()

    '''
    def test_fs_outgoing(self):
        inc = fs_adaptor.IncomingQueue(self.ingest_dir, 'ingest')
        out = fs_adaptor.OutgoingQueue()
        adapt.do
        inc.foo
        out.bar
        #@mock.patch('call_lax'
        #adapt.do(inc, out)
    '''
