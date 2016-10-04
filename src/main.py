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
import re

import conf
conf.LOG

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.FileHandler('scrape.log'))
LOG.level = logging.INFO

placeholder_version = 1

placeholder_box_title_if_missing = "Placeholder box title because we must have one"

placeholder_related_article = OrderedDict({
            "type": "research-article",
            "status": "vor",
            "id": "09561",
            "version": 1,
            "doi": "10.7554/eLife.09561",
            "authorLine": "Paul HGM Dirks et al",
            "title": "Geological and taphonomic context for the new hominin species <i>Homo naledi</i> from the Dinaledi Chamber, South Africa",
            "published": "2015-09-10T00:00:00Z",
            "statusDate": "2015-09-10T00:00:00Z",
            "volume": 4,
            "elocationId": "e09561",
            "pdf": "https://elifesciences.org/content/4/e09561.pdf",
            "subjects": [
                "genomics-evolutionary-biology"
            ],
            "impactStatement": "A new hominin species found in a South African cave is part of one of the most unusual hominin fossil assemblages on record.",
            "image": {
                "alt": "",
                "sizes": {
                    "2:1": {
                        "900": "https://placehold.it/900x450",
                        "1800": "https://placehold.it/1800x900"
                    },
                    "16:9": {
                        "250": "https://placehold.it/250x141",
                        "500": "https://placehold.it/500x281"
                    },
                    "1:1": {
                        "70": "https://placehold.it/70x70",
                        "140": "https://placehold.it/140x140"
                    }
                }
            }
})

placeholder_statusDate = "1970-09-10T00:00:00Z"
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
        "Short Report": "short-report",
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

    # Short-circuit here because related articles has changed
    if related_article_list:
        related_articles.append(placeholder_related_article)
        return related_articles
    else:
        return None

    # Old code below to be enhanced
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

def generate_section_id():
    """section id attribute generator"""
    global section_id_counter
    try:
        section_id_counter = section_id_counter + 1
    except NameError:
        section_id_counter = 1
    return "phantom-s-" + str(section_id_counter)

def wrap_body_rewrite(body):
    """JSON schema requires body to be wrapped in a section even if not present"""

    if "type" in body[0] and body[0]["type"] != "section":
        # Wrap this one
        new_body_section = OrderedDict()
        new_body_section["type"] = "section"
        new_body_section["id"] = generate_section_id()
        new_body_section["title"] = ""
        new_body_section["content"] = []
        for body_block in body:
            new_body_section["content"].append(body_block)
        new_body = []
        new_body.append(new_body_section)
        body = new_body

    # Continue with rewriting
    return body_rewrite(body)

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

def fix_box_title_if_missing(body_json):
    for element in body_json:
        if "type" in element and element["type"] == "box":
            if "title" not in element:
                element["title"] = placeholder_box_title_if_missing
        for content_index in ["content"]:
            if content_index in element:
                try:
                    fix_box_title_if_missing(element[content_index])
                except TypeError:
                    # not iterable
                    pass

    return body_json

def fix_paragraph_with_content(body_json):
    """
    Hopefully a temporary fix, the parser is currently not handling
    content inside a paragraph when the paragraph is just a wrapper
    at the start of a body in an Insight article
    This should take the content of a paragraph and add it to its parent
    so the JSON has a chance to pass validation
    """
    for element in body_json:
        if "type" in element and "content" in element:
            for i, content_child in enumerate(element["content"]):
                if ("type" in content_child
                    and content_child["type"] == "paragraph"
                    and "content" in content_child):
                    for p_content in content_child["content"]:
                        # Set its parent content to this content
                        element["content"][i] = p_content

    return body_json

def fix_section_id_if_missing(body_json):
    for element in body_json:
        if "type" in element and element["type"] == "section":
            if "id" not in element:
                element["id"] = generate_section_id()
        for content_index in ["content"]:
            if content_index in element:
                try:
                    fix_section_id_if_missing(element[content_index])
                except TypeError:
                    # not iterable
                    pass

    return body_json

