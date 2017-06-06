"""
article-json derived from elife xml article cannot be valid by itself
and requires some minimal post-processing to pass json schema
validation and making it into lax for further wrangling.

"""

import os, sys, json
import conf, utils
import jsonschema
import logging
LOG = logging.getLogger(__name__)

# output to adaptor.log
_handler = logging.FileHandler("validate.log")
_handler.setLevel(logging.ERROR)
_handler.setFormatter(conf._formatter)
LOG.addHandler(_handler)

def is_poa(contents):
    try:
        return contents["article"]["status"] == "poa"
    except KeyError:
        return False

def add_placeholders_for_validation(contents):
    """mutator! this function modifies it's content.
    please make any placeholders OBVIOUS while still remaining valid data."""

    art = contents['article']

    if not '-meta' in art:
        # probably a bad scrape or an old fixture or ...
        art['-meta'] = {}

    # simple indicator that this article content contains patched values
    art['-meta']['patched'] = True

    # an article will always have a pubdate, so we don't know if it's actually published or not...
    art['stage'] = 'published'

    # the statusDate is when an article transitioned from POA to VOR and can't be known
    # in all cases without consulting the article history
    art['statusDate'] = '2099-01-01T00:00:00Z'

    if 'versionDate' not in art:
        # a versionDate is when this specific version of an article was published
        # a versionDate wouldn't be present if we're dealing with a version > 1
        art['versionDate'] = '2099-01-01T00:00:00Z'

#
#
#

def main(doc, quiet=False):
    contents = json.load(doc)
    add_placeholders_for_validation(contents)

    schema = conf.POA_SCHEMA if is_poa(contents) else conf.VOR_SCHEMA

    filename = os.path.basename(doc.name)
    msid, ver = utils.version_from_path(filename)
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
        LOG.error("failed to validate %s: %s", msid, err, extra=log_context)
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
