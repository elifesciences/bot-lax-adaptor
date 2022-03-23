import copy
import io
import json
import os
import sqlite3
import subprocess
import time
from collections import OrderedDict
import jsonschema
from jsonschema import validate as validator, ValidationError
import requests
import requests_cache
import dateutils

# import conf # don't do this, conf.py depends on utils.py

import logging
LOG = logging.getLogger(__name__)

lmap = lambda func, *iterable: list(map(func, *iterable))

lfilter = lambda func, *iterable: list(filter(func, *iterable))

#keys = lambda d: list(d.keys())

#lzip = lambda *iterable: list(zip(*iterable))


def is_file(obj):
    try:
        return isinstance(obj, file)
    except NameError:
        return isinstance(obj, io.IOBase)


class StateError(RuntimeError):
    pass

def pad_msid(msid):
    return str(int(msid)).zfill(5)

def pad_filename(msid, filename):
    "rename the referenced file for end2end tests"
    # elife-09560-foo.ext => "-09560-" =>  elife-676378463709560-foo.ext
    # elife-1234567890-foo.ext => "-1234567890-" =>  elife-676301234567890-foo.ext
    match = '-' + str(video_msid_2(msid, filename)) + '-'
    replacement = '-' + str(pad_msid(msid)) + '-'
    return filename.replace(match, replacement)

def video_msid(msid):
    """Replaces the `msid` of testing articles with the reference one they were generated from.
    Leaves real articles untouched."""
    if int(msid) > 100000:
        return pad_msid(str(msid)[-5:])
    return msid

def video_msid_2(msid, video_href=None):
    """Replaces the `msid` of testing articles with the reference one they were generated from.
    Leaves real articles AND the kitchen sink untouched.

    Testing uses actual articles and generates a very long random msid from their shorter one.
    For example: 09560 => 5432109560 (trailing msid is preserved)

    All instances of the msid in the XML are replaced with this generated msid.
    `utils.video_msid` *truncates* this so external references continue pointing to the actual article assets.
    For example: 5432109560 => 09560

    The kitchen sink however is its own article with its own set of videos.
    Its msid is still changed from 1234567890 to a generated one *except* for video hrefs.
    See `elife-spectrum/update-kitchen-sinks-from-github.sh`."""
    kitchen_sink_msid = '1234567890'
    # `video_href` looks like "elife-1234567890-fig3-video1.mp4"
    if video_href and kitchen_sink_msid in video_href:
        return kitchen_sink_msid
    return video_msid(msid)

def ensure(assertion, msg, exception_class=AssertionError):
    """intended as a convenient replacement for `assert` statements that
    get compiled away with -O flags"""
    if not assertion:
        raise exception_class(msg)

def writable_dir(path):
    ensure(os.path.exists(path), "path doesn't exist: %r" % path)
    # directories need to be executable as well to be considered writable
    ensure(os.access(path, os.W_OK | os.X_OK), "directory isn't writable: %r" % path)

def contains_any(ddict, key_list):
    return any([key in ddict for key in key_list])

def has_all_keys(ddict, key_list):
    return all([key in ddict for key in key_list])

def rmkeys(ddict, key_list, pred):
    "immutable. removes all keys from ddict in given key list if pred is true"
    data = copy.deepcopy(ddict)
    for key in key_list:
        if key in ddict and pred(data[key]):
            del data[key]
    return data

def renkeys(data, pair_list):
    "returns a copy of the given data with the list of oldkey->newkey pairs changes made"
    data = copy.deepcopy(data)
    for key, replacement in pair_list:
        if key in data:
            data[replacement] = data[key]
            del data[key]
    return data

def subdict(data, lst):
    keyvals = [(k, v) for k, v in data.items() if k in lst]
    fn = OrderedDict if isinstance(data, OrderedDict) else dict
    return fn(keyvals)


def first(x):
    try:
        # if we've been given an iterator, use `next` instead
        if hasattr(x, 'next'):
            return next(x)
        return x[0]
    except (StopIteration, IndexError, TypeError):
        return None

def validate(struct, schema):
    # if given a string, assume it's json and try to load it
    # else, assume it's serializable, dump it and load it
    try:
        if isinstance(struct, str):
            struct = json.loads(struct)
        else:
            struct = json.loads(json_dumps(struct))
    except ValueError as err:
        LOG.error("struct is not serializable: %s", str(err))
        raise

    try:
        validator(struct, schema, format_checker=jsonschema.FormatChecker())
        return struct

    except ValueError as err:
        # your json is broken
        raise ValidationError("validation error: '%s' for: %s" % (str(err), struct))

    except ValidationError as err:
        # your json is incorrect
        LOG.error("struct failed to validate against schema: %s" % str(err))
        raise

