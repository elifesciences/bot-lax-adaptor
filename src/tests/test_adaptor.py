from os.path import join
from .base import BaseCase
from adapt import read_from_fs, do

class TestIngest(BaseCase):
    def setUp(self):
        self.ingest_dir = join(self.fixtures_dir, 'dir-ingest')

    def tearDown(self):
        pass

    def test_adaptor(self):
        inc, out = read_from_fs(self.ingest_dir)
        do(inc, out)
