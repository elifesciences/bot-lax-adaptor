import json
from unittest import TestCase
import os
from os.path import join

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
    this_dir = os.path.realpath(os.path.dirname(__file__))
    fixtures_dir = join(this_dir, 'fixtures')
