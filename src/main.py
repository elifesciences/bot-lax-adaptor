import sys, json
from et3.extract import path as p
from et3.render import render
from et3 import utils
from elifetools import parseJATS

def article_list(doc):
    return [parseJATS.parse_document(doc)]

def parser(funcname, *args, **kwargs):
    def fn(soup):
        return getattr(parseJATS, funcname)(soup, *args, **kwargs)
    return fn

description = {
    'journal': {
        'id': [1],
        'title': ['eLife']
    },
    'article': {
        'title': [parser('title')],
        'impact-statement': [parser('impact_statement')],
    }
}

if __name__ == '__main__':
    doc = sys.argv[1]
    print json.dumps(render(description, article_list(doc)), indent=4)
