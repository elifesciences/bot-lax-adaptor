from datetime import datetime
from functools import partial, wraps
import json
import logging
import os
from os.path import join
import sys
from time import time
from awsauth import S3Auth
import botocore.session
from jsonschema import ValidationError
import requests
import signal
from urllib.parse import urlparse
import conf
from conf import (
    INVALID,
    ERROR,
    VALIDATED,
    INGESTED,
    PUBLISHED,
    INGEST,
    PUBLISH,
    INGEST_PUBLISH,

    PROJECT_DIR
)
import main as scraper, fs_adaptor, sqs_adaptor, utils
from utils import (
    subdict,
    renkeys,
    ensure,
    lfilter
)


LOG = logging.getLogger(__name__)

# output to adaptor.log
_handler = logging.FileHandler(join(conf.LOG_DIR, "adaptor.log"))
_handler.setLevel(logging.DEBUG)
_handler.setFormatter(conf._formatter)
LOG.addHandler(_handler)


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
        utils.validate(response, conf.RESPONSE_SCHEMA)
        channel = outgoing.write
    except ValidationError as err:
        # response doesn't validate. this probably means
        # we had an error decoding request and have no id or token
        # because the message will not validate, we will not be sending it back
        response['validation-error-msg'] = str(err)
        channel = outgoing.error
    channel(utils.json_dumps(response))
    return response

def find_lax():
    ensure(os.path.exists(conf.PATH_TO_LAX), "could not find lax")
    script = join(conf.PATH_TO_LAX, "manage.sh")
    ensure(os.path.exists(script), "could not find lax's manage.sh script")
    return script

def call_lax(action, msid, version, token, article_json=None, force=False, dry_run=False):
    #raise EnvironmentError("whoooooa. no.")
    cmd = [
        find_lax(), # /srv/lax/manage.sh
        "--skip-install",
        "ingest",
        "--" + action, # ll: --ingest+publish
        "--serial",
        "--id", str(msid),
        "--version", str(version),
    ]
    if dry_run:
        cmd += ["--dry-run"]
    if force:
        cmd += ["--force"]
    lax_stdout = None
    try:
        rc, lax_stdout = utils.run_script(cmd, article_json)
        lax_resp = json.loads(lax_stdout)

        bot_lax_resp = {
            "id": msid,
            "status": None,
            # not present in success responses
            # added in error responses
            #"message":
            #"code":
            #"comment":
            "datetime": datetime.now(),

            # additional attributes we'll be returning
            "action": action,
            "force": force,
            "dry-run": dry_run,
            "token": token,
        }

        # ensure everything that lax returns is preserved
        # valid adaptor responses are handled in `mkresponse`
        # valid api responses are handled in api.post_xml
        bot_lax_resp.update(lax_resp)
        bot_lax_resp['id'] = str(bot_lax_resp['id'])
        return bot_lax_resp

    except ValueError as err:
        # could not parse lax response. this is a lax error
        raise RuntimeError("failed to parse response from lax, expecting json, got error %r from stdout %r" %
                           (str(err), lax_stdout))

def file_handler(path):
    ensure(path.startswith(PROJECT_DIR),
           "unsafe operation - refusing to read from a file location outside of project root. %r does not start with %r" % (path, PROJECT_DIR))
    xml = open(path, 'r').read()
    # write cache?
    return xml

def http_download(location):
    cred = None
    if location.startswith('https://s3-external-1.amazonaws.com/') or location.startswith('https://s3.amazonaws.com/'):
        s3_base = urlparse(location).hostname
        # if we can find credentials, attach them
        session = botocore.session.get_session()
        cred = [getattr(session.get_credentials(), attr) for attr in ['access_key', 'secret_key']]
        if lfilter(None, cred): # remove any empty values
            cred = S3Auth(*cred, service_url=s3_base)
    resp = requests.get(location, auth=cred)
    if resp.status_code != 200:
        raise RuntimeError("failed to download xml from %r, got response code: %s\n%s" % (location, resp.status_code, resp.content))
    resp.encoding = 'utf-8'
    return resp.text

def download(location):
    "download file, convert and pipe content straight into lax + transparent cache"
    ensure('://' in location[:10], 'no protocol found in %r, failing' % location)
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
    packet.update(request)

    # merge in any explicit overrides
    packet.update(kwargs)

    # more response wrangling
    packet = renkeys(packet, [
        ("action", "requested-action"),
        ("dry-run", "validate-only")
    ])

    # remove any keys not supported in the schema
    supported_keys = conf.RESPONSE_SCHEMA['properties'].keys()
    packet = subdict(packet, supported_keys)

    # wrangle log context
    context = renkeys(packet, [("message", "status-message")])
    levels = {
        INVALID: logging.ERROR,
        ERROR: logging.ERROR,
        VALIDATED: logging.INFO,
        INGESTED: logging.DEBUG,
        PUBLISHED: logging.DEBUG
    }
    LOG.log(levels[packet["status"]], "%s response", packet['status'], extra=context)

    # success messages are None
    if not packet['message']:
        del packet['message']

    # double-publications are successful
    if kwargs.get('code') == 'already-published':
        packet['status'] = PUBLISHED

    return packet

