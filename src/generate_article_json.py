"""
looks in the article-xml directory and converts all/some/random xml to article-json

"""
import os
from os.path import join
import main as scraper
import sys
from StringIO import StringIO
from joblib import Parallel, delayed

SRC_DIR = os.path.dirname(os.path.abspath(__file__)) # ./bot-lax-adaptor/src/
PROJECT_DIR = os.path.dirname(SRC_DIR)
XML_DIR = join(PROJECT_DIR, 'article-xml', 'articles')
JSON_DIR = join(PROJECT_DIR, 'article-json2')

def render(path):
    strbuffer = StringIO()
    try:
        fname = os.path.basename(path)
        strbuffer.write("%s -> %s => " % (fname, fname + '.json'))
        json_result = scraper.main(path)
        outfname = join(JSON_DIR, fname + '.json')
        open(outfname, 'w').write(json_result)
        strbuffer.write("success")
    except Exception:
        strbuffer.write("failed")
    finally:
        sys.stderr.write(strbuffer.getvalue() + "\n")
        sys.stderr.flush()

def main():
    paths = map(lambda fname: join(XML_DIR, fname), os.listdir(XML_DIR))
    paths = filter(lambda path: path.lower().endswith('.xml'), paths)
    paths = sorted(paths, reverse=True)
    #paths_sizes = zip(paths, map(os.path.getsize, paths))
    #map(render, paths)
    Parallel(n_jobs=-1)(delayed(render)(path) for path in paths[:10])
    print 'see scrape.log for errors'

if __name__ == '__main__':
    '''
    import argparse
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    '''
    main()
