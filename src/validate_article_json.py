"""validates ALL article-json in the given directory, creating symlinks to valid/invalid files.

this should be run using the ./validate-json.sh script in the project's root.
it preps and cleans the environment."""
import time
import os
from os.path import join
from io import StringIO
import sys
from joblib import Parallel, delayed
import conf, validate
from utils import first, second, lfilter, lmap

VALIDDIR, INVALIDDIR = 'valid', 'invalid'

import logging

LOG = logging.getLogger('')
LOG.setLevel(logging.ERROR)

def job(path):
    strbuffer = StringIO()

    try:
        fname = os.path.basename(path)
        dirname = os.path.dirname(path)

        #strbuffer.write("%s => " % fname)
        doc = open(path, 'r')
        start = time.time()
        valid, article_with_placeholders = validate.main(doc, quiet=True)
        stop = time.time()
        elapsed = int((stop - start) * 1000)
        
        if valid:
            #strbuffer.write("success")
            strbuffer.write("valid in %4sms: %s" % (elapsed, fname))
            #os.symlink(path, join(dirname, VALIDDIR, fname))
        else:
            strbuffer.write("failed")
            #os.symlink(path, join(dirname, INVALIDDIR, fname))

        return elapsed
            
    except KeyboardInterrupt:
        print("ctrl-c caught")
        exit(1)
            
    except BaseException as err:
        strbuffer.write("error (%s)" % err)

    finally:
        #log = conf.multiprocess_log('validation.log', __name__)
        #log.info(strbuffer.getvalue())
        print(strbuffer.getvalue())
        

def main(args=None):
    target = first(args) or conf.JSON_DIR
    sample_size = second(args) or 1000

    if os.path.isdir(target):
        paths = lmap(lambda fname: join(target, fname), os.listdir(target))
        paths = lfilter(lambda path: path.lower().endswith('.json'), paths)
        
        def keyfn(fname):
            # elife-00003-v1.xml.json => 3
            return int(os.path.basename(fname).split('-')[1])
        
        paths = sorted(paths, key=keyfn)[:sample_size]
    else:
        paths = [os.path.abspath(target)]
    
    print('jobs %d' % len(paths))
    #Parallel(n_jobs=-1)(delayed(job)(path) for path in paths)
    ms_list = [job(path) for path in paths]
    total_ms = sum(ms_list)
    avg_ms = total_ms / len(ms_list)

    print("total: %sms  average: %sms" % (total_ms, avg_ms))
    
    #print('see validate.log for errors')

if __name__ == '__main__':
    main(sys.argv[1:])
