"""
looks in the article-xml directory and converts all/some/random xml to article-json

"""
from __future__ import print_function
import os
from os.path import join

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from joblib import Parallel, delayed

import src.conf as conf
import src.main as scraper
from src.utils import ensure


def render(path, json_output_dir):
    try:
        strbuffer = StringIO()
        fname = os.path.basename(path)
        strbuffer.write("%s -> %s => " % (fname, fname + '.json'))
        json_result = scraper.main(path)

        # ll: backfill-run-1234567890/ajson/elife-09560-v1.xml.ajson
        outfname = join(json_output_dir, fname + '.json')

        open(outfname, 'w').write(json_result)
        strbuffer.write("success")
    except BaseException as err:
        strbuffer.write("failed (%s)" % err)
    finally:
        log = conf.multiprocess_log('generation.log', __name__)
        log.info(strbuffer.getvalue())

def main(xml_dir, json_output_dir):
    paths = list(map(lambda fname: join(xml_dir, fname), os.listdir(xml_dir)))
    paths = list(filter(lambda path: path.lower().endswith('.xml'), paths))
    paths = sorted(paths, reverse=True)
    num_processes = 2
    Parallel(n_jobs=num_processes)(delayed(render)(path, json_output_dir) for path in paths)
    print('see scrape.log for errors')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('xml-dir', nargs='?', default=conf.XML_DIR)
    parser.add_argument('output-dir', nargs='?', default=conf.JSON_DIR)

    args = vars(parser.parse_args())
    indir, outdir = [os.path.abspath(args[key]) for key in ['xml-dir', 'output-dir']]

    ensure(os.path.exists(indir), "the path %r doesn't exist" % indir)
    ensure(os.path.exists(outdir), "the path %r doesn't exist" % outdir)

    main(indir, outdir)
