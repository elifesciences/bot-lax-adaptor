from __future__ import print_function
import calendar
import copy
from collections import OrderedDict
from datetime import datetime
from functools import partial, wraps
import logging
import json
from os.path import join
import os
import re

from elifetools import parseJATS
from et3.extract import lookup as p
from et3.render import render, doall, EXCLUDE_ME
from et3.utils import requires_context
from isbnlib import mask, to_isbn13
from past.builtins import basestring
from slugify import slugify

import conf, utils, glencoe, iiif, cdn
from utils import ensure, is_file, lmap, lfilter

LOG = logging.getLogger(__name__)
_handler = logging.FileHandler(join(conf.LOG_DIR, 'scrape.log'))
_handler.setLevel(logging.INFO)
_handler.setFormatter(conf._formatter)
LOG.addHandler(_handler)

#
# utils
#

def doi(item):
    return parseJATS.doi(item)

def to_isoformat(time_struct):
    if not time_struct:
        return time_struct
    # time_struct ll: time.struct_time(tm_year=2015, tm_mon=9, tm_mday=10, tm_hour=0, tm_min=0, tm_sec=0, tm_wday=3, tm_yday=253, tm_isdst=0)
    ts = calendar.timegm(time_struct) # ll: 1441843200
    ts = datetime.utcfromtimestamp(ts) # datetime.datetime(2015, 9, 10, 0, 0)
    return utils.ymdhms(ts)

def is_poa_to_status(is_poa):
    return "poa" if is_poa else "vor"

def to_soup(doc):
    if isinstance(doc, basestring):
        if os.path.exists(doc):
            return parseJATS.parse_document(doc)
        return parseJATS.parse_xml(doc)
    # assume it's a file-like object and attempt to .read() it's contents
    return parseJATS.parse_xml(doc.read())

def jats(funcname, *args, **kwargs):
    aliases = {
        'msid': 'publisher_id',
    }
    actual_func = getattr(parseJATS, funcname, None) or getattr(parseJATS, aliases.get(funcname))
    if not actual_func:
        raise ValueError("you asked for %r from parseJATS but I couldn't find it!" % funcname)

    @wraps(actual_func)
    def fn(soup):
        return utils.sortdict(actual_func(soup, *args, **kwargs))
    return fn

#
#
#


