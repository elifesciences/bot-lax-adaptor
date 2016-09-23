import os, sys, json
import conf
import jsonschema

def is_poa(contents):
    try:
        return contents["article"]["status"] == "poa"
    except KeyError:
        return False

def main(article_path):
    contents = json.load(open(os.path.abspath(article_path), 'r'))
    schema = conf.POA_SCHEMA if is_poa(contents) else conf.VOR_SCHEMA
    try:
        jsonschema.validate(contents["article"], schema)
    except jsonschema.ValidationError as err:
        print err.message
        exit(1)

if __name__ == '__main__':
    assert len(sys.argv) == 2, "the path to an article json file was expected"
    main(sys.argv[1])
