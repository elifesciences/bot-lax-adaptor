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

placeholder_statusDate = "1970-09-10T00:00:00Z"

placeholder_related_article = {
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
}

placeholder_references = [{
    "type": "journal", 
    "id": "bib1", 
    "date": "2008", 
    "authors": [
        {
            "type": "person", 
            "name": {
                "preferred": "Person One", 
                "index": "One, Person"
            }
        }
    ], 
    "articleTitle": "Auxin influx carriers stabilize phyllotactic patterning", 
    "journal": {
        "name": [
            "Genes & Development"
        ]
    }, 
    "volume": "22", 
    "pages": {
        "first": "810", 
        "last": "823", 
        "range": u"810\u2013823"
    }, 
    "doi": "10.1101/gad.462608"
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

    contents['snippet']['statusDate'] = placeholder_statusDate
    contents['article']['statusDate'] = placeholder_statusDate

    if 'relatedArticles' in contents['article']:
        for i, value in enumerate(contents['article']['relatedArticles']):
            contents['article']['relatedArticles'][i] = placeholder_related_article

    if 'references' in contents['article']:
        contents['article']['references'] = placeholder_references

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

if __name__ == '__main__':
    main()
