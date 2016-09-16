import json
from datetime import datetime
import os
from os.path import join
import requests
from . import main, fs_adaptor
from functools import partial
from jsonschema import validate
from jsonschema import ValidationError

import logging
LOG = logging.getLogger(__name__)

class StateError(RuntimeError):
    pass

PROJECT_DIR = os.path.basename(__name__)
INGEST, PUBLISH, INGEST_PUBLISH = 'ingest', 'publish', 'ingest+publish'
INVALID, ERROR = 'invalid', 'error'

print PROJECT_DIR
exit()

def doresponse(outgoing, response):
    outgoing.write(response)
    LOG.error(response)
    return response

def call_lax(action, msid, version, force, article_json):
    cmd = "./manage.sh ingest"
    results = os.system(cmd)
    if results.fail:
        raise StateError("lax says no")
    if results.error:
        raise RuntimeError("somethign basdf happened")
    return results
    
def download(location):
    """
    download file, convert and pipe content straight into lax with transparent cache?

    """
    file_contents = requests.get(location)
    return file_contents

def subdict(data, *lst):
    return {k:v for k,v in data if k in lst}

#
#
#

def ingest(request):
    params = subdict(request, 'action', 'id', 'version')
    params.update({
        'force': request.get('force'),
        'article_json': main.render_single(download(request['location']))
    })
    results = call_lax(**params)
    if results.fail:
        raise StateError("lax says no")
    if results.error:
        raise RuntimeError("somethign basdf happened")
    return results

def publish(request):
    params = subdict(request, 'action', 'id', 'version')
    params['force'] = request.get('force')
    return call_lax(**params)

def ingest_publish(request):
    ingest(request)
    return publish(request)

def mkresponse(status, message=None, **kwargs):
    packet = {
        "status": status,
        "message": message,
        "id": None,
        "token": None,
        "datetime": datetime.now(),
    }
    packet.update(kwargs)
    return packet

def validate_request(json_request):
    "validates incoming request"
    try:
        request = json.loads(json_request)
        schema = json.load(open(join(PROJECT_DIR, 'schema', 'request-schema.json')), 'r')
        return validate(request, schema)
    
    except ValueError as err:
        # your json is broken
        raise ValidationError(err.message)
    
    except ValidationError as err:
        # your json is incorrect
        LOG.error("incoming message failed to validate against schema: %s" % err.message)
        raise

def handler(request, outgoing):
    response = partial(doresponse, outgoing)    
    try:
        request = validate_request(request) # throws ValidationError
        actions = {
            INGEST: ingest,
            INGEST_PUBLISH: ingest_publish,
            PUBLISH: publish
        }
        return actions[request['action']]

    except StateError as err:
        return response(mkresponse(INVALID, err.message()))

    except ValidationError as err:
        return response(mkresponse(INVALID, "your request was incorrectly formed: %s" % err.message()))

    except Exception as err:
        return response(mkresponse(ERROR, "an unhandled exception occured attempting to handle your request: %s" % err.message()))

#
#
#

def read_from_sqs():
    "reads messages from an SQS queue, writes responses to another SQS queue"
    incoming = outgoing = None
    return incoming, outgoing

def read_from_fs():
    "generates messages from a directory, writes responses to a log file"
    incoming = fs_adaptor.IncomingQueue(join(PROJECT_DIR, 'article-xml'), INGEST_PUBLISH)
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
