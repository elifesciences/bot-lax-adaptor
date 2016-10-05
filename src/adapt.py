import copy
from jsonschema import ValidationError
import json
from datetime import datetime
import os
from os.path import join
import requests
import main, fs_adaptor
from functools import partial
import utils

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


def send_response(outgoing, response):
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
        raise RuntimeError("could not parse response from lax, expecting json, got error %r from stdout %r" % \
            (err.message, lax_stdout))

def file_handler(path):
    assert path.startswith(PROJECT_DIR), \
      "unsafe operation - refusing to read from a file location outside of project root. %r does not start with %r" % (path, PROJECT_DIR)
    xml = open(path, 'r').read()
    # write cache?
    return xml

def download(location):
    "download file, convert and pipe content straight into lax + transparent cache"
    protocol, path = location.split('://')
    downloaderficationer = {
        'https': lambda: requests.get(location).text,
        # load files relative to adaptor root
        'file': partial(file_handler, path)
    }
    file_contents = downloaderficationer[protocol]()
    return file_contents

def subdict(data, lst):
    return {k:v for k,v in data.items() if k in lst}

def renkeys(data, pair_list):
    "returns a copy of the given data with the list of oldkey->newkey pairs changes made"
    data = copy.deepcopy(data)
    for key, replacement in pair_list:
        if data.has_key(key):
            data[replacement] = data[key]
            del data[key]
    return data

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
        except AssertionError as err:
            msg = "refusing to download article xml: %s" % err.message
            return response(mkresponse(ERROR, msg, request))

        except Exception as err:
            msg = "failed to download article xml from %r: %s" % (request['location'], err.message)
            return response(mkresponse(ERROR, msg, request))

        try:
            article_data = main.render_single(article_xml, version=params['version'])
        except Exception as err:
            msg = "failed to render article-json from article-xml: %s" % err.message
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

#
#
#

def read_from_sqs():
    "reads messages from an SQS queue, writes responses to another SQS queue"
    incoming = outgoing = None
    return incoming, outgoing

def read_from_fs(path=join(PROJECT_DIR, 'article-xml', 'articles'), **kwargs):
    "generates messages from a directory, writes responses to a log file"
    kwargs['path'] = path
    incoming = fs_adaptor.IncomingQueue(**kwargs)
    outgoing = fs_adaptor.OutgoingQueue()
    return incoming, outgoing

def do(incoming, outgoing):
    # we'll see how far this abstraction gets us...
    try:
        for request in incoming:
            LOG.info("received request %s", request)
            handler(request, outgoing)

            print

    finally:
        incoming.close()
        outgoing.close()


def bootstrap():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', default=False)
    parser.add_argument('--action', choices=[INGEST, PUBLISH, INGEST_PUBLISH], default=INGEST)

    args = parser.parse_args()
    do(*read_from_fs(action=args.action, force=args.force))
    
if __name__ == '__main__':
    bootstrap()
