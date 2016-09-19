import dateutil
import subprocess
import json
from datetime import datetime
import os
from os.path import join
import requests
#from . import main, fs_adaptor
import main, fs_adaptor
from functools import partial
from jsonschema import validate
from jsonschema import ValidationError

import logging
LOG = logging.getLogger(__name__)

class StateError(RuntimeError):
    pass

DEBUG = True
PATHS_TO_LAX = [
    '/srv/lax/',
    '/home/luke/dev/python/lax/'
]
PROJECT_DIR = os.getcwdu() # ll: /path/to/adaptor/
INGEST, PUBLISH, INGEST_PUBLISH = 'ingest', 'publish', 'ingest+publish'
INGESTED, PUBLISHED, INVALID, ERROR = 'ingested', 'published', 'invalid', 'error'

def json_dumps(obj):
    "drop-in for json.dumps that handles datetime objects."
    def datetime_handler(obj):
        if hasattr(obj, 'isoformat'):
            return {"-val": obj.isoformat(), "-type": "datetime"}
        else:
            raise TypeError, 'Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj))
    return json.dumps(obj, default=datetime_handler)

def json_loads(string):
    def datetime_handler(obj):
        if not obj.get("-type"):
            return obj
        return dateutil.parser.parse
    return json.loads(string, object_hook=datetime_handler)

def doresponse(outgoing, response):
    json_response = json_dumps(response)
    outgoing.write(json_response)
    LOG.error(json_response)
    return response

def _run_script(args, article_content):
    try:
        # https://docs.python.org/2/library/subprocess.html#subprocess.check_output
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE) # returns stdout
        stdout, stderr = process.communicate(article_content)
        return stdout
    except subprocess.CalledProcessError as err:
        # non-zero response
        retcode = err.returncode
        LOG.error("got return code calling lax: %s", retcode)
        raise

def get_exec():
    dirname = filter(os.path.exists, PATHS_TO_LAX)
    assert dirname, "could not find lax"
    script = join(dirname[0], "manage.sh")
    assert os.path.exists(script), "could not find lax's manage.sh script"
    return script

def call_lax(action, id, version, force, article_json):
    cmd = [get_exec(), "ingest", "--" + action] #, article_json]
    if force:
        cmd += ["--force"]
    raw_result = _run_script(cmd, article_json)
    print raw_result
    results = json_loads(raw_result)
    status = results['status']
    if status == INVALID:
        raise StateError("lax says no")
    if status == ERROR:
        raise RuntimeError("something bad happened")
    return {
        "status": status,
        "datetime": results['datetime']
    }

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

#
#
#

def ingest(request):
    params = subdict(request, 'action', 'id', 'version')
    params.update({
        'force': request.get('force'),
        'article_json': json.dumps(main.render_single(download(request['location'])))
    })
    return call_lax(**params)

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
    request = json_loads(json_request)
    schema = json.load(open(join(PROJECT_DIR, 'schema', 'request-schema.json'), 'r'))
    try:
        validate(request, schema)
        LOG.info("request successfully validated")
        valid_request = request
        return valid_request
    
    except ValueError as err:
        # your json is broken
        raise ValidationError("validation error: '%s' for: %s" % (err.message, request))
    
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
        results = response(actions[request['action']](request))
        return response(mkresponse(**results))

    except StateError as err:
        if DEBUG:
            raise
        return response(mkresponse(INVALID, err.message))

    except ValidationError as err:
        if DEBUG:
            raise
        return response(mkresponse(INVALID, "your request was incorrectly formed: %s" % err.message))

    except Exception as err:
        if DEBUG:
            raise
        return response(mkresponse(ERROR, "an unhandled exception occured attempting to handle your request: %s" % err.message))

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
