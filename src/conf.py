import utils
import configparser as configparser
import inspect
import json
import logging
import os
from os.path import join
import log
from datetime import datetime

log.setup_root_logger()

_formatter = log.json_formatter() # todo: _formatter is unused, function call has side effects

# Files created by `www-data` or `elife` must have 664 permissions rather
# than the default 644. That leaves the files writable+readable by the
# whole group, which includes the other user.
os.umask(int('002', 8))

SRC_DIR = os.path.dirname(inspect.getfile(inspect.currentframe())) # "/path/to/bot-lax-adaptor/src/"
PROJECT_DIR = os.path.dirname(SRC_DIR)  # "/path/to/bot-lax-adaptor"

CFG_NAME = 'app.cfg'
DYNCONFIG = configparser.ConfigParser(**{
    'allow_no_value': True,
    # these can be used like template variables
    # https://docs.python.org/2/library/configparser.html
    'defaults': {'dir': PROJECT_DIR}})
DYNCONFIG.read(join(PROJECT_DIR, CFG_NAME)) # "/path/to/bot-lax-adaptor/app.cfg"

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
    """Creates a shared log for name and the current process,
    writing to `filename` with the append flag.

    On Linux this should ensure that no log entries are lost, thanks to kernel-specific behavior."""
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
utils.writable_dir(LOG_DIR)

IIIF_LOG_PATH = join(LOG_DIR, 'iiif.log')

#
#
#

PATH_TO_LAX = cfg('lax.location')

DEFAULT_CACHE_PATH = join(PROJECT_DIR, 'cache')
CACHE_PATH = cfg('general.cache_path', DEFAULT_CACHE_PATH)

INGEST, PUBLISH, INGEST_PUBLISH = 'ingest', 'publish', 'ingest+publish'

VALIDATED, INGESTED, PUBLISHED, INVALID, ERROR = 'validated', 'ingested', 'published', 'invalid', 'error'

XML_DIR = join(PROJECT_DIR, 'article-xml', 'articles')
JSON_DIR = join(PROJECT_DIR, 'article-json')

def load(path):
    path = join(PROJECT_DIR, 'schema', path)
    return json.load(open(path, 'r'))

POA_SCHEMA = load('api-raml/dist/model/article-poa.v4.json')
VOR_SCHEMA = load('api-raml/dist/model/article-vor.v8.json')
RELATED_SCHEMA = load('api-raml/dist/model/article-related.v2.json')

REQUEST_SCHEMA = load('request-schema.json')
RESPONSE_SCHEMA = load('response-schema.json')

API_URL = cfg("api.url") # "https://api.elifesciences.org", "http://prod--gateway.elife.internal"

CDN1 = cfg('general.cdn1') + '%(padded-msid)s/%(fname)s'

if cfg('general.env_for_cdn'):
    # "https://continuumtest.cdn.elifesciences.org/articles/"
    CDN = 'https://' + cfg('general.env_for_cdn') + '-' + CDN1
else:
    # "https://cdn.elifesciences.org/articles/"
    CDN = 'https://' + CDN1

# "https://iiif.elifesciences.org/lax/09560%2Fdefault.jpg"
CDN_IIIF = cfg('general.cdn_iiif') + '%(padded-msid)s%%2F%(fname)s'
IIIF = cfg('general.iiif') + '%(padded-msid)s%%2F%(fname)s/info.json'

# global requests_cache switch
REQUESTS_CACHING = True
# glencoe specific requests_cache switch
GLENCOE_REQUESTS_CACHING = cfg('glencoe.cache_requests', True)

REQUESTS_CACHE = join(CACHE_PATH, 'requests_cache')
REQUESTS_CACHE_DB = REQUESTS_CACHE + '.sqlite3'

# todo: remove this, unused
# *may* improve locked db problem
# https://requests-cache.readthedocs.io/en/latest/api.html#backends-dbdict
ASYNC_CACHE_WRITES = False

REQUESTS_CACHE_CONFIG = {
    'allowable_methods': ('GET', 'HEAD'),
    'cache_name': REQUESTS_CACHE,
    'backend': 'sqlite',
    'fast_save': ASYNC_CACHE_WRITES,
    'extension': '.sqlite3'
}

XML_REV = open(join(PROJECT_DIR, 'elife-article-xml.sha1'), 'r').read().strip()

JOURNAL_INCEPTION = 2012 # used to calculate volumes

# `published` date of earliest reviewed-preprint, 80494, "2022-10-20T03:00:00Z"
RPP_INCEPTION = datetime(year=2022, month=10, day=20, hour=3, minute=0, second=0)
