import os, json

import logging
LOG = logging.getLogger(__name__)

class IncomingQueue(object):
    def __init__(self, dirname, action):
        self.action = action
        self.dirname = dirname

    def next(self):
        for path in os.listdir(self.dirname):
            _, msid, ver = os.path.split(path)[-1].split('-') # ll: ['elife', '09560', 'v1.xml']
            ver = int(ver[1]) # "v1.xml" -> 1
            yield json.dumps({
                'action': self.action,
                'location': path,
                'id': msid,
                'version': ver,
                'force': False,
                'token': 'pants-party'
            })

class OutgoingQueue(object):    
    def write(self, string):
        LOG.info(string)

    def close(self):
        pass
