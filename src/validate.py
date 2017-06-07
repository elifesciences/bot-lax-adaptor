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

def main(doc, quiet=False):
    contents = json.load(doc)
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