def video_rewrite(body_json):
    for element in body_json:
        if "type" in element and element["type"] == "video":
            if "uri" in element:
                element["sources"] = []
                source_media = OrderedDict()
                source_media["mediaType"] = "video/mp4; codecs=\"avc1.42E01E, mp4a.40.2\""
                source_media["uri"] = "https://example.org/" + element.get("uri")
                element["sources"].append(source_media)

                element["image"] = "https://example.org/" + element.get("uri")
                element["width"] = 640
                element["height"] = 480

                del element["uri"]

        for content_index in ["content"]:
            if content_index in element:
                try:
                    video_rewrite(element[content_index])
                except TypeError:
                    # not iterable
                    pass

    return body_json

def body_rewrite(body):
    body = image_uri_rewrite(body)
    body = mathml_rewrite(body)
    body = fix_section_id_if_missing(body)
    body = fix_paragraph_with_content(body)
    body = fix_box_title_if_missing(body)
    body = video_rewrite(body)
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

def clean_copyright(article_json):
    # Clean copyright in article or snippet
    remove_from_copyright_if_none = ["holder"]
    for remove_index in remove_from_copyright_if_none:
        if article_json.get("copyright", {}).has_key(remove_index):
            if article_json["copyright"][remove_index] is None:
                del article_json["copyright"][remove_index]
    return article_json

def clean(article_data):
    # Remove null or blank elements

    article_json = article_data # we're dealing with json just yet ...
    remove_if_none = ["pdf", "relatedArticles", "digest", "abstract"]
    for remove_index in remove_if_none:
        if (remove_index in article_json["article"]
            and article_json["article"][remove_index] is None):
            del article_json["article"][remove_index]

    remove_if_empty = ["impactStatement", "decisionLetter", "authorResponse",
                       "researchOrganisms", "keywords"]
    for remove_index in remove_if_empty:
        if (article_json["article"].get(remove_index) is not None
            and (
                article_json["article"].get(remove_index) == ""
                or article_json["article"].get(remove_index) == []
                or article_json["article"].get(remove_index) == {})):
            del article_json["article"][remove_index]

    article_json["article"] = clean_copyright(article_json["article"])
    article_json["snippet"] = clean_copyright(article_json["snippet"])

    # If abstract has no DOI, turn it into an impact statement
    if "abstract" in article_json["article"] and "impactStatement" not in article_json["article"]:
        if "doi" not in article_json["article"]["abstract"]:
            # Take the first paragraph text
            abstract_text = article_json["article"]["abstract"]["content"][0]["text"]
            article_json["article"]["impactStatement"] = abstract_text
            del article_json["article"]["abstract"]

    return article_json

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
    ('status', [jats('is_poa'), is_poa_to_status]), # shared by both POA and VOR snippets but not obvious in schema
    ('id', [jats('publisher_id')]),
    ('version', [placeholder_version, todo('version')]),
    ('type', [jats('display_channel'), display_channel_to_article_type]),
    ('doi', [jats('doi')]),
    ('authorLine', [jats('author_line')]),
    ('title', [jats('title')]),
    ('published', [jats('pub_date'), to_isoformat]),
    ('statusDate', [placeholder_statusDate, todo('placeholder_statusDate')]),
    ('volume', [jats('volume'), to_volume]),
    ('elocationId', [jats('elocation_id')]),
    ('pdf', [jats('self_uri'), self_uri_to_pdf]),
    ('subjects', [jats('category'), category_codes]),
    ('research-organisms', [jats('research_organism')]),
    ('abstract', [jats('abstract_json')]),
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
    ('authors', [jats('authors_json'), authors_rewrite])
]))

VOR_SNIPPET = copy.deepcopy(POA)
VOR_SNIPPET.update(OrderedDict([
    ('impactStatement', [jats('impact_statement')]),
]))

VOR = copy.deepcopy(VOR_SNIPPET)
VOR.update(OrderedDict([
    ('keywords', [jats('keywords')]),
    ('relatedArticles', [jats('related_article'), related_article_to_related_articles]),
    ('digest', [jats('digest_json')]),
    ('body', [jats('body'), wrap_body_rewrite]), # ha! so easy ...
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
        print json.dumps(render_single(doc), indent=4)
    except Exception:
        LOG.exception("failed to scrape article", extra={'doc': doc})
        raise

if __name__ == '__main__':  # pragma: no cover
    args = sys.argv[1:]
    if len(args) == 0:
        print "path to an article xml file required"
        exit(1)
    main(sys.argv[1]) # pragma: no cover
