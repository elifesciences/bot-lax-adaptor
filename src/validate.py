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

def is_poa(contents):
    try:
        return contents["article"]["status"] == "poa"
    except KeyError:
        return False

def add_placeholders_for_validation(contents):
    """these placeholder values are now making their way into production.
    please make them OBVIOUS placeholders while still remaining valid data."""
    art = contents['article']

    if not '-meta' in art:
        # probably a bad scrape or an old fixture or ...
        art['-meta'] = {}

    # simple indicator that this article content contains patched values
    art['-meta']['patched'] = True

    # this is weird. disabling, `toisoformat` already calls ymdhms on `published`
    # if 'published' in art:
    #    art['published'] = utils.ymdhms(art['published'])

    # an article will always have a pubdate, so we don't know if it's actually published or not...
    art['stage'] = 'published'

    art['statusDate'] = '2099-01-01T00:00:00Z'

    if 'versionDate' not in art:
        # a versionDate wouldn't be present if we're dealing with a version > 1
        art['versionDate'] = '2099-01-01T00:00:00Z'

#
#
#

def main(doc, quiet=False):
    contents = json.load(doc)

    # this will just overwrite previous values if originally scraped with placeholders
    # we can't guarantee the state of the original scrape though.
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
        #return True, contents
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
