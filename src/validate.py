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


def main(doc, quiet=False):
    contents = json.load(doc)
    add_placeholders_for_validation(contents)

    schema = conf.POA_SCHEMA if is_poa(contents) else conf.VOR_SCHEMA

    filename = os.path.basename(doc.name)
    _, msid, tail = filename.split('-', 2)
    ver, _ = tail.split('.', 1)

    log_context = {
        'json-filename': filename,
        'msid': msid,
        'version': ver
    }
    try:
        jsonschema.validate(contents["article"], schema)
        LOG.info("validated %s", msid, extra=log_context)
        return True, contents
    except jsonschema.ValidationError as err:
        LOG.error("failed to validate %s: %s", msid, err.message, extra=log_context)
        if quiet:
            return False, contents
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
