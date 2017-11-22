import inspect
import os, json, logging
from os.path import join
from pythonjsonlogger import jsonlogger
import utils
import configparser as configparser
import yaml

os.umask(int('002', 8))
SRC_DIR = os.path.dirname(inspect.getfile(inspect.currentframe())) # ll: /path/to/adaptor/src/
PROJECT_DIR = os.path.dirname(SRC_DIR)  # ll: /path/to/adaptor/


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

ENV = cfg('general.env')
DEV, VAGRANT, CONTINUUMTEST, END2END, PROD = 'dev', 'vagrant', 'continuumtest', 'end2end', 'prod'
if ENV == DEV and os.path.exists('/vagrant'):
    ENV = VAGRANT

#
#
#

ROOTLOG = logging.getLogger("")

_supported_keys = [
    'asctime',
    #'created',
    'filename',
    'funcName',
    'levelname',
    #'levelno',
    'lineno',
    'module',
    #'msecs',
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

class FormatterWithEncodedExtras(logging.Formatter):
    def format(self, record):
        # exclude all known keys in Record
        # bundle the remainder into an 'extra' field,
        # bypassing attempt to make Record read-only
        _known_keys = [
            'asctime', 'created', 'filename', 'funcName', 'levelname', 'levelno', 'lineno',
            'module', 'msecs', 'message', 'name', 'pathname', 'process', 'processName',
            'relativeCreated', 'thread', 'threadName',
            # non-formatting fields present in __dict__
            'exc_text', 'exc_info', 'msg', 'args',
        ]
        unknown_fields = {key: val for key, val in record.__dict__.items() if key not in _known_keys}
        record.__dict__['extra'] = utils.json_dumps(unknown_fields)
        return super(FormatterWithEncodedExtras, self).format(record)

_handler.setFormatter(FormatterWithEncodedExtras('%(levelname)s - %(asctime)s - %(message)s -- %(extra)s'))

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

LOG_DIR = PROJECT_DIR
if ENV != DEV:
    LOG_DIR = '/var/log/bot-lax-adaptor/'
utils.writable_dir(LOG_DIR)

#
#
#

PATH_TO_LAX = cfg('lax.location')

DEFAULT_CACHE_PATH = join(PROJECT_DIR, 'cache')
CACHE_PATH = cfg('general.cache_path', DEFAULT_CACHE_PATH)

INGEST, PUBLISH, INGEST_PUBLISH = 'ingest', 'publish', 'ingest+publish'

# these values are mostly duplicated in schema/api.yaml
# if you update here, update there.
VALIDATED, INGESTED, PUBLISHED, INVALID, ERROR = 'validated', 'ingested', 'published', 'invalid', 'error'
BAD_OVERRIDES, BAD_UPLOAD, BAD_SCRAPE = 'problem-overrides', 'problem-uploading-xml', 'problem-scraping-xml'
ERROR_INVALID = 'invalid-article-json' # eh
ERROR_VALIDATING, ERROR_COMMUNICATING = 'error-validating-article-json', 'error-sending-article-json'

XML_DIR = join(PROJECT_DIR, 'article-xml', 'articles')
JSON_DIR = join(PROJECT_DIR, 'article-json')

def load(path):
    path = join(PROJECT_DIR, 'schema', path)
    if path.endswith('.json'):
        return json.load(open(path, 'r'))
    elif path.endswith('.yaml'):
        return yaml.load(open(path, 'r'))

POA_SCHEMA = load('api-raml/dist/model/article-poa.v2.json')
VOR_SCHEMA = load('api-raml/dist/model/article-vor.v2.json')

REQUEST_SCHEMA = load('request-schema.json')
RESPONSE_SCHEMA = load('response-schema.json')

API_SCHEMA = load('api.yaml')

# can be overriden when creating an app
API_UPLOAD_FOLDER = join(PROJECT_DIR, "uploads")
if ENV != DEV:
    API_UPLOAD_FOLDER = cfg('general.upload_path', API_UPLOAD_FOLDER)
utils.writable_dir(API_UPLOAD_FOLDER)

CDN1 = 'cdn.elifesciences.org/articles/%(padded-msid)s/%(fname)s'

DEFAULT_CDN = CDN1
CDNS_BY_ENV = {
    END2END: 'end2end-' + CDN1,
    CONTINUUMTEST: 'continuumtest-' + CDN1,
}
CDN = 'https://' + CDNS_BY_ENV.get(ENV, DEFAULT_CDN)

if ENV == PROD:
    # used for generating public links
    CDN_IIIF = 'https://iiif.elifesciences.org/lax:%(padded-msid)s/%(fname)s'
    # used for direct access to the IIIF server
    IIIF = 'https://prod--iiif.elifesciences.org/lax:%(padded-msid)s/%(fname)s/info.json'
elif ENV in [CONTINUUMTEST, END2END]:
    CDN_IIIF = 'https://' + ENV + '--cdn-iiif.elifesciences.org/lax:%(padded-msid)s/%(fname)s'
    IIIF = 'https://' + ENV + '--iiif.elifesciences.org/lax:%(padded-msid)s/%(fname)s/info.json'
else:
    # default to prod as a data source for testing
    CDN_IIIF = 'https://prod--cdn-iiif.elifesciences.org/lax:%(padded-msid)s/%(fname)s'
    IIIF = 'https://prod--iiif.elifesciences.org/lax:%(padded-msid)s/%(fname)s/info.json'

# should our http requests to external services be cached?
REQUESTS_CACHING = True
REQUESTS_CACHE = join(CACHE_PATH, 'requests-cache')

# *may* improve locked db problem
# https://requests-cache.readthedocs.io/en/latest/api.html#backends-dbdict
ASYNC_CACHE_WRITES = False

XML_REV = open(join(PROJECT_DIR, 'elife-article-xml.sha1'), 'r').read()

JOURNAL_INCEPTION = 2012 # used to calculate volumes
