import os, json, logging
from os.path import join
from pythonjsonlogger import jsonlogger

ROOTLOG = logging.getLogger("")

_supported_keys = [
    #'asctime',
    #'created',
    'filename',
    'funcName',
    'levelname',
    #'levelno',
    'lineno',
    'module',
    'msecs',
    'message',
    'name',
    'pathname',
    #'process',
    #'processName',
    #'relativeCreated',
    #'thread',
    #'threadName'
]
# optional json logging if you need it
_log_format = ['%({0:s})'.format(i) for i in _supported_keys]
_log_format = ' '.join(_log_format)
_formatter = jsonlogger.JsonFormatter(_log_format)

# output to stderr
_handler = logging.StreamHandler()
_handler.setLevel(logging.INFO)
_handler.setFormatter(logging.Formatter('%(levelname)s - %(asctime)s - %(message)s'))

ROOTLOG.addHandler(_handler)
ROOTLOG.setLevel(logging.DEBUG)

def multiprocess_log(filename, name=__name__):
    """Creates a shared log for name and the current process, writing to filename
    with the append flag.

    On Linux this should ensure that no log entries are lost, thanks to kernel-specific behavior"""
    log = logging.getLogger("%s.%d" % (__name__, os.getpid()))
    if not log.handlers:
        _handler = logging.FileHandler(filename)
        _handler.setLevel(logging.INFO)
        _handler.setFormatter(logging.Formatter('%(levelname)s - %(asctime)s - %(message)s'))
        log.addHandler(_handler)
    return log

DEBUG = False
PATHS_TO_LAX = map(os.path.expanduser, [
    '/srv/lax/',
    '~/dev/python/lax/'
])

SEND_LAX_PATCHED_AJSON = True

PROJECT_DIR = os.getcwdu() # ll: /path/to/adaptor/
INGEST, PUBLISH, INGEST_PUBLISH = 'ingest', 'publish', 'ingest+publish'
INGESTED, PUBLISHED, INVALID, ERROR = 'ingested', 'published', 'invalid', 'error'

XML_DIR = join(PROJECT_DIR, 'article-xml', 'articles')
JSON_DIR = join(PROJECT_DIR, 'article-json')
VALID_JSON_DIR = join(JSON_DIR, 'valid')
INVALID_JSON_DIR = join(JSON_DIR, 'invalid')
VALID_PATCHED_JSON_DIR = join(JSON_DIR, 'patched') # only valid json is output to the patched dir

def json_load(path):
    path = join(PROJECT_DIR, 'schema', path)
    return json.load(open(path, 'r'))

POA_SCHEMA = json_load('api-raml/dist/model/article-poa.v1.json')
VOR_SCHEMA = json_load('api-raml/dist/model/article-vor.v1.json')

REQUEST_SCHEMA = json_load('request-schema.json')
RESPONSE_SCHEMA = json_load('response-schema.json')

CDN_PROTOCOL = 'https'
CDN_BASE_URL = '//cdn.elifesciences.org'

OTHER_CDN_HOST = 'publishing-cdn.elifesciences.org'
def set_temporary_cdn_host(host):
    global OTHER_CDN_HOST
    OTHER_CDN_HOST = host

def other_cdn_host():
    return OTHER_CDN_HOST
