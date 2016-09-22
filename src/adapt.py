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
from utils import StateError

from conf import PATHS_TO_LAX, INVALID, ERROR, PROJECT_DIR, INGEST, INGEST_PUBLISH

import logging
LOG = logging.getLogger(__name__)

def doresponse(outgoing, response):
    utils.validate_response(response)
    json_response = utils.json_dumps(response)
    outgoing.write(json_response)
    LOG.error(json_response)
    return response

def find_lax():
    dirname = filter(os.path.exists, PATHS_TO_LAX)
    assert dirname, "could not find lax"
    script = join(dirname[0], "manage.sh")
    assert os.path.exists(script), "could not find lax's manage.sh script"
    return script

def call_lax(action, id, version, article_json=None, force=False, dry_run=True):
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
        status = results['status']
        if status == INVALID:
            raise StateError("lax says no")
        if status == ERROR:
            raise RuntimeError("something bad happened")
        
        # successful response :)
        return {
            "status": status,
            "datetime": results['datetime']
        }
    except ValueError as err:
        # could not parse lax response. this is a lax error
        raise RuntimeError("could not parse response from lax, expecting json, got error: %s" % err.message)

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

def subdict(data, *lst):
    return {k:v for k,v in data.items() if k in lst}

def renkeys(data, pair_list):
    data = copy.deepcopy(data)
    for key, replacement in pair_list:
        if data.has_key(key):
            data[replacement] = data[key]
            del data[key]
    return data

#
#
#

def mkresponse(status, message=None, **kwargs):
    request = kwargs.pop('request', {})
    request = subdict(request, ['id', 'token'])
    packet = {
        "status": status,
        "message": message,
        "id": None,
        "token": None,
        "datetime": datetime.now(),
    }
    packet.update(request)
    packet.update(kwargs)
    context = renkeys(packet, [("message", "status-message")])
    LOG.error("returning an %s response", packet['status'], extra=context)
    return packet

def handler(json_request, outgoing):
    response = partial(doresponse, outgoing)
    
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

    params = subdict(request, 'action', 'id', 'version')
    params['force'] = request.get('force') # optional value
    
    # if we're to ingest/publish, then we expect a location to download article data
    if params['action'] in [INGEST, INGEST_PUBLISH]:
        try:
            article_xml = download(request['location'])
        except Exception as err:
            msg = "failed to download article xml from %r: %s" % (request['location'], err.message)
            return response(mkresponse(ERROR, msg, request=request))

        try:
            article_data = main.render_single(article_xml)
        except Exception as err:
            msg = "failed to render article-json from article-xml: %s" % err.message
            return response(mkresponse(ERROR, msg, request=request))

        try:
            article_json = utils.json_dumps(article_data)
        except ValueError as err:
            msg = "failed to serialize article data to article-json: %s" % err.message
            return response(mkresponse(ERROR, msg, request=request))

        # phew! gauntlet ran, we're now confident of passing this article-json to lax
        # lax may still reject the data as invalid, but we'll proxy that back if necessary
        params['article_json'] = article_json

    try:
        lax_response = call_lax(**params)
        return response(mkresponse(**lax_response))

    except StateError as err:
        # lax understood our request but rejected it :(
        return response(mkresponse(INVALID, err.message, request=request))

    except Exception as err:
        # lax didn't understand us or broke
        msg = "lax failed attempting to handle our request: %s"
        return response(mkresponse(ERROR, msg, request=request))

#
#
#

def read_from_sqs():
    "reads messages from an SQS queue, writes responses to another SQS queue"
    incoming = outgoing = None
    return incoming, outgoing

def read_from_fs(path=join(PROJECT_DIR, 'article-xml', 'articles')):
    "generates messages from a directory, writes responses to a log file"
    incoming = fs_adaptor.IncomingQueue(path, INGEST_PUBLISH)
    outgoing = fs_adaptor.OutgoingQueue() 
    return incoming, outgoing

def do(incoming, outgoing):
    # we'll see how far this abstraction gets us...
    try:
        for request in incoming:
            handler(request, outgoing)
    finally:
        incoming.close()
        outgoing.close()
        
if __name__ == '__main__':
    do(*read_from_fs())
