from jsonschema import ValidationError
import json
from datetime import datetime
import os
from os.path import join
import requests
import signal
import main, fs_adaptor, sqs_adaptor
from functools import partial
import validate, utils
from utils import subdict, renkeys

from awsauth import S3Auth
import botocore.session

import conf
from conf import PATHS_TO_LAX, PROJECT_DIR
from conf import INVALID, ERROR, INGESTED, PUBLISHED, INGEST, PUBLISH, INGEST_PUBLISH

import logging
LOG = logging.getLogger(__name__)

# output to adaptor.log
_handler = logging.FileHandler("adaptor.log")
_handler.setLevel(logging.DEBUG)
_handler.setFormatter(conf._formatter)
LOG.addHandler(_handler)


from time import time
from functools import wraps

# http://stackoverflow.com/questions/1622943/timeit-versus-timing-decorator
def timeit(fn):
    @wraps(fn)
    def wrap(*args, **kw):
        ts = time()
        result = fn(*args, **kw)
        te = time()
        context = {'start': ts, 'end': te, 'total': "%2.4f" % (te - ts)}
        LOG.info('func:%r args:[%r, %r] took: %2.4f sec',
                 fn.__name__, args, kw, te - ts, extra=context)
        return result
    return wrap

#
#
#

def send_response(outgoing, response):
    # `response` here is the result of `mkresponse` below
    try:
        utils.validate_response(response)
        channel = outgoing.write
    except ValidationError as err:
        # response doesn't validate. this probably means
        # we had an error decoding request and have no id or token
        # because the message will not validate, we will not be sending it back
        response['validation-error-msg'] = err.message
        channel = outgoing.error
    channel(utils.json_dumps(response))
    return response

def find_lax():
    dirname = filter(os.path.exists, PATHS_TO_LAX)
    assert dirname, "could not find lax"
    script = join(dirname[0], "manage.sh")
    assert os.path.exists(script), "could not find lax's manage.sh script"
    return script

def call_lax(action, id, version, token, article_json=None, force=False, dry_run=False):
    cmd = [
        find_lax(),
        "ingest",
        "--" + action, # ll: --ingest+publish
        "--id", str(id),
        "--version", str(version),
    ]
    if dry_run:
        cmd += ["--dry-run"]
    if force:
        cmd += ["--force"]
    lax_stdout = None
    try:
        rc, lax_stdout = utils.run_script(cmd, article_json)
        results = json.loads(lax_stdout)
        return {
            "id": id,
            "requested-action": action,
            "token": token,
            "status": results['status'],
            "message": results['message'],
            "datetime": results.get('datetime', datetime.now())
        }
    except ValueError as err:
        # could not parse lax response. this is a lax error
        raise RuntimeError("failed to parse response from lax, expecting json, got error %r from stdout %r" %
                           (err.message, lax_stdout))

def file_handler(path):
    assert path.startswith(PROJECT_DIR), \
        "unsafe operation - refusing to read from a file location outside of project root. %r does not start with %r" % (path, PROJECT_DIR)
    xml = open(path, 'r').read()
    # write cache?
    return xml

def http_download(location):
    cred = None
    if location.startswith('https://s3.amazonaws.com'):
        # if we can find credentials, attach them
        session = botocore.session.get_session()
        cred = [getattr(session.get_credentials(), attr) for attr in ['access_key', 'secret_key']]
        if filter(None, cred): # remove any empty values
            cred = S3Auth(*cred)
    resp = requests.get(location, auth=cred)
    if resp.status_code != 200:
        raise RuntimeError("failed to download xml from location %r, got response code: %s" % (location, resp.status_code))
    return resp.text

def download(location):
    "download file, convert and pipe content straight into lax + transparent cache"
    protocol, path = location.split('://')
    downloaderficationer = {
        'https': lambda: http_download(location),
        # load files relative to adaptor root
        'file': partial(file_handler, path)
    }
    file_contents = downloaderficationer[protocol]()
    return file_contents

#
#
#

def mkresponse(status, message, request={}, **kwargs):
    packet = {
        "status": status,
        "message": message,
        "id": None,
        "token": None,
        "datetime": datetime.now(),
    }

    request = subdict(request, ['id', 'token', 'action'])
    request = renkeys(request, [("action", "requested-action")])
    packet.update(request)

    # merge in any explicit overrides
    packet.update(kwargs)

    # wrangle log context
    context = renkeys(packet, [("message", "status-message")])
    levels = {
        INVALID: logging.ERROR,
        ERROR: logging.ERROR,
        INGESTED: logging.DEBUG,
        PUBLISHED: logging.DEBUG
    }
    LOG.log(levels[packet["status"]], "%s response", packet['status'], extra=context)

    # bit ick
    if not packet['message']:
        del packet['message']

    return packet

