import os, json, logging
from os.path import join
from pythonjsonlogger import jsonlogger
import configparser as configparser

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

#
#
#

PROJECT_DIR = os.getcwdu() # ll: /path/to/adaptor/

CFG_NAME = 'app.cfg'
DYNCONFIG = configparser.SafeConfigParser(**{
    'allow_no_value': True,
    # these can be used like template variables
    # https://docs.python.org/2/library/configparser.html
    'defaults': {'dir': PROJECT_DIR}})
DYNCONFIG.read(join(PROJECT_DIR, CFG_NAME)) # ll: /path/to/lax/app.cfg

def cfg(path, default=0xDEADBEEF):
    lu = {'True': True, 'true': True, 'False': False, 'false': False} # cast any obvious booleans
    try:
        val = DYNCONFIG.get(*path.split('.'))
        return lu.get(val, val)
    except (configparser.NoOptionError, configparser.NoSectionError): # given key in section hasn't been defined
        if default == 0xDEADBEEF:
            raise ValueError("no value/section set for setting at %r" % path)
        return default
    except Exception:
        raise

#
#
#

ENV = cfg('general.env')

PATH_TO_LAX = cfg('lax.location')

# certain values that can't be known at render time are
# added so the result can be validated against the schema
PATCH_AJSON_FOR_VALIDATION = True

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

CDN1 = 'cdn.elifesciences.org/articles/%(padded-msid)s/%(fname)s'
CDN2 = 'publishing-cdn.elifesciences.org/%(padded-msid)s/%(fname)s'

DEFAULT_CDN = CDN1 if False else CDN2 # 'False' until we finish switching to a single CDN :(
CDNS_BY_ENV = {
    'end2end': 'end2end-' + CDN2,
    'continuumtest': 'continuumtest-' + CDN2,
}
CDN = 'https://' + CDNS_BY_ENV.get(ENV, DEFAULT_CDN)

# this coincides with the IIIF server now, but it will be put behind a CDN soon
# used for generating public links
CDN_IIIF = 'https://' + ENV + '--iiif.elifesciences.org/lax:%(padded-msid)s/%(fname)s'
# used for direct access to the IIIF server
IIIF = 'https://' + ENV + '--iiif.elifesciences.org/lax:%(padded-msid)s/%(fname)s'

# NOTE: do not move to /tmp
GLENCOE_CACHE = join(PROJECT_DIR, 'glencoe-cache') # ll: /opt/bot-lax-adaptor/glencoe-cache.sqlite3
IIIF_CACHE = join(PROJECT_DIR, 'iiif-cache')

XML_REV = open(join(PROJECT_DIR, 'elife-article-xml.sha1'), 'r').read()

JOURNAL_INCEPTION = 2012 # used to calculate volumes
