import json
from unittest import TestCase
import os
from os.path import join

THIS_DIR = os.path.realpath(os.path.dirname(__file__))
FIXTURES_DIR = join(THIS_DIR, 'fixtures')

def fixture_path(path):
    return os.path.join(FIXTURES_DIR, path)

def read_fixture(path):
    return open(fixture_path(path), 'r').read()

def load_ajson(path, string=False):
    # loads article json from given path, stripping out the -meta fields
    # that will vary between scrapes (making comparisons difficult
    if string:
        ajson = json.loads(path)
    else:
        ajson = json.load(open(path, 'r'))
    del ajson['article']['-meta']
    del ajson['snippet']['-meta']
    return ajson

class BaseCase(TestCase):
    maxDiff = None
    this_dir = THIS_DIR
    fixtures_dir = FIXTURES_DIR
