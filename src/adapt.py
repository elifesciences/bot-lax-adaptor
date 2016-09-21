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

DEBUG = False
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

def run_script(args, user_input):
    try:
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        if user_input:
            stdout, stderr = process.communicate(user_input)
        else:
            stdout, stderr = process.communicate()
        return process.returncode, stdout
    except IOError as err:
        LOG.exception("unhandled I/O error attempting to call lax: %s" % err)
        raise err

#
#
#

def doresponse(outgoing, response):
    json_response = json_dumps(response)
    outgoing.write(json_response)
    LOG.error(json_response)
    return response

def get_exec():
    dirname = filter(os.path.exists, PATHS_TO_LAX)
    assert dirname, "could not find lax"
    script = join(dirname[0], "manage.sh")
    assert os.path.exists(script), "could not find lax's manage.sh script"
    return script

def call_lax(action, id, version, article_json=None, force=False, dry_run=True):
    cmd = [
        get_exec(),
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
        rc, lax_stdout = run_script(cmd, article_json)        
        results = json_loads(lax_stdout)
        status = results['status']
        print results
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

#
#
#

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
        params = subdict(request, 'action', 'id', 'version')
        params['force'] = request.get('force')
        if params['action'] in [INGEST, INGEST_PUBLISH]:
            try:
                params['article_json'] = json.dumps(main.render_single(download(request['location'])))
            except:
                raise RuntimeError("error parsing xml -> json")
        results = call_lax(**params)
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
