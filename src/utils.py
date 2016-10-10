import os
import subprocess
import json
from jsonschema import validate as validator
from jsonschema import ValidationError
#from os.path import join
import conf

import logging
LOG = logging.getLogger(__name__)

class StateError(RuntimeError):
    pass

def validate(struct, schema):
    # if given a string, assume it's json and try to load it
    # if given a data, assume it's serializable, dump it and load it
    try:
        if isinstance(struct, basestring):
            struct = json.loads(struct)
        else:
            struct = json.loads(json_dumps(struct))
    except ValueError as err:
        LOG.error("struct is not serializable: %s", err.message)
        raise

    try:
        validator(struct, schema)
        return struct

    except ValueError as err:
        # your json is broken
        raise ValidationError("validation error: '%s' for: %s" % (err.message, struct))

    except ValidationError as err:
        # your json is incorrect
        LOG.error("struct failed to validate against schema: %s" % err.message)
        raise

def validate_request(request):
    "validates incoming request"
    return validate(request, conf.REQUEST_SCHEMA)

def validate_response(response):
    "validates outgoing response"
    return validate(response, conf.RESPONSE_SCHEMA)

def json_dumps(obj):
    "drop-in for json.dumps that handles datetime objects."
    def datetime_handler(obj):
        if hasattr(obj, 'isoformat'):
            # return {"-val": obj.isoformat(), "-type": "datetime"}
            return obj.isoformat()
        else:
            raise TypeError('Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj)))
    return json.dumps(obj, default=datetime_handler)


'''
def json_loads(string):
    def datetime_handler(obj):
        if not obj.get("-type"):
            return obj
        return dateutil.parser.parse
    return json.loads(string, object_hook=datetime_handler)
'''


def run_script(args, user_input=None):
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    if user_input:
        stdout, stderr = process.communicate(user_input)
    else:
        stdout, stderr = process.communicate()
    return process.returncode, stdout

def version_from_path(path):
    _, msid, ver = os.path.split(path)[-1].split('-') # ll: ['elife', '09560', 'v1.xml']
    ver = int(ver[1]) # "v1.xml" -> 1
    return msid, ver
