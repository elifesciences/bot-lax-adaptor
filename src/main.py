import os, sys, json, copy, re
import threading
from et3.render import render, EXCLUDE_ME
from elifetools import parseJATS
from functools import wraps
import logging
from collections import OrderedDict
from datetime import datetime
import time
import calendar
from slugify import slugify
import conf, utils

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

def references_rewrite(references):
    "clean up values that will not pass validation temporarily"
    for ref in references:
        if "date" in ref:
            # Scrub non-numeric values from the date, which comes from the reference year
            ref["date"] = re.sub("[^0-9]", "", ref["date"])
        if ref.get("type") == "other":
            # The schema cannot support type other, turn this into a basic journal reference
            #  to pass validation
            ref["type"] = "journal"
            #if not "articleTitle" in ref:
            #    ref["articleTitle"] = "Placeholder article title for ref of type 'other'"
            if not "journal" in ref:
                ref["journal"] = {}
                ref["journal"]["name"] = []
                #ref["journal"]["name"].append("This is a transformed placeholder journal name for ref of type 'other'")
                if "source" in ref:
                    ref["journal"]["name"].append(ref["source"])
                    del ref["source"]
        if ref.get("type") == "journal" and not "pages" in ref:
            #ref["pages"] = "placeholderforrefwithnopages"
            pass
        if ref.get("type") == "book":
            if not "publisher" in ref:
                ref["publisher"] = {}
                ref["publisher"]["name"] = []
                #ref["publisher"]["name"].append("This is a placeholder book publisher name for ref that does not have one")

    return references

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

def discard_if_not_v1(v):
    "discards given value if the version of the article being worked on is not a v1"
    if getvar('version')(v) == 1:
        return v
    return EXCLUDE_ME

def authors_rewrite(authors):
    # Clean up phone number format
    for author in authors:
        if "phoneNumbers" in author:
            for i, phone in enumerate(author["phoneNumbers"]):
                # Only one phone number so far, simple replace to validate
                author["phoneNumbers"][i] = re.sub(r'[\(\) -]', '', phone)
    return authors

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
    ('version', [getvar('version')]),
    ('type', [jats('display_channel'), display_channel_to_article_type]),
    ('doi', [jats('doi')]),
    ('authorLine', [jats('author_line')]),
    ('title', [jats('title')]),
    ('published', [jats('pub_date'), to_isoformat, discard_if_not_v1]),
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
    ('authors', [jats('authors_json'), authors_rewrite])
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
    ('body', [jats('body')]), # ha! so easy ...
    ('references', [jats('references'), references_rewrite]),
    ('decisionLetter', [jats('decision_letter')]),
    ('authorResponse', [jats('author_response')]),
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
    msid, version = utils.version_from_path(getattr(doc, 'name', doc))
    try:
        article_json = render_single(doc, version=version)
        print json.dumps(article_json, indent=4)
    except Exception:
        LOG.exception("failed to scrape article", extra={'doc': doc, 'msid': msid, 'version': version})
        raise

if __name__ == '__main__':
    main()
