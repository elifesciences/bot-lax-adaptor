import os
from os.path import join
from .base import BaseCase
from adapt import read_from_fs, do

class Ingest(BaseCase):
    def setUp(self):
        self.ingest_dir = join(self.fixtures_dir, 'dir-ingest', 'v1')

    def tearDown(self):
        pass

    def test_adaptor_v1(self):
        inc, out = read_from_fs(self.ingest_dir)
        do(inc, out)
        self.assertEqual(len(out.invalids), 0)
        self.assertEqual(len(out.errors), 0)
        self.assertEqual(len(out.passes), len(os.listdir(self.ingest_dir)))
