import os, sys, json, copy
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
    # time_struct ll: time.struct_time(tm_year=2015, tm_mon=9, tm_mday=10, tm_hour=0, tm_min=0, tm_sec=0, tm_wday=3, tm_yday=253, tm_isdst=0)
    ts = calendar.timegm(time_struct) # ll: 1441843200
    ts = datetime.utcfromtimestamp(ts) # datetime.datetime(2015, 9, 10, 0, 0)
    return ts.isoformat() # 2015-09-10T00:00:00

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
    "Registered report": "registered-report",
    "Research Advance": "research-advance",
    "Research Article": "research-article",
    "Research article": "research-article",
    "Short report": "short-report",
    "Short Report": "short-report",
    "Tools and Resources": "tools-resources",

    # NOTE: have not seen the below ones yet, guessing
    "Research exchange": "research-exchange",
    "Retraction": "retraction",
    "Replication study": "replication-study",
}

def display_channel_to_article_type(display_channel_list):
    if not display_channel_list:
        LOG.warn("type: display channel list not provided")
        return
    display_channel = display_channel_list[0]
    retval = DISPLAY_CHANNEL_TYPES.get(display_channel)
    if not retval:
        LOG.warn("type: given value %r has no mention in idx: %s", display_channel, DISPLAY_CHANNEL_TYPES.keys())
    return retval

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

def cdnlink(path):
    use_other_cdn = True
    if use_other_cdn:
        _, padded_msid, filename = path.split('/') # 'articles', padded msid, filename
        return 'https://publishing-cdn.elifesciences.org/%s/%s' % (padded_msid, filename)
    return conf.CDN_PROTOCOL + ':' + conf.CDN_BASE_URL + '/' + path

def pdf_uri(triple):
    """predict an article's pdf url.
    some article types don't have a PDF (like corrections) and some
    older articles that should have a pdf, don't. this function doesn't
    concern itself with those latter exceptions."""
    content_type, msid, version = triple
    if content_type in ['Correction']:
        return EXCLUDE_ME
    padded_msid = str(int(msid)).zfill(5)
    filename = "elife-%s-v%s.pdf" % (padded_msid, version) # ll: elife-09560-v1.pdf
    return cdnlink('/'.join(['articles', padded_msid, filename]))

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
    subjects = []
    for cat in cat_list:
        subject = OrderedDict()
        subject['id'] = slugify(cat, stopwords=['and'])
        subject['name'] = cat
        subjects.append(subject)
    return subjects

THIS_YEAR = time.gmtime()[0]
def to_volume(volume):
    if not volume:
        # No volume on unpublished PoA articles, calculate based on current year
        volume = THIS_YEAR - 2011
    return int(volume)

def clean_if_none(article_or_snippet):
    remove_if_none = ["pdf", "relatedArticles", "digest", "abstract", "titlePrefix",
                      "acknowledgements"]
    for remove_index in remove_if_none:
        if remove_index in article_or_snippet:
            if article_or_snippet[remove_index] is None:
                del article_or_snippet[remove_index]
    return article_or_snippet

def clean_if_empty(article_or_snippet):
    remove_if_empty = ["impactStatement", "decisionLetter", "authorResponse",
                       "researchOrganisms", "keywords", "references",
                       "ethics", "appendices", "dataSets", "additionalFiles"]
    for remove_index in remove_if_empty:
        if (article_or_snippet.get(remove_index) is not None
            and (
                article_or_snippet.get(remove_index) == ""
                or article_or_snippet.get(remove_index) == []
                or article_or_snippet.get(remove_index) == {})):
            del article_or_snippet[remove_index]
    return article_or_snippet

def clean(article_data):
    # Remove null or blank elements
    article_json = article_data # we're not dealing with json just yet ...

    article_json["article"] = clean_if_none(article_json["article"])
    article_json["snippet"] = clean_if_none(article_json["snippet"])

    article_json["article"] = clean_if_empty(article_json["article"])
    article_json["snippet"] = clean_if_empty(article_json["snippet"])

    return article_json

