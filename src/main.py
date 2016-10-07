import os, sys, json, copy
import threading
from et3.render import render
from elifetools import parseJATS
from functools import wraps
import logging
from collections import OrderedDict
from datetime import datetime
import time
import calendar
from slugify import slugify

import conf

LOG = logging.getLogger(__name__)
_handler = logging.FileHandler('scrape.log')
_handler.setLevel(logging.INFO)
_handler.setFormatter(conf._formatter)

LOG.addHandler(_handler)

#
# global mutable state! warning!
#

# not sure where I'm going with this, but I might send each
# action to it's own subprocess
VARS = threading.local()

def getvar(key, default=0xDEADBEEF):
    def fn(v):
        var = getattr(VARS, key, default)
        if var == 0xDEADBEEF:
            raise AttributeError("no var %r found" % key)
        return var
    return fn

def setvar(**kwargs):
    [setattr(VARS, key, val) for key, val in kwargs.items()]

#
# utils
#

def doi(item):
    return parseJATS.doi(item)

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

#
#
#


DISPLAY_CHANNEL_TYPES = {
    "Correction": "correction",
    "Editorial": "editorial",
    "Feature Article": "feature",
    "Feature article": "feature",
    "Insight": "insight",
    "Registered Report": "registered-report",
    "Research Advance": "research-advance",
    "Research Article": "research-article",
    "Research article": "research-article",
    "Short report": "short-report",
    "Tools and Resources": "tools-resources",

    # NOTE: have not seen the below ones yet, guessing
    "Research exchange": "research-exchange",
    "Retraction": "retraction",
    "Replication study": "replication-study",
}

def display_channel_to_article_type(display_channel_list):
    if not display_channel_list:
        return
    display_channel = display_channel_list[0]
    return DISPLAY_CHANNEL_TYPES.get(display_channel)

LICENCE_TYPES = {
    "http://creativecommons.org/licenses/by/3.0/": "CC-BY-3.0",
    "http://creativecommons.org/licenses/by/4.0/": "CC-BY-4.0",
    "http://creativecommons.org/publicdomain/zero/1.0/": "CC0-1.0"
}

def related_article_to_related_articles(related_article_list):
    related_articles = []
    if related_article_list:
        for related in related_article_list:
            try:
                doi = related["xlink_href"]
            except KeyError:
                continue
            if doi:
                related_articles.append(doi.split('.')[-1])
    if len(related_articles) <= 0:
        return None
    return related_articles

def is_poa_to_status(is_poa):
    return "poa" if is_poa else "vor"

def self_uri_to_pdf(self_uri_list):
    if self_uri_list:
        return self_uri_list[0]["xlink_href"]

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

def body_rewrite(body):
    body = image_uri_rewrite(body)
    body = mathml_rewrite(body)
    return body


#
#
#

def to_soup(doc):
    if isinstance(doc, basestring):
        if os.path.exists(doc):
            return parseJATS.parse_document(doc)
        return parseJATS.parse_xml(doc)
    # assume it's a file-like object and attempt to .read() it's contents
    return parseJATS.parse_xml(doc.read())

def jats(funcname, *args, **kwargs):
    actual_func = getattr(parseJATS, funcname)

    @wraps(actual_func)
    def fn(soup):
        return actual_func(soup, *args, **kwargs)
    return fn

def category_codes(cat_list):
    return [slugify(cat, stopwords=['and']) for cat in cat_list]

THIS_YEAR = time.gmtime()[0]
def to_volume(volume):
    if not volume:
        # No volume on unpublished PoA articles, calculate based on current year
        volume = THIS_YEAR - 2011
    return int(volume)