def json_dumps(obj, **kwargs):
    return dateutils.json_dumps(obj, **kwargs)

def json_loads(string):
    return json.loads(string, object_pairs_hook=OrderedDict)

def run_script(args, user_input=None):
    # doesn't log because LOG is created before conf.py is evaluated
    # extract src/logger.py
    LOG.info("run_script: %s", args)
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    if user_input:
        try:
            user_input = user_input.encode('utf-8')
        except AttributeError:
            pass
        stdout, stderr = process.communicate(user_input)
    else:
        stdout, stderr = process.communicate()
    return process.returncode, stdout.decode('utf-8')

def version_from_path(path):
    _, msid, ver = os.path.split(path)[-1].split('-') # ll: ['elife', '09560', 'v1.xml']
    ver = int(ver[1]) # "v1.xml" -> 1
    return msid, ver

def partial_match(pattern, actual):
    # print 'testing %s against %s' % (pattern, actual)
    t1, t2 = type(pattern), type(actual)
    ensure(isinstance(t2, type(t1)), "type error, expecting %r got %r" % (t1, t2))
    if isinstance(pattern, dict):
        for key, val in pattern.items():
            partial_match(val, actual[key])

    elif isinstance(pattern, list):
        l1, l2 = len(pattern), len(actual)
        ensure(l1 == l2, "wrong number of elements, expecting %r got %r on %r" % (l1, l2, pattern))
        for idx, val in enumerate(pattern):
            partial_match(val, actual[idx])

    else:
        ensure(actual == pattern, "%r != %r" % (actual, pattern))

    return True

#
#
#

def call_n_times(fn, protect_from, num_attempts=3, initial_waiting_time=0):
    """if after calling `num_attempts` it fails to return a value, it will return None

    Uses exponential backoff not to overload the target, if initial_waiting_time is specified"""
    def wrap(*args, **kwargs):
        waiting_time = initial_waiting_time
        for i in range(0, num_attempts):
            try:
                # print 'calling',args[0],i
                return fn(*args, **kwargs)
            except BaseException as err:
                if type(err) in protect_from:
                    LOG.error("caught error: %s" % err)
                    if waiting_time:
                        time.sleep(waiting_time)
                        waiting_time = waiting_time * 2
                    continue
                raise
    return wrap

class RemoteResponseTemporaryError(RuntimeError):
    pass

class RemoteResponsePermanentError(RuntimeError):
    pass

# keeping this here as cache_requests would create a mutual dependency between conf and utils
def requests_cache_create_key(prepared_request):
    return requests_cache.get_cache().create_key(prepared_request)

'''
# works, but only good for debugging/mocking responses
def dumpobj(obj):
    import cPickle, time
    from os.path import join
    import conf
    fname = str(int(time.time() * 1000000)) + ".pickle"
    path = join(conf.PROJECT_DIR, fname)
    pickler = cPickle.Pickler(open(path, 'w'))
    pickler.dump(obj)
    return path

def loadobj(path):
    pass
'''

def requests_get(*args, **kwargs):
    def target(*args, **kwargs):
        # https://2.python-requests.org/en/master/user/advanced/#prepared-requests
        request = requests.Request('GET', *args, **kwargs)
        prepared_request = request.prepare()
        s = requests.Session()

        # if caching enabled, log the key used to cache the response
        if hasattr(s, 'cache'): # test if requests_cache is enabled
            cache_key = requests_cache_create_key(prepared_request)
            LOG.info("Requesting url %s (cache key '%s')", args[0], cache_key)
        else:
            LOG.info("Requesting url %s", args[0])

        response = s.send(prepared_request)
        if response.status_code >= 500:
            raise RemoteResponseTemporaryError("Status code was %s" % response.status_code)
        #dumpobj((request, response))
        return response
    num_attempts = 3
    resp = call_n_times(
        target,
        [sqlite3.OperationalError, RemoteResponseTemporaryError],
        num_attempts,
        initial_waiting_time=1
    )(*args, **kwargs)
    if resp is None:
        # function has been called num_attempts and has been caught each time.
        # at this point we have an empty response.
        raise RemoteResponsePermanentError("failed to call %r %s times" % (args[0], num_attempts))
    return resp

def todt(val):
    return dateutils.todt(val)

def ymdhms(dt):
    return dateutils.ymdhms(dt)

def sortdict(d):
    "imposes alphabetical ordering on a dictionary. returns an OrderedDict"
    if isinstance(d, list):
        return lmap(sortdict, d)
    elif not isinstance(d, dict):
        return d
    keyvals = sorted(d.items(), key=lambda pair: pair[0])
    keyvals = lmap(lambda pair: (pair[0], sortdict(pair[1])), keyvals)
    return OrderedDict(keyvals)
