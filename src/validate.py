import os, sys, json
import conf
import jsonschema

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
    parser.add_argument('--verbose', action="store_true", default=False)
    args = parser.parse_args()

    contents = json.load(args.infile)
    add_placeholders_for_validation(contents)

    schema = conf.POA_SCHEMA if is_poa(contents) else conf.VOR_SCHEMA
    try:
        jsonschema.validate(contents["article"], schema)
    except jsonschema.ValidationError as err:
        if args.verbose:
            print err
            print "\n\n[failed] %s\n\n" % err.message
        else:
            print err.message
        exit(1)

if __name__ == '__main__':
    main()
