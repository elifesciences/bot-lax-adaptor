import glob
from datetime import datetime, timedelta
import urllib
import base64
import json
import os
import requests
import conf
from utils import ensure, call_n_times
import logging

LOG = logging.getLogger(__name__)

class RemoteResponseTemporaryError(RuntimeError):
    pass

class RemoteResponsePermanentError(RuntimeError):
    pass

def read_response_from_cache(cache_key):
    "reads a cache file from the disk as json"
    with open(cache_key, "r") as fh:
        return json.load(fh)

def write_response_to_cache(simple_response, cache_key):
    "writes a cache file to disk as json"
    os.makedirs(os.path.dirname(cache_key), exist_ok=True)
    with open(cache_key, "w") as fh:
        json.dump(simple_response, fh, indent=4)

def _valid_cache_exists(cache_key, expiry_seconds):
    """returns `True` if the given `cache_key` is 'valid'.
    A valid cache key is a path to a file that exists on the filesystem whose
    last modification date + conf.REQUESTS_CACHE_EXPIRY_SECONDS isn't older than now().
    Returns `False` when caching is disabled."""
    if not os.path.exists(cache_key):
        return False
    if not expiry_seconds:
        return True
    last_mod_dt = datetime.fromtimestamp(os.path.getmtime(cache_key))
    offset = last_mod_dt + timedelta(seconds=expiry_seconds)
    return offset < datetime.now()

def valid_cache_exists(cache_key, expiry_seconds):
    """returns `True` if the given `cache_key` is 'valid'.
    A valid cache key is a path to a file that exists on the filesystem whose
    last modification date + conf.REQUESTS_CACHE_EXPIRY_SECONDS isn't older than now().
    Returns `False` when caching is disabled."""
    if not conf.REQUESTS_CACHING:
        return False
    return _valid_cache_exists(cache_key, expiry_seconds)

def requests_cache_create_key(url, cache_root=None):
    "returns an absolute path to a place to write content for the given `url`, rooted in the given `cache_root` directory."
    cache_root = cache_root or conf.CACHE_PATH
    bits = urllib.parse.urlparse(url)
    params = bits.query
    if params:
        # params exist, order them for a predictable cache key
        params = "&".join(sorted(params.split("&")))
        params = "?" + params
    url = "%s://%s%s%s" % (bits.scheme, bits.netloc, bits.path, params)
    b64_encoded_url = base64.urlsafe_b64encode(url.encode("utf-8")).decode()
    # "/path/to/cache/static-movie-usa.glencoesoftware.com/0f10378e095dde7aaf579af504c4bfdc6fb86550==.json"
    # "/path/to/cache/prod--iiif.elifesciences.org/0f10378e095dde7aaf579af504c4bfdc6fb86550==.json"
    path = os.path.join(cache_root, bits.netloc, b64_encoded_url) + ".json"
    return os.path.abspath(path)

def _clear_cached_response(cache_key):
    "deletes a cache file from the disk"
    LOG.debug("deleting cached response: %s" % (cache_key,))
    # os.unlink(cache_key) # TODO: reenable once thoroughly tested
    return True

def clear_cached_response(url, cache_root=None):
    "safely deletes a cache file from the disk"
    cache_root = cache_root or conf.REQUESTS_CACHE_PATH
    cache_key = requests_cache_create_key(url, cache_root)
    if os.path.exists(cache_key) and cache_key.startswith(cache_root):
        return _clear_cached_response(cache_key)
    return False

def clear_expired():
    "removes expired entries from the cache, if installed. returns path to database regardless of installation"

    # "/path/to/cache/prod--iiif.elifesciences.org/0f10378e095dde7aaf579af504c4bfdc6fb86550==.json"
    # "/path/to/cache/             *              /                     *                    .json"
    pattern = "%s/*/*.json" % conf.REQUESTS_CACHE_PATH
    for cache_key in glob.glob(pattern):
        if _valid_cache_exists(cache_key, conf.REQUESTS_CACHE_EXPIRY_SECONDS):
            _clear_cached_response(cache_key)

def make_response_simple(response):
    "converts a requests `response` object to a simple dictionary that can be cached."
    return {
        'url': response.url,
        'status_code': response.status_code,
        'reason': response.reason,
        'headers': dict(response.headers),
        'encoding': response.encoding,
        'text': response.text, # `.text` is a string, `.content` is bytes
    }

def _request(url, *args, **kwargs):
    "simple wrapper around `requests.get` with disk caching."

    method = kwargs.pop('method', 'get')
    fn = getattr(requests, method)

    cache_root = kwargs.pop('cache_root', None)
    cache_key = requests_cache_create_key(url, cache_root)
    LOG.info("Requesting url %s (cache key '%s')", url, cache_key)

    if valid_cache_exists(cache_key, conf.REQUESTS_CACHE_EXPIRY_SECONDS):
        LOG.debug("cache hit: %s" % url)
        simple_response = read_response_from_cache(cache_key)

    else:
        LOG.debug("cache miss: %s" % url)
        response = fn(url, *args, **kwargs)
        simple_response = make_response_simple(response)

        # only cache successful responses
        if response.status_code == 200:
            write_response_to_cache(simple_response, cache_key)

    if simple_response['status_code'] >= 500:
        raise RemoteResponseTemporaryError("Status code was %s" % simple_response['status_code'])

    return simple_response

def _requests_method(*args, **kwargs):
    """wrapper around `_requests_get`, but re-attempts the request up to 3 times with exponential backoff for temporary errors.
    raises a `RemoteResponsePermanentError` if failure to make a request"""

    method = kwargs.pop('method', 'get')
    ensure(method in ['get', 'head'], 'unsupported requests method %r' % method)

    # caching is enabled by default, pass `disable_cache=False` to bypass caching.
    cache_disabled = kwargs.pop('disable_cache', False)

    if cache_disabled:
        fn = getattr(requests, method)
    else:
        fn = _request
        kwargs['method'] = method

    num_attempts = 3
    resp = call_n_times(
        fn,
        [RemoteResponseTemporaryError],
        num_attempts,
        initial_waiting_time=1
    )(*args, **kwargs)

    if resp is None:
        # function has been called `num_attempts` and has been caught each time.
        # at this point we have an empty response.
        raise RemoteResponsePermanentError("failed to call %r %s times" % (args[0], num_attempts))
    return resp

def requests_get(*args, **kwargs):
    kwargs['method'] = 'get'
    return _requests_method(*args, **kwargs)

def requests_head(*args, **kwargs):
    kwargs['method'] = 'head'
    return _requests_method(*args, **kwargs)
