"""
adhoc_backfill.py provides support for backfilling small numbers of arbitrary articles.

it accepts a list of paths to xml files from the command line:
  ./adhoc_backfill.py /path/to/file1.xml /path/to/file2.xml

or it accepts a list of json dictionaries (one per line) whose values will override the
default values in making a request via adaptor.py. these values can be seen in `fs_adaptor.mkreq`

"""

import sys
import adaptor, fs_adaptor
import json
from conf import logging

LOG = logging.getLogger(__name__)

def send_ingest_requests_to_lax(request_list):
    "for each article we want to send a request "
    incoming = fs_adaptor.SimpleQueue(path_list=request_list)
    outgoing = fs_adaptor.OutgoingQueue()
    adaptor.do(incoming, outgoing)
    # ... ?
    LOG.info("done - %s requests consumed" % len(request_list))
    return outgoing.dump()

def mkreq(path):
    try:
        handlers = {
            str: fs_adaptor.mkreq,
            dict: lambda lax_result: fs_adaptor.mkreq(lax_result['location']),
        }
        return handlers[type(path)](path)
    except ValueError:
        LOG.warning("skipping path %r as I can't extract a location from it", path)
    except KeyError:
        LOG.warning("unhandled input type, %r" % type(path))

def do_paths(paths, dry_run=False):
    ingest_requests = filter(None, map(mkreq, paths))
    if dry_run:
        return ingest_requests
    return send_ingest_requests_to_lax(ingest_requests)

#
# bootstrap
#

read_from_stdin = sys.stdin.readlines

def main(args):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('paths', nargs="*")
    args = parser.parse_args(args)

    # read any filenames that were passed in as arguments
    paths = args.paths

    # failing that, try reading from stdin
    if not paths:
        paths = read_from_stdin()
        try:
            paths = map(json.loads, paths)
        except ValueError:
            # assume filenames.
            pass

    return do_paths(paths, dry_run=args.dry_run)

if __name__ == '__main__':
    print(json.dumps(main(sys.argv[1:]), indent=4))
