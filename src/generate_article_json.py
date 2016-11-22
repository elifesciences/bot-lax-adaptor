"""
looks in the article-xml directory and converts all/some/random xml to article-json

"""
import os
from os.path import join
import main as scraper
from StringIO import StringIO
from joblib import Parallel, delayed
import conf
import logging
LOG = logging.getLogger(__name__)

def render(path):
    strbuffer = StringIO()
    try:
        LOG.info("Started generation from %s" % fname)
        fname = os.path.basename(path)
        strbuffer.write("%s -> %s => " % (fname, fname + '.json'))
        json_result = scraper.main(path)
        outfname = join(conf.JSON_DIR, fname + '.json')
        open(outfname, 'w').write(json_result)
        strbuffer.write("success")
    except BaseException as err:
        strbuffer.write("failed (%s)" % err)
    finally:
        LOG.info(strbuffer.getvalue())

def main():
    paths = map(lambda fname: join(conf.XML_DIR, fname), os.listdir(conf.XML_DIR))
    paths = filter(lambda path: path.lower().endswith('.xml'), paths)
    paths = sorted(paths, reverse=True)
    #paths_sizes = zip(paths, map(os.path.getsize, paths))
    #map(render, paths)
    Parallel(n_jobs=-1)(delayed(render)(path) for path in paths)
    print 'see scrape.log for errors'

if __name__ == '__main__':
    '''
    import argparse
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    '''
    main()
