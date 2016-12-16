"""validates ALL article-json in the article-json directory, creating symlinks to the
valid/invalid files.

this should be run using the ./validate-json.sh script in the project's root. it preps
and cleans the environment."""

import os, platform, shutil
from utils import first
from os.path import join
import validate
import sys, json
from StringIO import StringIO
from joblib import Parallel, delayed
import conf
from conf import JSON_DIR, VALID_JSON_DIR, INVALID_JSON_DIR, VALID_PATCHED_JSON_DIR
import jsonschema

WINDOWS = platform.system().lower() == 'windows'

def job(path):
    strbuffer = StringIO()

    def copyfn(src, dest):
        if os.path.exists(dest):
            os.unlink(dest)
        return shutil.copyfile(src, dest)

    fn = copyfn
    if not WINDOWS:
        fn = os.symlink

    try:
        fname = os.path.basename(path)
        strbuffer.write("%s => " % fname)
        article_with_placeholders = validate.main(open(path, 'r'))
        strbuffer.write("success")
        fn(path, join(VALID_JSON_DIR, fname))
        json.dump(article_with_placeholders, open(join(VALID_PATCHED_JSON_DIR, fname), 'w'), indent=4)
    except jsonschema.ValidationError:
        strbuffer.write("failed")
        fn(path, join(INVALID_JSON_DIR, fname))
    except BaseException as err:
        strbuffer.write("error (%s)" % err)
    finally:
        log = conf.multiprocess_log('validation.log', __name__)
        log.info(strbuffer.getvalue())

def main(args=None):
    target = first(args)
    if not target:
        target = JSON_DIR

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
