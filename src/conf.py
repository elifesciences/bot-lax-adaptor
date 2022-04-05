import configparser as configparser
import inspect
import json
import logging
import os
from os.path import join
import yaml
# import utils # don't do this
import log

def writable_dir(path):
    """returns `True` if given `path` exists, is a directory and writeable+executable.
    raises an `AssertionError` if not."""
    if not os.path.exists(path):
        raise AssertionError("path doesn't exist: %r" % path)
    if not os.path.isdir(path):
        raise AssertionError("path is not a directory: %r" % path)
    if not os.access(path, os.W_OK | os.X_OK):
        raise AssertionError("directory isn't writeable: %r" % path)
    return True

log.setup_root_logger()

_formatter = log.json_formatter() # todo: _formatter is unused, function call has side effects

os.umask(int('002', 8))
SRC_DIR = os.path.dirname(inspect.getfile(inspect.currentframe())) # ll: /path/to/adaptor/src/
PROJECT_DIR = os.path.dirname(SRC_DIR)  # ll: /path/to/adaptor/


CFG_NAME = 'app.cfg'
DYNCONFIG = configparser.ConfigParser(**{
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

def multiprocess_log(filename, name=__name__):
    """Creates a shared log for name and the current process, writing to filename
    with the append flag.

    On Linux this should ensure that no log entries are lost, thanks to kernel-specific behavior"""
    log = logging.getLogger("%s.%d" % (name, os.getpid()))
    if not log.handlers:
        _handler = logging.FileHandler(filename)
        _handler.setLevel(logging.INFO)
        _handler.setFormatter(logging.Formatter('%(levelname)s - %(asctime)s - %(message)s'))
        log.addHandler(_handler)
    return log

LOG_DIR = PROJECT_DIR
if ENV != DEV:
    LOG_DIR = '/var/log/bot-lax-adaptor/'
writable_dir(LOG_DIR)

IIIF_LOG_PATH = join(LOG_DIR, 'iiif.log')

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
        return yaml.load(open(path, 'r'), Loader=yaml.FullLoader)

POA_SCHEMA = load('api-raml/dist/model/article-poa.v3.json')
VOR_SCHEMA = load('api-raml/dist/model/article-vor.v6.json')

REQUEST_SCHEMA = load('request-schema.json')
RESPONSE_SCHEMA = load('response-schema.json')

API_SCHEMA = load('api.yaml')

# can be overriden when creating an app
API_UPLOAD_FOLDER = join(PROJECT_DIR, "uploads")
if ENV != DEV:
    API_UPLOAD_FOLDER = cfg('general.upload_path', API_UPLOAD_FOLDER)
writable_dir(API_UPLOAD_FOLDER)

# pre-validate means 'validate with placeholders in bot-lax before proper validating on lax'
API_PRE_VALIDATE = cfg('api.pre_validate', True)

CDN1 = cfg('general.cdn1') + '%(padded-msid)s/%(fname)s'

if cfg('general.env_for_cdn'):
    CDN = 'https://' + cfg('general.env_for_cdn') + '-' + CDN1
else:
    CDN = 'https://' + CDN1

CDN_IIIF = cfg('general.cdn_iiif') + '%(padded-msid)s%%2F%(fname)s'
IIIF = cfg('general.iiif') + '%(padded-msid)s%%2F%(fname)s/info.json'

# global requests caching switch
REQUESTS_CACHING = True

# how long should a request be cached for?
REQUESTS_CACHE_EXPIRY_SECONDS = None # None is 'no expiry'

# glencoe specific requests caching switch.
# this allow you to disable caching responses from Glencoe while caching all other requests.
GLENCOE_REQUESTS_CACHING = cfg('glencoe.cache_requests', True)

REQUESTS_CACHE_PATH = join(CACHE_PATH, 'requests_cache')

XML_REV = open(join(PROJECT_DIR, 'elife-article-xml.sha1'), 'r').read()

JOURNAL_INCEPTION = 2012 # used to calculate volumes
