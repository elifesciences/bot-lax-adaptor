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

# output to screen
_handler2 = logging.StreamHandler()
_handler2.setLevel(logging.INFO)
_handler2.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
LOG.addHandler(_handler2)

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

def is_poa(contents):
    try:
        return contents["article"]["status"] == "poa"
    except KeyError:
        return False

def add_placeholders_for_validation(contents):
    art = contents['article']

    #art['authors'] = placeholder_authors
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
        del art['references']

    if not is_poa(contents):
        pass

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', type=argparse.FileType('r'), default=sys.stdin)
    args = parser.parse_args()

    contents = json.load(args.infile)
    add_placeholders_for_validation(contents)

    schema = conf.POA_SCHEMA if is_poa(contents) else conf.VOR_SCHEMA

    filename = os.path.basename(args.infile.name)
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
    except jsonschema.ValidationError as err:
        LOG.error("failed to validate %s: %s", msid, err.message, extra=log_context)
        exit(1)
    except KeyboardInterrupt:
        exit(1)

if __name__ == '__main__':
    main()
