import sys, json, copy
from et3.extract import path as p
from et3.render import render
from et3 import utils
from elifetools import parseJATS
from functools import partial, wraps
import logging
from collections import OrderedDict
from datetime import datetime
import time
import calendar
from slugify import slugify

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.FileHandler('scrape.log'))
LOG.level = logging.INFO

placeholder_version = 1
placeholder_pdf = "elife-00007-v1.pdf"
placeholder_status = "vor"
placeholder_related_articles = "10.7554/eLife.00240"
placeholder_image_alt = ""
placeholder_abstract = {
        "doi": "10.7554/eLife.09560.001",
        "content": [
            {
                "type": "paragraph",
                "text": "Abstract"
            }
        ]
    }
placeholder_license = "CC-BY-4.0"
placeholder_body = [{"type": "section",
            "title": "Introduction",
            "content": [
                {
                    "type": "paragraph",
                    "text": "Introduction"
                }]}]
placeholder_digest = {
        "doi": "10.7554/eLife.09560.002",
        "content": [
            {
                "type": "paragraph",
                "text": "Digest"
            }]}
placeholder_authorLine = "eLife et al"
placeholder_authors = [{
            "type": "person",
            "name": {
                "preferred": "Lee R Berger",
                "index": "Berger, Lee R"
            },
            "affiliations": [
                {
                    "name": [
                        "Evolutionary Studies Institute and Centre of Excellence in PalaeoSciences",
                        "University of the Witwatersrand"
                    ],
                    "address": {
                        "formatted": [
                            "Johannesburg",
                            "South Africa"
                        ],
                        "components": {
                            "locality": [
                                "Johannesburg"
                            ],
                            "country": "South Africa"
                        }
                    }
                }]}
                ]
#
# utils
#

def item_id(item):
    return parseJATS.doi(item)

def pipeline(*pline):
    "a wrapper around the typical list that helps with debugging"
    def wrapper(processor, item):
        try:
            return processor(item, pline)
        except Exception as err:
            def forn(x):
                if hasattr(x, '__name__'):
                    return 'fn:' + x.__name__
                return str(x)
            msg = "pipeline %r failed with: %s" % (map(forn, pline), err)
            LOG.error(item_id(item) + " - caught exception attempting to render: " + msg)
            raise
    return wrapper

def to_isoformat(time_struct):
    return datetime.utcfromtimestamp(calendar.timegm(time_struct)).isoformat()

def note(msg, level=logging.DEBUG):
    "a note logs some message about the value but otherwise doesn't interrupt the pipeline"
    # if this is handy, consider adding to et3?
    def fn(val):
        LOG.log(level, msg, extra={'value': val})
        return val
    return fn

def todo(msg):
    "this value requires more work"
    return note("todo: %s" % msg, logging.INFO)

def nonxml(msg):
    "we're scraping a value that doesn't appear in the XML"
    return note("nonxml: %s" % msg, logging.WARN)

def body_rewrite(body):
    body = image_uri_rewrite(body)
    body = mathml_rewrite(body)
    return body

def image_uri_rewrite(body_json):
    base_uri = "https://example.org/"
    for element in body_json:
        if (("type" in element and element["type"] == "image") or
            ("mediaType" in element)):
            if "uri" in element:
                element["uri"] = base_uri + element["uri"]
                # Add or edit file extension
                # TODO!!
        for content_index in ["content", "supplements", "sourceData"]:
            if content_index in element:
                try:
                    image_uri_rewrite(element[content_index])
                except TypeError:
                    # not iterable
                    pass

    return body_json


def mathml_rewrite(body_json):
    for element in body_json:
        if "type" in element and element["type"] == "mathml":
            if "mathml" in element:
                # Quick edits to get mathml to comply with the json schema
                mathml = "<math>" + element["mathml"] + "</math>"
                mathml = mathml.replace("<mml:", "<").replace("</mml:", "</")
                element["mathml"] = mathml

        if "content" in element:
            try:
                mathml_rewrite(element["content"])
            except TypeError:
                # not iterable
                pass
    return body_json

