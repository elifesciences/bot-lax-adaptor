from os.path import join
import conf
from flex.core import validate
import flex

def validates(spec):
    path = join(conf.PROJECT_DIR, 'schema', 'api.yaml')
    spec = flex.load(path)
    validate(spec)
    return True