DISPLAY_CHANNEL_TYPES = {
    "Book review": "scientific-correspondence",
    "Software review": "registered-report",
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
    "Data watch": "tools-resources",
    "Tools and Resources": "tools-resources",
    "Replication Study": "replication-study",
    "Replication study": "replication-study",
    "Review Article": "review-article",

    # NOTE: have not seen the below ones yet, guessing
    "Research exchange": "research-exchange", # deprecated in favour of Scientific Correspondence
    "Retraction": "retraction",
    "Scientific Correspondence": "scientific-correspondence",
    "Research Communication": "research-communication",
    "Research note": "short-report",
    "software review": "registered-report",
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
    # ll: [{'xlink_href': u'10.7554/eLife.09561', 'related_article_type': u'article-reference', 'ext_link_type': u'doi'}]
    def et(struct):
        return (struct.get('xlink_href') or '').rsplit('.', 1)[-1] or None
    # ll: ['09561'] or None
    return lfilter(None, map(et, related_article_list))

def mixed_citation_to_related_articles(mixed_citation_list):
    # ll: [{'article': {'authorLine': 'R Straussman et al',
    #      'authors': [{'given': u'R', 'surname': u'Straussman'}, ...}],
    #      'doi': u'10.1038/nature11183', 'pub-date': [2014, 2, 28], 'title': u'Pants-Party'},
    #      'journal': {'volume': u'487', 'lpage': u'504', 'name': u'Nature', 'fpage': u'500'}}]

    def et(struct):
        return OrderedDict([
            ('type', 'external-article'),
            ('articleTitle', p(struct, 'article.title')),
            ('journal', p(struct, 'journal.name')),
            ('authorLine', p(struct, 'article.authorLine')),
            ('uri', 'https://doi.org/%s' % p(struct, 'article.doi')),
        ])
    return lmap(et, mixed_citation_list)

def cdnlink(msid, filename):
    kwargs = {
        'padded-msid': utils.pad_msid(msid),
        'fname': filename
    }
    return conf.CDN % kwargs

def base_url(msid):
    return cdnlink(msid, '')

def iiiflink(msid, filename):
    kwargs = {
        'padded-msid': utils.pad_msid(msid),
        'fname': filename
    }
    raw_link = (conf.CDN_IIIF % kwargs)
    return utils.pad_filename(msid, raw_link)

def iiifsource(msid, filename):
    source = OrderedDict()
    source["mediaType"] = "image/jpeg"
    source["uri"] = iiiflink(msid, filename) + '/full/full/0/default.jpg'
    source["filename"] = re.sub(r'\.tif$', '.jpg', filename)
    return source

def pdf_uri(triple):
    """predict an article's pdf url.
    some article types don't have a PDF (like corrections) and some
    older articles that should have a pdf, don't. this function doesn't
    concern itself with those latter exceptions."""
    content_type, msid, version = triple
    if content_type and any(lmap(lambda type: type in ['Correction', 'Retraction'], content_type)):
        return EXCLUDE_ME
    filename = "ijm-%s.pdf" % (utils.pad_msid(msid))
    return cdnlink(msid, filename)

def xml_uri(params):
    """predict an article's xml url."""
    msid, version = params
    filename = "elife-%s-v%s.xml" % (utils.pad_msid(msid), version) # ll: elife-09560-v1.xml
    return cdnlink(msid, filename)

def figures_pdf_uri(triple):
    graphics, msid, version = triple
    filename_match = '-figsupp'

    if any(lmap(lambda graphic: graphic.get('xlink_href')
                and filename_match in graphic.get('xlink_href'), graphics)):
        filename = "elife-%s-figures-v%s.pdf" % (utils.pad_msid(msid), version) # ll: elife-09560-figures-v1.pdf
        figures_pdf_cdnlink = cdnlink(msid, filename)
        return cdn.url_exists(figures_pdf_cdnlink, msid)
    else:
        return None

def category_codes(cat_list):
    subjects = []
    for cat in cat_list:
        subject = OrderedDict()
        subject['id'] = slugify(cat, stopwords=['and', 'of'])
        subject['name'] = cat
        subjects.append(subject)
    return subjects

def handle_isbn(val):
    if val:
        return mask(to_isbn13(str(val)))

def to_volume(pair):
    pub_date, volume = pair
    if not volume:
        # no volume on unpublished PoA articles, calculate based on year published
        if isinstance(pub_date, basestring):
            # assume yyyy-mm-dd formatted string
            pub_year = int(pub_date[:4])
        else:
            # assume a timestruct
            pub_year = pub_date[0]  # to_isoformat(pub_date)[:4]
        volume = pub_year - (conf.JOURNAL_INCEPTION - 1) # 2011 for elife
    return int(volume)


def elocation_id_from_fpage_lpage(pair):
    fpage, lpage = pair
    return '%s-%s' % (fpage, lpage) if fpage and lpage else None


def to_int(value):
    return int(value) if value else None

def try_to_int(value):
    try:
        return int(value)
    except ValueError:
        return value
    return value

@requires_context
def discard_if_not_v1(ctx, ver):
    "discards given value if the version of the article being worked on is not a v1"
    if ctx['version'] == 1:
        return ver
    return EXCLUDE_ME

def getvar(varname):
    @requires_context
    def fn(ctx, _):
        return ctx[varname]
    return fn

'''
def discard_if(pred): # can also be used like: discard_if(None)
    def fn(v):
        if pred is None:
            return EXCLUDE_ME
        return EXCLUDE_ME if pred(v) else v
    return fn
'''

def fail_if_none(label):
    def wrap(v):
        ensure(v, "%s cannot be blank/empty/None" % label)
        return v
    return wrap

def discard_if_none_or_empty(v):
    if not v:
        return EXCLUDE_ME
    elif len(v) <= 0:
        return EXCLUDE_ME
    return v

def discard_if_none_or_cc0(pair):
    holder, licence = pair
    if not holder or str(licence).upper().startswith('CC0-'):
        return EXCLUDE_ME
    return holder

def not_applicable_if_none(v):
    if not v:
        return 'n/a'
    return v

def body(soup):
    body_json = jats('body_json', base_url(jats('publisher_id')(soup)))(soup)
    footnotes_json = jats('footnotes_json', base_url(jats('publisher_id')(soup)))(soup)
    if footnotes_json:
        footnotes_section = {"id": "footnotes",
                        "title": "Footnotes",
                        "type": "section",
                        "content": []}
        for f_json in footnotes_json:
            footnotes_section["content"].append(f_json)
        body_json.append(footnotes_section)
    return body_json

def appendices(soup):
    return jats('appendices_json', base_url(jats('publisher_id')(soup)))(soup)

#
# post processing
#

def visit(data, pred, fn, coll=None):
    "visits every value in the given data and applies `fn` when `pred` is true "
    if pred(data):
        if coll is not None:
            data = fn(data, coll)
        else:
            data = fn(data)
        # why don't we return here after matching?
        # the match may contain matches within child elements (lists, dicts)
        # we want to visit them, too
    if isinstance(data, OrderedDict):
        results = OrderedDict()
        for key, val in data.items():
            results[key] = visit(val, pred, fn, coll)
        return results
    elif isinstance(data, dict):
        return OrderedDict([(key, visit(val, pred, fn, coll)) for key, val in data.items()])
    elif isinstance(data, list):
        return [visit(row, pred, fn, coll) for row in data]
    # unsupported type/no further matches
    return data


def expand_videos(data):
    msid = data['snippet']['id']

    def pred(element):
        return isinstance(element, dict) and element.get("type") == "video"

    return visit(data, pred, partial(glencoe.expand_videos, utils.video_msid(msid)))

def expand_placeholder(msid, data):

    def pred(element):
        # dictionary with 'uri' key exists that hasn't been expanded yet
        return isinstance(element, dict) \
            and element.get("type") == "video" \
            and "placeholder" in element

    def fn(element):
        if isinstance(element.get("placeholder"), dict) and element.get("placeholder").get("uri"):
            expand_iiif_uri(msid, element, "placeholder")
        return element
    return visit(data, pred, fn)


def expand_image(msid, data):
    "image load from IIIF server"

    def pred(element):
        # dictionary with 'uri' key exists that hasn't been expanded yet
        return isinstance(element, dict) and "image" in element

    def fn(element):
        if element.get("type") == "video":
            element["image"] = cdnlink(msid, element["image"].split('/')[-1])
            element["image"] = utils.pad_filename(msid, element["image"])
        else:
            if isinstance(element.get("image"), dict) and element.get("image").get("uri"):
                element = expand_iiif_uri(msid, element, "image")
        return element
    return visit(data, pred, fn)

def expand_iiif_uri(msid, element, element_type):
    element[element_type]["uri"] = iiiflink(msid, element[element_type]["uri"].split('/')[-1])

    (width, height) = iiif.basic_info(msid, element[element_type]["uri"].split('%2F')[-1])
    element[element_type]["size"] = OrderedDict([("width", width), ("height", height)])
    element[element_type]["source"] = iiifsource(msid, element[element_type]["uri"].split('%2F')[-1])

    return element

def expand_uris(msid, data):
    "any 'uri' element is given a proper cdn link"

    protocol_matcher = re.compile(r'(http|ftp)s?:\/\/.*')

    def pred(element):
        # dictionary with 'uri' key exists that hasn't been expanded yet
        return isinstance(element, dict) \
            and "uri" in element \
            and not protocol_matcher.match(element["uri"])

    def fn(element):
        uri = element["uri"]
        # edge case: 'www' without a protocol
        if uri.startswith('www'):
            # all urls must have a protocol.
            # this should have been picked up in the bot or in production.
            fixed = 'http://' + element['uri']
            LOG.warn("broken url: %r has become %r" % (uri, fixed))
            element['uri'] = fixed
            return element
        # edge case: 'doi:' is not a protocol
        if uri.startswith('doi:'):
            fixed = 'https://doi.org/' + uri[4:]
            LOG.warn("broken url: %r has become %r" % (uri, fixed))
            element['uri'] = fixed
            return element
        # normal case: cdn link
        element["uri"] = cdnlink(msid, element["uri"])
        return element
    return visit(data, pred, fn)

def fix_extensions(data):
    "in some older articles there are uris with no file extensions. call before expand_uris"

    # 15852
    def pred(element):
        return isinstance(element, dict) \
            and element.get("type") == "image" \
            and element.get("image") \
            and isinstance(element["image"], dict) \
            and not os.path.splitext(element["image"]["uri"])[1] # ext in pair of (fname, ext) is empty

    def fn(element, missing):
        missing.append(utils.subdict(element, ['type', 'id', 'uri']))
        element["image"]["uri"] += ".tif"
        return element

    missing = []
    data = visit(data, pred, fn, missing)

    if missing and 'snippet' in data: # test cases rarely have a 'snippet' in them
        context = {
            'msid': data['snippet']['id'],
            'version': data['snippet']['version'],
            'missing': missing
        }
        LOG.info("encountered article with %s images with missing file extensions. assuming .tif", len(missing), extra=context)

    return data

def prune(data):
    prune_if_none = [
        "pdf", "relatedArticles", "digest", "abstract", "titlePrefix",
        "acknowledgements",
    ]
    prune_if_empty = [
        "impactStatement", "decisionLetter", "authorResponse",
        "researchOrganisms", "keywords", "references",
        "ethics", "appendices", "dataSets", "additionalFiles",
        "funding",
        "-history",
    ]
    empty = [[], {}, ""]

    def pred(element):
        # visit any element that contains any of the above keys
        return isinstance(element, dict) and utils.contains_any(element, prune_if_none + prune_if_empty)

    def fn(element):
        element = utils.rmkeys(element, prune_if_none, lambda val: val is None)
        element = utils.rmkeys(element, prune_if_empty, lambda val: val in empty)
        return element
    return visit(data, pred, fn)

def format_isbns(data):
    def pred(element):
        return isinstance(element, dict) and 'isbn' in element

    def fn(element):
        element['isbn'] = handle_isbn(element['isbn'])
        return element

    return visit(data, pred, fn)

'''
# this is validation code rather than transformation code
# validation is handled by our laborious efforts with json-schema and CI
# it needs a really good reason to be uncommented or it's going to be removed
def check_authors(data):
    "in postprocessing, check all authors have competingInterests except in certain article types"
    skip_types = ['correction']
    if data['snippet']['type'] in skip_types:
        return data
    # continue
    context = {
        'msid': data['snippet'].get('id'),
        'version': data['snippet'].get('version')
    }
    if 'authors' in data['snippet']:
        for author in data['snippet']['authors']:
            if (author.get('type') in ['person', 'group']
                    and author.get('competingInterests') is None):
                context['author'] = author
                raise ValueError("Author missing required competingInterests", context)
    return data
'''

def non_nil_image_dimensions(ctx, data):
    """articles not yet in iiif will have their dimensions populated with None.
    a width or height of None will fail validation with a standard obscure jsonschema dump.
    used by the API for pre-production articles."""
    if not ctx.get('fill-missing-image-dimensions'):
        return data

    def pred(element):
        return isinstance(element, dict) \
            and 'image' in element \
            and 'size' in element['image']

    def fix(element):
        if not element['image']['size']['height'] or not element['image']['size']['width']:
            element['image']['size']['height'] = 1
            element['image']['size']['width'] = 1
        return element

    return visit(data, pred, fix)

DUMMY_DATE = '2099-01-01T00:00:00Z'

def placeholders_for_validation(data):
    """add any missing values to allow article-json to pass json schema validation
    please make any placeholders OBVIOUS while still remaining valid data."""

    art = data['article']

    if not '-meta' in art:
        # probably a bad scrape or an old fixture or ...
        art['-meta'] = {}

    # simple indicator that this article content contains patched values
    art['-meta']['patched'] = True

    # an article will always have a pubdate, so we don't know if it's actually published or not...
    art['stage'] = 'published'

    # the statusDate is when an article transitioned from POA to VOR and can't be known
    # in all cases without consulting the article history
    if 'statusDate' not in art:
        art['statusDate'] = DUMMY_DATE

    if 'versionDate' not in art:
        # a versionDate is when this specific version of an article was published
        # a versionDate wouldn't be present if we're dealing with a version > 1
        art['versionDate'] = DUMMY_DATE

    if 'references' in art:
        for ref in art.get('references'):
            # reference, add missing date value
            if not ref.get('date'):
                ref['date'] = '1000'
            elif ref.get('date') and not re.match(r'^[0-9]*$', ref.get('date')):
                ref['date'] = '1000'

            # reference, add placeholder author if missing
            if not ref.get('editors') and not ref.get('authors'):
                ref['authors'] = [
                    {
                        "name": "n/a",
                        "type": "group"
                    }
                    ]

    data['article'] = art

    return data

def manual_overrides(ctx, data):
    "replace top-level article keys with new values provided in ctx.override"
    overrides = ctx.get('override', {})
    ensure(isinstance(overrides, dict), "given mapping of overrides is not a dictionary")
    # possibly add support for dotted paths in future?
    for key, value in overrides.items():
        data['article'][key] = value
    return data


def postprocess(data, ctx):
    msid = data['snippet']['id']
    data = doall(data, [
        # check_authors,
        fix_extensions,
        expand_videos,
        partial(expand_uris, msid),
        partial(expand_image, msid),
        partial(expand_placeholder, msid),
        format_isbns,
        prune,
        placeholders_for_validation,

        partial(non_nil_image_dimensions, ctx),

        # do this last. anything that comes after this can't be altered by user-provided values
        partial(manual_overrides, ctx),
    ])
    return data
#
#
#

JOURNAL = OrderedDict([
    ('id', [jats('journal_id')]),
    ('title', [jats('journal_title')]),
    ('issn', [jats('journal_issn', 'electronic')]),
])

SNIPPET = OrderedDict([
    # ('-meta', OrderedDict([
    #     ('location', [getvar('location')]),
    # ])),
    ('-history', OrderedDict([
        ('received', [jats('history_date', date_type='received'), to_isoformat, discard_if_none_or_empty]),
        ('accepted', [jats('history_date', date_type='accepted'), to_isoformat, discard_if_none_or_empty]),
    ])),
    ('status', [jats('is_poa'), is_poa_to_status]),
    ('id', [jats('publisher_id')]),
    ('version', [getvar('version')]),
    ('type', [jats('display_channel'), display_channel_to_article_type]),
    ('doi', [jats('doi')]),
    ('authorLine', [jats('author_line'), discard_if_none_or_empty]),
    ('title', [jats('full_title_json')]),
    ('titlePrefix', [jats('title_prefix_json')]),
    ('published', [jats('pub_date'), to_isoformat, fail_if_none('pubdate')]), # 'published' is the pubdate of the v1 article
    ('versionDate', [jats('pub_date'), to_isoformat, discard_if_not_v1]), # date *this version* published. provided by Lax.
    ('statusDate', [jats('pub_date'), to_isoformat, discard_if_not_v1]), # date *this version* published. provided by Lax.
    ('volume', [(jats('pub_date'), jats('volume')), to_volume]),
    ('issue', [jats('issue'), to_int]),
    ('fpage', [jats('fpage'), try_to_int, not_applicable_if_none]),
    ('lpage', [jats('lpage'), try_to_int, not_applicable_if_none]),
    ('elocationId', [(jats('fpage'), jats('lpage')), elocation_id_from_fpage_lpage, not_applicable_if_none]),
    ('pdf', [(jats('display_channel'), jats('publisher_id'), getvar('version')), pdf_uri]),
    # ('xml', [(jats('publisher_id'), getvar('version')), xml_uri]),
    ('figuresPdf', [(jats('graphics'), jats('publisher_id'), getvar('version')), figures_pdf_uri, discard_if_none_or_empty]),
    ('subjects', [jats('category'), category_codes, discard_if_none_or_empty]),
    ('researchOrganisms', [jats('research_organism_json')]),
    ('abstract', [jats('abstract_json')]),
])
# https://github.com/elifesciences/api-raml/blob/develop/dist/model/article-poa.v1.json#L689
POA_SNIPPET = copy.deepcopy(SNIPPET)

# a POA contains the contents of a POA snippet
POA = copy.deepcopy(POA_SNIPPET)
POA.update(OrderedDict([
    ('copyright', OrderedDict([
        ('license', [jats('license_url'), LICENCE_TYPES.get]),
        ('holder', [(jats('copyright_holder_json'), jats('license')), discard_if_none_or_cc0]),
        ('statement', [jats('license_json')]),
    ])),
    ('authors', [jats('authors_json'), discard_if_none_or_empty]),
    ('reviewers', [jats('editors_json'), discard_if_none_or_empty]),
    ('ethics', [jats('ethics_json')]),
    ('funding', OrderedDict([
        ('awards', [jats('funding_awards_json'), discard_if_none_or_empty]),
        ('statement', [jats('funding_statement_json'), discard_if_none_or_empty]),
    ])),
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
    # ('-related-articles-internal', [jats('related_article'), related_article_to_related_articles]),
    # ('-related-articles-external', [jats('mixed_citations'), mixed_citation_to_related_articles]),
    ('digest', [jats('digest_json')]),
    ('body', [body]),
    ('references', [jats('references_json')]),
    ('appendices', [appendices]),
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

def expand_location(path):
    # if isinstance(path, file):
    if is_file(path):
        path = path.name

    if path.startswith('https://s3-external-1.amazonaws.com/') or path.startswith('https://s3.amazonaws.com/'):
        # it's being downloaded from a bucket, no worries
        return path

    # resolve any symlinks
    # the backfill uses symlinks to the article-xml dir
    path = os.path.abspath(os.path.realpath(path))

    if re.match(r".*article-xml/articles/.+\.xml$", path):
        # this article is coming from the local ./article-xml/ directory, which
        # is almost certainly a git checkout. we want a location that looks like:
        # https://raw.githubusercontent.com/elifesciences/elife-article-xml/5f1179c24c9b8a8b700c5f5bf3543d16a32fbe2f/articles/elife-00003-v1.xml
        rc, rawsha = utils.run_script(["cat", "elife-article-xml.sha1"])
        ensure(rc == 0, "failed to read the contents of './elife-article-xml.sha1'")
        sha = rawsha.strip()
        fname = os.path.basename(path)
        return "https://raw.githubusercontent.com/elifesciences/elife-article-xml/%s/articles/%s" % (sha, fname)

    # who knows what this path is ...
    LOG.warn("scraping article content in a non-repeatable way. path %r not found in article-xml dir. please don't send the results to lax", path)
    return path

def render_single(doc, **ctx):
    try:
        # passing a 'location' value will override pulling the value from the doc
        ctx['location'] = expand_location(ctx.get('location', doc))
        soup = to_soup(doc)
        description = mkdescription(parseJATS.is_poa(soup))
        article_data = postprocess(list(render(description, [soup], ctx))[0], ctx)
        return article_data

    except Exception as err:
        LOG.error("failed to render doc %r with error: %s", ctx.get('location', '[no location]'), err)
        raise

def serialize_overrides(override_map):
    def serialize(pair):
        key, val = pair
        ensure(isinstance(key, basestring), "key must be a string")
        ensure('|' not in key, "key must not contain a pipe")
        key = key.strip()
        ensure(key, "key must not be empty")
        return '|'.join([key, json.dumps(val)])
    return lmap(serialize, override_map.items())

def deserialize_overrides(override_list):
    def splitter(string):
        if isinstance(string, list):
            pair = string # already split into pairs, return what we have
            return pair
        ensure('|' in string, "override key and value must be seperated by a pipe '|'", ValueError)
        first, rest = string.split('|', 1)
        ensure(rest.strip(), "a value must be provided. use 'null' without quotes to use an empty value", ValueError)
        return first, rest
    pairs = lmap(splitter, override_list)
    return OrderedDict([(key, utils.json_loads(val)) for key, val in pairs])

def main(doc, args=None):
    args = args or {}
    msid, version = utils.version_from_path(getattr(doc, 'name', doc))
    ctx = {
        'version': version,
        'override': {},
        'fill-missing-image-dimensions': False
    }
    ctx.update(args)
    try:
        article_json = render_single(doc, **ctx)
        return json.dumps(article_json, indent=4)

    except AssertionError:
        # business error
        log_ctx = {
            'doc': str(doc), # context needs to be json serializable
            'msid': msid,
            'version': version,
            'override': ctx['override'],
        }
        LOG.error("failed to scrape article", extra=log_ctx)
        raise

    except Exception:
        # unhandled exception
        log_ctx = {
            'doc': str(doc), # context needs to be json serializable
            'msid': msid,
            'version': version,
            'render-ctx': ctx,
            # 'override': ctx['override'],
        }
        LOG.exception("failed to scrape article", extra=log_ctx)
        raise

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', type=argparse.FileType('r'))
    parser.add_argument('--verbose', action="store_true", default=False)
    parser.add_argument('--override', nargs=2, action="append")
    args = vars(parser.parse_args())
    doc = args.pop('infile')
    args['override'] = deserialize_overrides(args['override'] or [])
    print(main(doc, args))
