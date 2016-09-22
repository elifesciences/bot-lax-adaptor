import os
from os.path import join
from .base import BaseCase
import adapt
from adapt import read_from_fs, do
import unittest

def requires_lax(fn):
    try:
         adapt.find_lax()
         return fn
    except AssertionError:
        return unittest.skip("missing lax")(fn)

class Ingest(BaseCase):
    def setUp(self):
        self.ingest_dir = join(self.fixtures_dir, 'dir-ingest', 'v1')

    def tearDown(self):
        pass

    @requires_lax
    def test_adaptor_v1(self):
        inc, out = read_from_fs(self.ingest_dir)
        do(inc, out)
        self.assertEqual(len(out.invalids), 0)
        self.assertEqual(len(out.errors), 0)
        self.assertEqual(len(out.passes), len(os.listdir(self.ingest_dir)))
