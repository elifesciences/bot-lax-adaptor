import os, sys, json, re
import conf
import jsonschema

import logging
LOG = logging.getLogger(__name__)

# output to adaptor.log
_handler = logging.FileHandler("validate.log")
_handler.setLevel(logging.ERROR)
_handler.setFormatter(conf._formatter)
LOG.addHandler(_handler)

# output to screen
_handler2 = logging.StreamHandler()
_handler2.setLevel(logging.INFO)
_handler2.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
LOG.addHandler(_handler2)

placeholder_reference_authors = [
    {
        "type": "person",
        "name": {
            "preferred": "Person One",
            "index": "One, Person"
        }
    }
]

def uri_rewrite(body_json):
    base_uri = "https://example.org/"
    # Check if it is not a list, in the case of authorResponse
    if "content" in body_json:
        uri_rewrite(body_json["content"])
    # A list, like in body, continue
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
                    uri_rewrite(element[content_index])
                except TypeError:
                    # not iterable
                    pass
    return body_json

def video_rewrite(body_json):
    for element in body_json:
        if "type" in element and element["type"] == "video":
            if "uri" in element:
                element["sources"] = []
                source_media = {}
                source_media["mediaType"] = "video/mp4; codecs=\"avc1.42E01E, mp4a.40.2\""
                source_media["uri"] = "https://example.org/" + element.get("uri")
                source_media["filename"] = os.path.basename(element.get("uri"))

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

def mathml_rewrite(body_json):
    # Check if it is not a list, in the case of authorResponse
    if "content" in body_json:
        mathml_rewrite(body_json["content"])
    # A list, like in body, continue
    for element in body_json:
        if "type" in element and element["type"] == "mathml":
            if "mathml" in element:
                # Quick edits to get mathml to comply with the json schema
                mathml = "<math>" + element["mathml"] + "</math>"
                mathml = mathml.replace("<mml:", "<").replace("</mml:", "</")
                element["mathml"] = mathml

        for content_index in ["content", "caption", "supplements"]:
            if content_index in element:
                try:
                    mathml_rewrite(element[content_index])
                except TypeError:
                    # not iterable
                    pass

        if "items" in element:
            # list block items is a list of lists
            for list_item in element["items"]:
                mathml_rewrite(list_item)

    return body_json

def generate_section_id():
    """section id attribute generator"""
    global section_id_counter
    try:
        section_id_counter = section_id_counter + 1
    except (NameError, TypeError):
        section_id_counter = 1
    return "phantom-s-" + str(section_id_counter)

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

def fix_box_title_if_missing(body_json):
    placeholder_box_title_if_missing = "Placeholder box title because we must have one"
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

def wrap_body_in_section(body_json):
    """JSON schema requires body to be wrapped in a section even if not present"""

    if (body_json and len(body_json) > 0 and "type" in body_json[0]
            and body_json[0]["type"] != "section"):
        # Wrap this one
        new_body_section = {}
        new_body_section["type"] = "section"
        new_body_section["id"] = generate_section_id()
        new_body_section["title"] = ""
        new_body_section["content"] = []
        for body_block in body_json:
            new_body_section["content"].append(body_block)
        new_body = []
        new_body.append(new_body_section)
        body_json = new_body

    # Continue with rewriting
    return body_json


def references_rewrite(references):
    "clean up values that will not pass validation temporarily"
    for ref in references:
        if "date" in ref:
            # Scrub non-numeric values from the date, which comes from the reference year
            ref["date"] = re.sub("[^0-9]", "", ref["date"])
        elif "date" not in ref:
            ref["date"] = "1000"
        if (ref.get("type") in ["book", "book-chapter", "conference-proceeding", "data",
                                "journal", "software", "unknown", "web"]
                and "authors" not in ref):
            ref["authors"] = placeholder_reference_authors

    return references


def is_poa(contents):
    try:
        return contents["article"]["status"] == "poa"
    except KeyError:
        return False

def add_placeholders_for_validation(contents):
    art = contents['article']

    art['statusDate'] = '2016-01-01T00:00:00Z'

    # the versionDate is discarded when the article is not v1
    if art['version'] > 1:
        # add a placeholder for validation
        art['versionDate'] = '2016-01-01T00:00:00Z'

    # relatedArticles are not part of article deliverables
    if 'relatedArticles' in art:
        del art['relatedArticles']

    # what references we do have are invalid
    if 'references' in art:
        art['references'] = references_rewrite(art['references'])

    for elem in ['body', 'decisionLetter', 'authorResponse']:
        if elem in art:
            art[elem] = uri_rewrite(art[elem])
            art[elem] = video_rewrite(art[elem])
            art[elem] = fix_section_id_if_missing(art[elem])
            art[elem] = mathml_rewrite(art[elem])
            art[elem] = fix_box_title_if_missing(art[elem])

    for elem in ['body']:
        if elem in art:
            art[elem] = wrap_body_in_section(art[elem])

    if not is_poa(contents):
        pass

def main(doc):
    contents = json.load(doc)
    add_placeholders_for_validation(contents)

    schema = conf.POA_SCHEMA if is_poa(contents) else conf.VOR_SCHEMA

    filename = os.path.basename(doc.name)
    _, msid, tail = filename.split('-')
    ver, _ = tail.split('.', 1)

    log_context = {
        'json-filename': filename,
        'msid': msid,
        'version': ver
    }
    try:
        jsonschema.validate(contents["article"], schema)
        LOG.info("validated %s", msid, extra=log_context)
        # return the contents, complete with placeholders
        return contents
    except jsonschema.ValidationError as err:
        LOG.error("failed to validate %s: %s", msid, err.message, extra=log_context)
        raise

if __name__ == '__main__':
    try:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('infile', type=argparse.FileType('r'), default=sys.stdin)
        args = parser.parse_args()
        print json.dumps(main(args.infile))
    except jsonschema.ValidationError:
        exit(1)
    except KeyboardInterrupt:
        exit(1)