def discard_if_not_v1(v):
    "discards given value if the version of the article being worked on is not a v1"
    if getvar('version')(v) == 1:
        return v
    return EXCLUDE_ME

'''
def discard_if(pred): # can also be used like: discard_if(None)
    def fn(v):
        if pred is None:
            return EXCLUDE_ME
        return EXCLUDE_ME if pred(v) else v
    return fn
'''

def discard_if_none_or_cc0(pair):
    holder, licence = pair
    if not holder or str(licence).upper().startswith('CC0-'):
        return EXCLUDE_ME
    return holder
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
    ('title', [jats('full_title_json')]),
    ('titlePrefix', [jats('title_prefix')]),
    ('published', [jats('pub_date'), to_isoformat]), # 'published' is the pubdate of the v1 article
    ('versionDate', [jats('pub_date'), to_isoformat, discard_if_not_v1]), # date *this version* published. provided by Lax.
    ('volume', [jats('volume'), to_volume]),
    ('elocationId', [jats('elocation_id')]),
    ('pdf', [(jats('display_channel'), jats('publisher_id'), getvar('version')), pdf_uri]),
    ('subjects', [jats('category'), category_codes]),
    ('researchOrganisms', [jats('research_organism')]),
    ('abstract', [jats('abstract_json')]),
])
# https://github.com/elifesciences/api-raml/blob/develop/dist/model/article-poa.v1.json#L689
POA_SNIPPET = copy.deepcopy(SNIPPET)

# a POA contains the contents of a POA snippet
POA = copy.deepcopy(POA_SNIPPET)
POA.update(OrderedDict([
    ('copyright', OrderedDict([
        ('license', [jats('license_url'), LICENCE_TYPES.get]),
        ('holder', [(jats('copyright_holder'), jats('license')), discard_if_none_or_cc0]),
        ('statement', [jats('license')]),
    ])),
    ('authors', [jats('authors_json')]),
    ('ethics', [jats('ethics_json')]),
    ('additionalFiles', [jats('supplementary_files_json')]),
    ('dataSets', [jats('datasets_json')]),
]))

# a VOR snippets contains the contents of a POA
VOR_SNIPPET = copy.deepcopy(POA)
VOR_SNIPPET.update(OrderedDict([
    ('impactStatement', [jats('impact_statement_json')]),
]))

# a VOR contains the contents of a VOR snippet
VOR = copy.deepcopy(VOR_SNIPPET)
VOR.update(OrderedDict([
    ('keywords', [jats('keywords_json')]),
    ('relatedArticles', [jats('related_article'), related_article_to_related_articles]),
    ('digest', [jats('digest_json')]),
    ('body', [jats('body')]), # ha! so easy ...
    ('references', [jats('references_json')]),
    ('appendices', [jats('appendices_json')]),
    ('acknowledgements', [jats('acknowledgements_json')]),
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

def instrument(description):
    # try:
    #    import newrelic.agent

    #    for key, pipeline in description.items():
    #        if isinstance(pipeline, dict): # OrderedDict is subtype of dict
    #            subdescription = pipeline
    #            instrument(subdescription) # recurse
    #        else:
    #            description[key] = map(newrelic.agent.FunctionTraceWrapper, pipeline)

    # except ImportError:
    #    pass

    return description

def render_single(doc, **overrides):
    try:
        setvar(**overrides)
        soup = to_soup(doc)
        description = mkdescription(parseJATS.is_poa(soup))
        description = instrument(description)
        return clean(render(description, [soup])[0])
    except Exception as err:
        LOG.error("failed to render doc with error: %s", err)
        raise

def main(doc):
    msid, version = utils.version_from_path(getattr(doc, 'name', doc))
    try:
        article_json = render_single(doc, version=version)
        return json.dumps(article_json, indent=4)
    except Exception:
        LOG.exception("failed to scrape article", extra={'doc': doc, 'msid': msid, 'version': version})
        raise

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', nargs="?", type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('--verbose', action="store_true", default=False)
    args = parser.parse_args()
    doc = args.infile
    print main(doc)