def clean(article_data):
    # Remove null or blank elements
    article_json = article_data # we're not dealing with json just yet ...
    remove_if_none = ["pdf", "relatedArticles"]
    for remove_index in remove_if_none:
        if remove_index in article_json["article"]:
            if article_json["article"][remove_index] is None:
                del article_json["article"][remove_index]

    remove_if_empty = ["impactStatement", "decisionLetter", "authorResponse"]
    for remove_index in remove_if_empty:
        if (article_json["article"].get(remove_index) is not None
            and (
                article_json["article"].get(remove_index) == ""
                or article_json["article"].get(remove_index) == []
                or article_json["article"].get(remove_index) == {})):
            del article_json["article"][remove_index]

    remove_from_copyright_if_none = ["holder"]
    for remove_index in remove_from_copyright_if_none:
        if remove_index in article_json["article"].get("copyright", {}):
            if article_json["article"]["copyright"][remove_index] is None:
                del article_json["article"]["copyright"][remove_index]

    return article_json

#
#
#

JOURNAL = OrderedDict([
    ('id', [jats('journal_id')]),
    ('title', [jats('journal_title')]),
    ('issn', [jats('journal_issn', 'electronic')]),
])

SNIPPET = OrderedDict([
    ('status', [jats('is_poa'), is_poa_to_status]),
    ('id', [jats('publisher_id')]),
    ('version', [getvar('version', 9)]),
    ('type', [jats('display_channel'), display_channel_to_article_type]),
    ('doi', [jats('doi')]),
    ('authorLine', [jats('author_line')]),
    ('title', [jats('title')]),
    ('published', [jats('pub_date'), to_isoformat]),
    ('volume', [jats('volume'), to_volume]),
    ('elocationId', [jats('elocation_id')]),
    ('pdf', [jats('self_uri'), self_uri_to_pdf]),
    ('subjects', [jats('category'), category_codes]),
    ('research-organisms', [jats('research_organism')]),
    ('abstract', [jats('abstract_json')]),
])
# https://github.com/elifesciences/api-raml/blob/develop/dist/model/article-poa.v1.json#L689
POA_SNIPPET = copy.deepcopy(SNIPPET)

# a POA contains the contents of a POA snippet
POA = copy.deepcopy(POA_SNIPPET)
POA.update(OrderedDict([
    ('copyright', OrderedDict([
        ('license', [jats('license_url'), LICENCE_TYPES.get]),
        ('holder', [jats('copyright_holder')]),
        ('statement', [jats('license')]),
    ])),
]))

# a VOR snippets contains the contents of a POA
VOR_SNIPPET = copy.deepcopy(POA)
VOR_SNIPPET.update(OrderedDict([
    ('impactStatement', [jats('impact_statement')]),
]))

# a VOR contains the contents of a VOR snippet
VOR = copy.deepcopy(VOR_SNIPPET)
VOR.update(OrderedDict([
    ('keywords', [jats('keywords')]),
    ('relatedArticles', [jats('related_article'), related_article_to_related_articles]),
    ('digest', [jats('digest_json')]),
    ('body', [jats('body'), body_rewrite]), # ha! so easy ...
    ('decisionLetter', [jats('decision_letter'), body_rewrite]),
    ('authorResponse', [jats('author_response'), body_rewrite]),
]))

def mkdescription(poa=True):
    "returns the description to scrape based on the article type"
    return OrderedDict([
        ('journal', JOURNAL),
        ('snippet', POA_SNIPPET if poa else VOR_SNIPPET),
        ('article', POA if poa else VOR),
    ])

#
# bootstrap
#

def render_single(doc, **overrides):
    try:
        setvar(**overrides)
        soup = to_soup(doc)
        description = mkdescription(parseJATS.is_poa(soup))
        return clean(render(description, [soup])[0])
    except Exception as err:
        LOG.error("failed to render doc with error: %s", err)
        raise

def main(doc=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', nargs="?", type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('--verbose', action="store_true", default=False)
    args = parser.parse_args()
    doc = args.infile if not doc else doc
    try:
        article_json = render_single(doc)
        print json.dumps(article_json, indent=4)
    except Exception:
        LOG.exception("failed to scrape article", extra={'doc': doc})
        raise

if __name__ == '__main__':
    main()
