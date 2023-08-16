"""An interface to generating multiple article-json files.
By default it converts *all* xml in `./article-xml/articles` to article-json,
writing the results to the `./article-json/` directory.

The number of article-xml files to process can be capped with `--num n`."""

import argparse
import json
import os
from os.path import join
from io import StringIO
from joblib import Parallel, delayed
import conf, main as scraper
from utils import ensure, lfilter, lmap
import logging

LOG = logging.getLogger(__name__)

def render(path, json_output_dir):
    try:
        strbuffer = StringIO()
        fname = os.path.basename(path)
        strbuffer.write("%s -> %s => " % (fname, fname + '.json'))
        json_result = scraper.main(path)

        # "backfill-run-1234567890/ajson/elife-09560-v1.xml.ajson"
        outfname = join(json_output_dir, fname + '.json')

        open(outfname, 'w').write(json_result)
        strbuffer.write("success")
    except BaseException as err:
        strbuffer.write("failed (%s)" % err)
    finally:
        log = conf.multiprocess_log('generation.log', __name__)
        log.info(strbuffer.getvalue())

def pformat(d):
    return json.dumps(d, indent=4, default=str)

def main(xml_dir, json_output_dir, num=None):
    paths = lmap(lambda fname: join(xml_dir, fname), os.listdir(xml_dir))
    paths = lfilter(lambda path: path.lower().endswith('.xml'), paths)
    paths = sorted(paths, reverse=True)
    if num is not None and num > -1:
        paths = paths[:num] # only scrape first n articles
    num_processes = -1
    Parallel(n_jobs=num_processes)(delayed(render)(path, json_output_dir) for path in paths)
    print('see scrape.log for errors')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('xml-dir', nargs='?', default=conf.XML_DIR)
    parser.add_argument('output-dir', nargs='?', default=conf.JSON_DIR)
    parser.add_argument('--num', type=int, nargs='?')

    args = vars(parser.parse_args())
    indir, outdir = [os.path.abspath(args[key]) for key in ['xml-dir', 'output-dir']]

    ensure(os.path.exists(indir), "the path %r doesn't exist" % indir)
    ensure(os.path.exists(outdir), "the path %r doesn't exist" % outdir)

    blacklist = ['DYNCONFIG', 'POA_SCHEMA', 'VOR_SCHEMA', 'REQUEST_SCHEMA', 'RESPONSE_SCHEMA', 'API_SCHEMA']
    config = {k: v for k, v in conf.__dict__.items() if k.isupper() and k not in blacklist}
    config = dict(sorted(config.items(), key=lambda x: x[0]))

    LOG.info("configuration: %s", pformat(config))
    LOG.info("command line arguments: %s", pformat(args))

    main(indir, outdir, args['num'])
