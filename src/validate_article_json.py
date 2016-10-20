"""validates ALL article-json in the article-json directory, creating symlinks to the 
valid/invalid files.

this should be run using the ./validate-json.sh script in the project's root. it preps 
and cleans the environment."""

import os
from os.path import join
import validate
import sys
from StringIO import StringIO
from joblib import Parallel, delayed
from conf import JSON_DIR, VALID_JSON_DIR, INVALID_JSON_DIR
import jsonschema

def job(path):
    strbuffer = StringIO()
    try:
        fname = os.path.basename(path)
        strbuffer.write("%s => " % fname)
        validate.main(open(path, 'r'))
        strbuffer.write("success")
        os.symlink(path, join(VALID_JSON_DIR, fname))
    except jsonschema.ValidationError:
        strbuffer.write("failed")
        os.symlink(path, join(INVALID_JSON_DIR, fname))
    except Exception:
        strbuffer.write("error")
    finally:
        sys.stderr.write(strbuffer.getvalue() + "\n")
        sys.stderr.flush()

def main():
    paths = map(lambda fname: join(JSON_DIR, fname), os.listdir(JSON_DIR))
    paths = filter(lambda path: path.lower().endswith('.json'), paths)
    paths = sorted(paths, reverse=True)
    Parallel(n_jobs=-1)(delayed(job)(path) for path in paths)
    print 'see validate.log for errors'

if __name__ == '__main__':
    main()
