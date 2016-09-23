import os, json, logging
from os.path import join
from pythonjsonlogger import jsonlogger

LOG = logging.getLogger(__name__)

_supported_keys = [
    'asctime',
    'created',
    'filename',
    'funcName',
    'levelname',
    'levelno',
    'lineno',
    'module',
    'msecs',
    'message',
    'name',
    'pathname',
    'process',
    'processName',
    'relativeCreated',
    'thread',
    'threadName'
]
_log_format = ['%({0:s})'.format(i) for i in _supported_keys]
_log_format = ' '.join(_log_format)
_formatter = jsonlogger.JsonFormatter(_log_format)
_handler = logging.StreamHandler()
_handler.setFormatter(_formatter)
LOG.addHandler(_handler)

# configure logging here

DEBUG = False
PATHS_TO_LAX = [
    '/srv/lax/',
    '/home/luke/dev/python/lax/'
]
PROJECT_DIR = os.getcwdu() # ll: /path/to/adaptor/
INGEST, PUBLISH, INGEST_PUBLISH = 'ingest', 'publish', 'ingest+publish'
INGESTED, PUBLISHED, INVALID, ERROR = 'ingested', 'published', 'invalid', 'error'

def json_load(path):
    path = join(PROJECT_DIR, 'schema', path)
    return json.load(open(path, 'r'))

POA_SCHEMA = json_load('api-raml/dist/model/article-poa.v1.json')
VOR_SCHEMA = json_load('api-raml/dist/model/article-vor.v1.json')

REQUEST_SCHEMA = json_load('request-schema.json')
RESPONSE_SCHEMA = json_load('response-schema.json')
