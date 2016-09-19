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
            yield json.dumps({
                'action': self.action,
                'location': 'file://' + path,
                'id': msid,
                'version': ver,
                'force': False,
                'token': 'pants-party'
            })

    def close(self):
        pass

class OutgoingQueue(object):    
    def write(self, string):
        LOG.info(string)

    def close(self):
        pass
