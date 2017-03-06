import os, json
from os.path import join
import logging
import utils, conf

LOG = logging.getLogger(__name__)

def mkreq(path, **overrides):
    path = 'file://' + path if not path.startswith('https://') else path
    msid, ver = utils.version_from_path(path)
    request = {
        'action': conf.INGEST,
        'location': path,
        'id': msid,
        'version': ver,
        'force': False,
        'token': 'pants-party'
    }
    request.update(overrides)
    # don't ever generate an invalid request
    utils.validate_request(request)
    return request

class SimpleQueue(object):
    def __init__(self, path_list):
        self.paths = path_list

    def __iter__(self):
        for path in self.paths:
            LOG.debug("processing path: %s", path)
            yield path

class IncomingQueue(object):
    def __init__(self, path, action=conf.INGEST, force=False):
        self.action = action
        self.force = force
        self.dirname = path

    def __iter__(self):
        paths = os.listdir(self.dirname)
        naledi = "elife-09560-v1.xml"
        if naledi in paths:
            paths.remove(naledi)
            paths = [naledi] + paths # naledi is always tested first :)
        for fname in paths:
            if fname.startswith('.') or not fname.endswith('.xml'):
                # hidden or not xml, skip
                continue
            path = join(self.dirname, fname)
            LOG.debug("processing file: %s", path)
            yield mkreq(path, force=self.force, action=self.action)

class OutgoingQueue(object):
    def __init__(self):
        self.valids = []
        self.invalids = []
        self.errors = []

    def write(self, string):
        "called when given a VALID message"
        LOG.info(string)
        struct = json.loads(string)
        if struct['status'] in [conf.PUBLISHED, conf.INGESTED]:
            q = self.valids
        else:
            q = self.errors if struct['status'] == 'error' else self.invalids
        q.append(struct)

    def error(self, string):
        "called when given a bad message"
        try:
            struct = json.loads(string)
            self.errors.append(struct)
        except ValueError:
            print 'WHHHHOOAOA - what did I just get??'
            self.errors.append(string)

    def dump(self):
        print 'valid ::', self.valids
        print 'invalid ::', self.invalids
        print 'errors ::', self.errors
