import os, json
from os.path import join
import logging

LOG = logging.getLogger(__name__)

class IncomingQueue(object):
    def __init__(self, dirname, action):
        self.action = action
        self.dirname = dirname

    def __iter__(self):
        for fname in os.listdir(self.dirname):
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
            yield request

    def close(self):
        pass

class OutgoingQueue(object):
    def __init__(self):
        self.passes = []
        self.invalids = []
        self.errors = []

    def write(self, string):
        LOG.info(string)
        try:
            struct = json.loads(string)
            if struct['status'] in ['published', 'ingested']:
                q = self.passes
            else:
                q = self.errors if struct['status'] == 'error' else self.invalids
        except:
            q = self.errors
        q.append(string)

    def error(self, response):
        self.errors.append(response)
        
    def close(self):
        pass
