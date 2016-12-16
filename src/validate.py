import utils
import os, sys, json
import conf
import jsonschema
import logging
LOG = logging.getLogger(__name__)

# output to adaptor.log
_handler = logging.FileHandler("validate.log")
_handler.setLevel(logging.ERROR)
_handler.setFormatter(conf._formatter)
LOG.addHandler(_handler)


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


def funding_rewrite(funding):
    "clean up funding values that will not pass validation"
    if funding.get("awards"):
        placeholder_recipients = [{"type": "group", "name": "Placeholder award recipient"}]
        for award in funding.get("awards"):
            if not award.get("recipients"):
                award["recipients"] = placeholder_recipients
        # Need a funding statement
        if not funding.get("statement"):
            funding["statement"] = "Placeholder for funding statement."
    return funding


def is_poa(contents):
    try:
        return contents["article"]["status"] == "poa"
    except KeyError:
        return False

def add_placeholders_for_validation(contents):
    """these placeholder values are now making their way into production.
    please make them OBVIOUS placeholders while still remaining valid data."""

    art = contents['article']

    # simple indicator that this article content contains patched values
    art['-patched'] = True

    if 'published' in art:
        art['published'] = utils.ymdhms(art['published'])

    art['stage'] = 'published'
    art['statusDate'] = '2099-01-01T00:00:00Z'
    art['versionDate'] = '2099-01-01T00:00:00Z'

    # relatedArticles are not part of article deliverables
    if 'relatedArticles' in art:
        del art['relatedArticles']

    if 'funding' in art:
        art['funding'] = funding_rewrite(art['funding'])

    for elem in ['body', 'decisionLetter', 'authorResponse', 'appendices']:
        if elem in art:
            art[elem] = fix_section_id_if_missing(art[elem])
            art[elem] = fix_box_title_if_missing(art[elem])

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
