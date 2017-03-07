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

def do_paths(paths):
    to_be_reingested = filter(None, map(mkreq, paths))
    return send_ingest_requests_to_lax(to_be_reingested)

#
# bootstrap
#

def main(args):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs="*")
    args = parser.parse_args(args)

    # read any filenames that were passed in as arguments
    paths = args.paths

    # failing that, try reading from stdin
    if not paths:
        paths = sys.stdin.readlines()
        try:
            paths = map(json.loads, paths)
        except ValueError:
            raise

    print paths

    return do_paths(paths)

if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)
