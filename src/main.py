import os, sys, json, copy
from et3.render import render
from elifetools import parseJATS
from functools import wraps
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

placeholder_abstract = {
    "doi": "10.7554/eLife.09560.001",
    "content": [{
        "type": "paragraph",
        "text": "Abstract"
    }]
}

placeholder_digest = {
    "doi": "10.7554/eLife.09560.002",
    "content": [{
        "type": "paragraph",
        "text": "Digest"
    }]
}

placeholder_authorLine = "eLife et al"

placeholder_authors = [{
    "type": "person",
    "name": {
        "preferred": "Lee R Berger",
        "index": "Berger, Lee R"
    },
    "affiliations": [{
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
    }]
}]

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

def display_channel_to_article_type(display_channel_list):
    if not display_channel_list:
        return    
    types = {
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
    display_channel = display_channel_list[0]
    return types.get(display_channel)

def license_url_to_license(license_url):
    idx = {
        "http://creativecommons.org/licenses/by/3.0/": "CC-BY-3.0",
        "http://creativecommons.org/licenses/by/4.0/": "CC-BY-4.0",
        "http://creativecommons.org/publicdomain/zero/1.0/": "CC0-1.0"
    }
    return idx.get(license_url)

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
    if os.path.exists(doc):
        return parseJATS.parse_document(doc)
    return parseJATS.parse_xml(doc)

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
        if article_json["article"].has_key(remove_index):
            if article_json["article"][remove_index] == None:
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
        if article_json["article"].get("copyright", {}).has_key(remove_index):
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
    ('status', [jats('is_poa'), is_poa_to_status]), # shared by both POA and VOR snippets but not obvious in schema
    ('id', [jats('publisher_id')]),
    ('version', [placeholder_version, todo('version')]),
    ('type', [jats('display_channel'), display_channel_to_article_type]),
    ('doi', [jats('doi')]),
    ('authorLine', [placeholder_authorLine, todo('authorLine')]),
    ('title', [jats('title')]),
    ('published', [jats('pub_date'), to_isoformat]),
    ('volume', [jats('volume'), to_volume]),
    ('elocationId', [jats('elocation_id')]),
    ('pdf', [jats('self_uri'), self_uri_to_pdf]),
    ('subjects', [jats('category'), category_codes]),
    ('research-organisms', [jats('research_organism')]),
    ('abstract', [placeholder_abstract, todo('abstract')]),
])
# https://github.com/elifesciences/api-raml/blob/develop/dist/model/article-poa.v1.json#L689
POA_SNIPPET = copy.deepcopy(SNIPPET)

POA = copy.deepcopy(POA_SNIPPET)
POA.update(OrderedDict([
    ('copyright', OrderedDict([
        ('license', [jats('license_url'), license_url_to_license]),
        ('holder', [jats('copyright_holder')]),
        ('statement', [jats('license')]),
    ])),
    ('authors', [placeholder_authors, todo('format authors')])
]))

VOR_SNIPPET = copy.deepcopy(POA_SNIPPET)
VOR_SNIPPET.update(OrderedDict([
    ('impactStatement', [jats('impact_statement')]),    
]))

VOR = copy.deepcopy(VOR_SNIPPET)
VOR.update(OrderedDict([
    ('keywords', [jats('keywords')]),
    ('relatedArticles', [jats('related_article'), related_article_to_related_articles]),
    ('digest', [placeholder_digest, todo('digest')]),
    ('body', [jats('body'), body_rewrite]), # ha! so easy ...
    ('decisionLetter', [jats('decision_letter'), body_rewrite]),
    ('authorResponse', [jats('author_response'), body_rewrite]),
]))

def mkdescription(poa=True):
    return OrderedDict([
        ('journal', JOURNAL),
        ('snippet', POA_SNIPPET if poa else VOR_SNIPPET),
        ('article', POA if poa else VOR),      
    ])

#
# bootstrap
#

def render_single(doc):
    soup = to_soup(doc)
    description = mkdescription(parseJATS.is_poa(soup))
    return clean(render(description, [soup])[0])

def main(doc):
    try:
        article_json = render_single(doc)
        print json.dumps(article_json, indent=4)
    except Exception:
        LOG.exception("failed to scrape article", extra={'doc': doc})
        raise

if __name__ == '__main__':  # pragma: no cover
    main(sys.argv[1]) # pragma: no cover