#
#
#

def is_poa(xmldoc):
    return False

def article_list(doc):
    return [parseJATS.parse_document(doc)]

def jats(funcname, *args, **kwargs):
    actual_func = getattr(parseJATS, funcname)
    @wraps(actual_func)
    def fn(soup):
        return actual_func(soup, *args, **kwargs)
    return fn

def category_codes(cat_list):
    return [slugify(cat, stopwords=['and']) for cat in cat_list]

def to_volume(volume):
    if not volume:
        # No volume on unpublished PoA articles, calculate based on current year
        volume = time.gmtime()[0] - 2011
    return int(volume)

#
# 
#

POA = OrderedDict([
    ('journal', OrderedDict([
        ('id', [jats('journal_id')]),
        ('title', [jats('journal_title')]),
        ('issn', [jats('journal_issn', 'electronic')]),
    ])),
    ('article', OrderedDict([
        ('status', [placeholder_status, todo('status')]),
        ('id', [jats('publisher_id')]),
        ('version', [placeholder_version, todo('version')]),
        ('type', [jats('article_type')]),
        ('doi', [jats('doi')]),
        ('title', [jats('title')]),
        ('published', [jats('pub_date'), to_isoformat]),
        ('volume', [jats('volume'), to_volume]),
        ('elocationId', [jats('elocation_id')]),
        ('pdf', [placeholder_pdf, todo('pdf')]),
        ('subjects', [jats('category'), category_codes]),
        ('research-organisms', [jats('research_organism')]),
        ('related-articles', [placeholder_related_articles, todo('related-articles')]),
        ('abstract', [placeholder_abstract, todo('abstract')]),

        # non-snippet values

        ('copyright', OrderedDict([
            ('license', [placeholder_license, todo('extract the licence code')]),
            ('holder', [jats('copyright_holder')]),
            ('statement', [jats('license')]),
        ])),
        ('authorLine', [placeholder_authorLine, todo('authorLine')]),
        ('authors', [placeholder_authors, todo('format authors')])
        
    ])
)])


VOR = copy.deepcopy(POA)
VOR['article'].update(OrderedDict([
        ('impactStatement', [jats('impact_statement')]),
        ('keywords', [jats('keywords')]),
        ('digest', [placeholder_digest, todo('digest')]),
        ('body', [jats('body'), body_rewrite]), # ha! so easy ...
        ('decisionLetter', [jats('decision_letter'), body_rewrite]),
        ('authorResponse', [jats('author_response'), body_rewrite]),
]))

# if has attached image ...
VOR['article'].update(OrderedDict([
    ('image', OrderedDict([
        ('alt', [placeholder_image_alt, todo('image alt')]),
        ('sizes', OrderedDict([
            ("2:1", OrderedDict([
                ("900", ["https://...", todo("vor article image sizes 2:1 900")]),
                ("1800", ["https://...", todo("vor article image sizes 2:1 1800")]),
            ])),
            ("16:9", OrderedDict([
                ("250", ["https://...", todo("vor article image sizes 16:9 250")]),
                ("500", ["https://...", todo("vor article image sizes 16:9 500")]),
            ])),
            ("1:1", OrderedDict([
                ("70", ["https://...", todo("vor article image sizes 1:1 70")]),
                ("140", ["https://...", todo("vor article image sizes 1:1 140")]),
            ])),
        ])),
    ]))
]))

#
# bootstrap
#

def main(doc):
    try:
        description = POA if is_poa(doc) else VOR
        print json.dumps(render(description, article_list(doc))[0], indent=4)
    except Exception as err:
        LOG.exception("failed to scrape article", extra={'doc': doc})
        raise

if __name__ == '__main__':
    main(sys.argv[1])
