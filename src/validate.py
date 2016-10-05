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

def is_poa(contents):
    try:
        return contents["article"]["status"] == "poa"
    except KeyError:
        return False
    
def add_placeholders_for_validation(contents):
    contents['snippet']['version'] = placeholder_version
    contents['article']['version'] = placeholder_version

    contents['snippet']['authorLine'] = placeholder_authorLine
    contents['article']['authorLine'] = placeholder_authorLine

    contents['snippet']['abstract'] = placeholder_abstract
    contents['article']['abstract'] = placeholder_abstract

    contents['article']['authors'] = placeholder_authors

    if not is_poa(contents):
        contents['article']['digest'] = placeholder_digest

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
    ver, _ = tail.split('.',1)

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

if __name__ == '__main__':
    main()
