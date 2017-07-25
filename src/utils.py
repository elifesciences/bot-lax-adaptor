import sqlite3
import requests
import os, copy
import subprocess
import time
import json
import jsonschema
from jsonschema import validate as validator
from jsonschema import ValidationError
# import conf # don't do this, conf.py depends on utils.py

import logging
LOG = logging.getLogger(__name__)

class StateError(RuntimeError):
    pass

def pad_msid(msid):
    return str(int(msid)).zfill(5)

def pad_filename(msid, filename):
    # Rename the file itself for end2end tests
    match = '-' + str(video_msid(msid)) + '-'
    replacement = '-' + str(pad_msid(msid)) + '-'
    return filename.replace(match, replacement)

def video_msid(msid):
    """Replaces the msid of testing articles with the reference one they were generated from.

    Leaves real articles untouched"""
    if int(msid) > 100000:
        return pad_msid(str(msid)[-5:])
    return msid

def ensure(assertion, msg, *args):
    """intended as a convenient replacement for `assert` statements that
    get compiled away with -O flags"""
    if not assertion:
        raise AssertionError(msg % args)

def writable_dir(path):
    ensure(os.path.exists(path), "path doesn't exist: %s" % path)
    # directories need to be executable as well to be considered writable
    ensure(os.access(path, os.W_OK | os.X_OK), "directory isn't writable: %s" % path)

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
    return {k: v for k, v in data.items() if k in lst}

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
        validator(struct, schema, format_checker=jsonschema.FormatChecker())
        return struct

    except ValueError as err:
        # your json is broken
        raise ValidationError("validation error: '%s' for: %s" % (err.message, struct))

    except ValidationError as err:
        # your json is incorrect
        LOG.error("struct failed to validate against schema: %s" % err.message)
        raise

def json_dumps(obj, **kwargs):
    "drop-in for json.dumps that handles datetime objects."
    def datetime_handler(obj):
        if hasattr(obj, 'isoformat'):
            return ymdhms(obj)
        else:
            raise TypeError('Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj)))
    return json.dumps(obj, default=datetime_handler, **kwargs)


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
        for i in xrange(0, num_attempts):
            try:
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

def requests_get(*args, **kwargs):
    def target(*args, **kwargs):
        response = requests.get(*args, **kwargs)
        if response.status_code >= 500:
            raise RemoteResponseTemporaryError("Status code was %s" % response.status_code)
        return response
    return call_n_times(
        target,
        [sqlite3.OperationalError, RemoteResponseTemporaryError],
        initial_waiting_time=1
    )(*args, **kwargs)

#
#
#

import pytz
from datetime import datetime
from dateutil import parser
from rfc3339 import rfc3339

def todt(val):
    "turn almost any formatted datetime string into a UTC datetime object"
    if val is None:
        return None
    dt = val
    if not isinstance(dt, datetime):
        dt = parser.parse(val, fuzzy=False)
    dt.replace(microsecond=0) # not useful, never been useful, will never be useful.

    if not dt.tzinfo:
        # no timezone (naive), assume UTC and make it explicit
        LOG.debug("encountered naive timestamp %r from %r. UTC assumed.", dt, val)
        return pytz.utc.localize(dt)

    else:
        # ensure tz is UTC
        if dt.tzinfo != pytz.utc:
            LOG.debug("converting an aware dt that isn't in utc TO utc: %r", dt)
            return dt.astimezone(pytz.utc)
    return dt

def ymdhms(dt):
    "returns an rfc3339 representation of a datetime object"
    if dt:
        dt = todt(dt) # convert to utc, etc
        return rfc3339(dt, utc=True)
