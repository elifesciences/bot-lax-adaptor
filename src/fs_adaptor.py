import os, json
from os.path import join
import logging
import utils, conf

LOG = logging.getLogger(__name__)

class IncomingQueue(object):
    def __init__(self, dirname, action):
        self.action = action
        self.dirname = dirname

    def __iter__(self):
        paths = os.listdir(self.dirname)
        naledi = "elife-09560-v1.xml"
        paths.remove(naledi)
        paths = [naledi] + paths
        for fname in paths:
            if fname.startswith('.') or not fname.endswith('.xml'):
                # hidden or not xml, skip
                continue
            path = join(self.dirname, fname)
            _, msid, ver = os.path.split(path)[-1].split('-') # ll: ['elife', '09560', 'v1.xml']
            ver = int(ver[1]) # "v1.xml" -> 1
            LOG.debug("processing file: %s", path)
            request = {
                'action': self.action,
                'location': 'file://' + path,
                'id': msid,
                'version': ver,
                'force': False,
                'token': 'pants-party'
            }
            # don't ever generate an invalid request
            utils.validate_request(request) 
            yield request

    def close(self):
        pass

class OutgoingQueue(object):
    def __init__(self):
        self.valids = []
        self.invalids = []
        self.errors = []

    def write(self, string):
        LOG.info(string)
        struct = json.loads(string)
        if struct['status'] in [conf.PUBLISHED, conf.INGESTED]:
            q = self.valids
        else:
            q = self.errors if struct['status'] == 'error' else self.invalids
        q.append(struct)

    def error(self, string):
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
        
    def close(self):
        pass
