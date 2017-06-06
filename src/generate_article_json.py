"""
looks in the article-xml directory and converts all/some/random xml to article-json

"""
import os
from os.path import join
import main as scraper
from StringIO import StringIO
from joblib import Parallel, delayed
import conf
from utils import ensure

def render(path):
    try:
        strbuffer = StringIO()
        fname = os.path.basename(path)
        strbuffer.write("%s -> %s => " % (fname, fname + '.json'))
        json_result = scraper.main(path)

        json_output_dir = join(os.path.dirname(path), 'ajson') # ll: backfill-run-1234567890/ajson/
        outfname = join(json_output_dir, fname + '.json') # ll: backfill-run-1234567890/ajson/elife-09560-v1.xml.ajson
        open(outfname, 'w').write(json_result)
        strbuffer.write("success")
    except BaseException as err:
        strbuffer.write("failed (%s)" % err)
    finally:
        log = conf.multiprocess_log('generation.log', __name__)
        log.info(strbuffer.getvalue())

def main(xml_dir):
    paths = map(lambda fname: join(xml_dir, fname), os.listdir(xml_dir))
    paths = filter(lambda path: path.lower().endswith('.xml'), paths)
    paths = sorted(paths, reverse=True)
    #paths_sizes = zip(paths, map(os.path.getsize, paths))
    #map(render, paths)
    Parallel(n_jobs=-1)(delayed(render)(path) for path in paths)
    print 'see scrape.log for errors'

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('xml-dir', default=conf.XML_DIR)
    args = vars(parser.parse_args())
    args['xml-dir'] = os.path.abspath(args['xml-dir'])
    ensure(os.path.exists(args['xml-dir']), "the path %r doesn't exist" % args['xml-dir'])
    main(args['xml-dir'])
    exit(0)
