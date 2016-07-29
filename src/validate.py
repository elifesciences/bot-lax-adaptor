import os, sys, json
from jsonschema import validate

def json_load(fname):
    path = os.path.abspath(fname)
    return json.load(open(path, 'r'))

def main(jsondoc):
    poa_schema = json_load('api-raml/dist/model/article-poa.v1.json')
    vor_schema = json_load('api-raml/dist/model/article-vor.v1.json')
    contents = json_load(jsondoc)

    print poa_schema

    print vor_schema

    print contents

if __name__ == '__main__':
    assert len(sys.argv) == 2, "the path to an article json file was expected"
    main(sys.argv[1])
