"""validates ALL article-json in the given directory, creating symlinks to valid/invalid files.

this should be run using the ./validate-json.sh script in the project's root.
it preps and cleans the environment."""

import os, sys
from utils import first
from os.path import join
import validate
from StringIO import StringIO
from joblib import Parallel, delayed
import conf
from conf import JSON_DIR

VALIDDIR, INVALIDDIR = 'valid', 'invalid'

def job(path):
    strbuffer = StringIO()

    try:
        fname = os.path.basename(path)
        dirname = os.path.dirname(path)

        strbuffer.write("%s => " % fname)
        doc = open(path, 'r')
        valid, article_with_placeholders = validate.main(doc, quiet=True)

        if valid:
            strbuffer.write("success")
            os.symlink(path, join(dirname, VALIDDIR, fname))
        else:
            strbuffer.write("failed")
            os.symlink(path, join(dirname, INVALIDDIR, fname))

    except BaseException as err:
        strbuffer.write("error (%s)" % err)

    finally:
        log = conf.multiprocess_log('validation.log', __name__)
        log.info(strbuffer.getvalue())

def main(args=None):
    target = first(args) or JSON_DIR

    if os.path.isdir(target):
        paths = map(lambda fname: join(target, fname), os.listdir(target))
        paths = sorted(paths, reverse=True)
    else:
        paths = [os.path.abspath(target)]

    paths = filter(lambda path: path.lower().endswith('.json'), paths)
    print 'jobs %d' % len(paths)
    Parallel(n_jobs=-1)(delayed(job)(path) for path in paths)
    print 'see validate.log for errors'

if __name__ == '__main__':
    main(sys.argv[1:])