@timeit
def handler(json_request, outgoing):
    response = partial(send_response, outgoing)

    try:
        request = utils.validate_request(json_request)
    except ValueError as err:
        # given bad data. who knows what it was. die
        return response(mkresponse(ERROR, "request could not be parsed: %s" % json_request))

    except ValidationError as err:
        # data is readable, but it's in an unknown/invalid format. die
        return response(mkresponse(ERROR, "request was incorrectly formed: %s" % err.message))

    except Exception as err:
        # die
        msg = "unhandled error attempting to handle request: %s" % err.message
        return response(mkresponse(ERROR, msg))

    # we have a valid request :)

    params = subdict(request, ['action', 'id', 'token', 'version'])
    params['force'] = request.get('force') # optional value

    # if we're to ingest/publish, then we expect a location to download article data
    if params['action'] in [INGEST, INGEST_PUBLISH]:
        try:
            article_xml = download(request['location'])
            if not article_xml:
                raise ValueError("no article content available")

        except AssertionError as err:
            msg = "refusing to download article xml: %s" % err.message
            return response(mkresponse(ERROR, msg, request))

        except Exception as err:
            msg = "failed to download article xml from %r: %s" % (request['location'], err.message)
            return response(mkresponse(ERROR, msg, request))

        try:
            article_data = main.render_single(article_xml, version=params['version'])
            if conf.SEND_LAX_PATCHED_AJSON: # makes in-place changes to the data
                validate.add_placeholders_for_validation(article_data)
        except Exception as err:
            error = err.message if hasattr(err, 'message') else err
            msg = "failed to render article-json from article-xml: %s" % error
            LOG.exception(msg, extra=params)
            return response(mkresponse(ERROR, msg, request))

        try:
            article_json = utils.json_dumps(article_data)
        except ValueError as err:
            msg = "failed to serialize article data to article-json: %s" % err.message
            return response(mkresponse(ERROR, msg, request))

        # phew! gauntlet ran, we're now confident of passing this article-json to lax
        # lax may still reject the data as invalid, but we'll proxy that back if necessary
        params['article_json'] = article_json

    try:
        lax_response = call_lax(**params)
        return response(mkresponse(**lax_response))

    except Exception as err:
        # lax didn't understand us or broke
        msg = "lax failed attempting to handle our request: %s" % err.message
        response(mkresponse(ERROR, msg, request))
        # when lax fails, we fail
        raise

try:
    import newrelic.agent
    handler = newrelic.agent.background_task()(handler)
except ImportError:
    pass

#
#
#

def read_from_sqs(stackname='temp'):
    "reads messages from an SQS queue, writes responses to another SQS queue"
    incoming = sqs_adaptor.IncomingQueue('bot-lax-%s-inc' % stackname)
    outgoing = sqs_adaptor.OutgoingQueue('bot-lax-%s-out' % stackname)
    return incoming, outgoing

def read_from_fs(path, **kwargs):
    "generates messages from a directory, writes responses to a log file"
    kwargs['path'] = path
    incoming = fs_adaptor.IncomingQueue(**kwargs)
    outgoing = fs_adaptor.OutgoingQueue()
    return incoming, outgoing

class Flag:
    def __init__(self):
        self.should_stop = False

    def stop(self):
        self.should_stop = True

def do(incoming, outgoing):
    flag = Flag()

    def signal_handler(signum, _frame):
        LOG.info("received signal %s", signum)
        flag.stop()
    signal.signal(signal.SIGTERM, signal_handler)

    # we'll see how far this abstraction gets us...
    try:
        for request in incoming:
            LOG.info("received request %s", request)
            handler(request, outgoing)
            print

            if flag.should_stop:
                LOG.info("stopping gracefully")
                return

    except KeyboardInterrupt:
        LOG.warn("stopping abruptly due to KeyboardInterrupt")

    finally:
        incoming.close()
        outgoing.close()


def bootstrap():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', choices=['sqs', 'fs'])

    # fs options
    parser.add_argument('--target', default=join(PROJECT_DIR, 'article-xml', 'articles'))
    parser.add_argument('--force', action='store_true', default=False)
    parser.add_argument('--action', choices=[INGEST, PUBLISH, INGEST_PUBLISH])

    # sqs options
    parser.add_argument('--instance', dest='instance_id', help='the "ci" in "lax--ci"')

    args = parser.parse_args()

    adaptors = {
        'fs': partial(read_from_fs, args.target),
        'sqs': read_from_sqs,
    }
    adaptor_type = args.type

    fn = adaptors[adaptor_type]
    if adaptor_type == 'fs':
        fn = partial(fn, action=args.action, force=args.force)
    else:
        if not args.instance_id:
            parser.error("--instance is required when --type=sqs")
        else:
            fn = partial(fn, args.instance_id)

    do(*fn())

if __name__ == '__main__':
    bootstrap()
