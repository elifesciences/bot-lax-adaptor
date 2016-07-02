import sys, json
from et3.extract import path as p
from et3.render import render
from et3 import utils
from elifetools import parseJATS
from functools import partial
import logging
from collections import OrderedDict
from datetime import datetime
import time
from slugify import slugify

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.FileHandler('scrape.log'))

def article_list(doc):
    return [parseJATS.parse_document(doc)]

def jats(funcname, *args, **kwargs):
    def fn(soup):
        return getattr(parseJATS, funcname)(soup, *args, **kwargs)
    return fn

def nonxml(attr):
    LOG.warn("non-xml value %r" % attr)
    return None

def todo(msg):
    def fn(val):
        LOG.info(msg, extra={'value': val})
        return val
    return fn

def to_isoformat(time_struct):
    return datetime.fromtimestamp(time.mktime(time_struct)).isoformat()

def category_codes(cat_list):
    return [slugify(cat, stopwords=['and']) for cat in cat_list]

description = OrderedDict([
    ('journal', OrderedDict([
        ('id', [jats('journal_id')]),
        ('title', [jats('journal_title')]),
        ('issn', [jats('journal_issn', 'electronic')]),
    ])
    ),
    ('article', OrderedDict([
        ('id', [jats('publisher_id')]),
        ('version', [nonxml('version')]),
        ('type', [jats('article_type')]),
        ('doi', [jats('doi')]),
        ('title', [jats('title')]),
        ('published', [jats('pub_date'), to_isoformat]),
        ('volume', [jats('volume'), int]),
        ('issue', [nonxml('issue')]),
        ('elocationId', [jats('elocation_id')]),
        ('copyright', OrderedDict([
            ('licence', [jats('license'), todo('extract the licence code')]),
            ('holder', [jats('copyright_holder')]),
         ])),
        ('pdf', [nonxml('pdf url')]),
        ('subjects', [jats('category'), category_codes]),
        ('research-organisms', [jats('research_organism')]),
        ('related-articles', [jats('related_article')]),
        ('abstract', OrderedDict([
            ('doi', [jats('doi'), lambda v: "%s.001" % v, todo\
                 ("is abstract doi logic cleverer than this?")]),
            ('content', [jats('abstract'), todo("paragraphize this")])
        ])),
        
    ])
)])

def main(doc):
    try:
        print json.dumps(render(description, article_list(doc))[0], indent=4)
    except Exception as err:
        LOG.exception("failed to scrape article", extra={'doc': doc})

if __name__ == '__main__':
    main(sys.argv[1])