@timeit
def handler(json_request, outgoing):
    response = partial(send_response, outgoing)

    try:
        request = utils.validate(json_request, conf.REQUEST_SCHEMA)
    except ValueError as err:
        # bad data. who knows what it was. die
        return response(mkresponse(ERROR, "request could not be parsed: %s" % json_request))

    except ValidationError as err:
        # data is readable, but it's in an unknown/invalid format. die
        return response(mkresponse(ERROR, "request was incorrectly formed: %s" % str(err)))

    except Exception as err:
        # die
        msg = "unhandled error attempting to handle request: %s" % str(err)
        return response(mkresponse(ERROR, msg))

    # we have a valid request :)
    LOG.info("valid request")

    params = subdict(request, ['action', 'id', 'token', 'version', 'force', 'validate-only'])
    params = renkeys(params, [('validate-only', 'dry_run')])

    # if we're to ingest/publish, then we expect a location to download article data
    if params['action'] in [INGEST, INGEST_PUBLISH]:
        try:
            article_xml = download(request['location'])
            if not article_xml:
                raise ValueError("no article content available")

        except AssertionError as err:
            msg = "refusing to download article xml: %s" % str(err)
            return response(mkresponse(ERROR, msg, request))

        except Exception as err:
            msg = "failed to download article xml from %r: %s" % (request['location'], str(err))
            return response(mkresponse(ERROR, msg, request))

        LOG.info("got xml")

        try:
            article_data = scraper.render_single(article_xml,
                                                 version=params['version'],
                                                 location=request['location'])
            LOG.info("rendered article data ")

        except Exception as err:
            error = str(err) if hasattr(err, 'message') else err
            msg = "failed to render article-json from article-xml: %s" % error
            LOG.exception(msg, extra=params)
            return response(mkresponse(ERROR, msg, request))

        LOG.info("successful scrape")

        try:
            article_json = utils.json_dumps(article_data)
        except ValueError as err:
            msg = "failed to serialize article data to article-json: %s" % str(err)
            return response(mkresponse(ERROR, msg, request))

        LOG.info("successfully serialized article-data to article-json")

        # phew! gauntlet ran, we're now confident of passing this article-json to lax
        # lax may still reject the data as invalid, but we'll proxy that back if necessary
        params['article_json'] = article_json

    try:
        LOG.info("calling lax") # with params: %r" % params)

        lax_response = call_lax(**params)

        LOG.info("lax response: %r", lax_response)

        return response(mkresponse(**lax_response))

    except Exception as err:
        # lax didn't understand us or broke
        msg = "lax failed attempting to handle our request: %s" % str(err)
        response(mkresponse(ERROR, msg, request))
        # when lax fails, we fail
        raise

# todo: why is this imported down here?
# if the reason is 'circular reference', we need to do a better job
try:
    import newrelic.agent
    handler = newrelic.agent.background_task()(handler)
except ImportError:
    pass

#
#
#

def read_from_sqs(env, **kwargs):
    "reads messages from an SQS queue, writes responses to another SQS queue"
    incoming = sqs_adaptor.IncomingQueue('bot-lax-%s-inc' % env, **kwargs) # ll: bot-lax-end2end-inc
    outgoing = sqs_adaptor.OutgoingQueue('bot-lax-%s-out' % env)           # ll: bot-lax-end2end-out
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
    # we'll see how far this abstraction gets us...
    try:
        for request in incoming:
            LOG.info("received request %s", request)
            handler(request, outgoing)

    except KeyboardInterrupt:
        LOG.warn("stopping abruptly due to KeyboardInterrupt")

    LOG.info("graceful shutdown")

def _setup_interrupt_flag():
    flag = Flag()

    def signal_handler(signum, _frame):
        LOG.info("received signal %s", signum)
        flag.stop()
    signal.signal(signal.SIGTERM, signal_handler)

    return flag

def main(*flgs):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', choices=['sqs', 'fs'])

    # fs options
    parser.add_argument('--target', default=join(PROJECT_DIR, 'article-xml', 'articles'))
    parser.add_argument('--force', action='store_true', default=False)
    parser.add_argument('--action', choices=[INGEST, PUBLISH, INGEST_PUBLISH])
    parser.add_argument('--validate-only', action='store_true', default=False)

    args = parser.parse_args(flgs or sys.argv[1:])

    adaptors = {
        'fs': partial(read_from_fs, args.target),
        'sqs': read_from_sqs,
    }
    adaptor_type = args.type

    fn = adaptors[adaptor_type]
    flag = _setup_interrupt_flag()

    if adaptor_type == 'fs':
        fn = partial(fn, action=args.action, force=args.force)
    else:
        fn = partial(fn, env=conf.ENV, flag=flag)

    do(*fn())

if __name__ == '__main__':
    main()
