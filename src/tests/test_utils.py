from base import BaseCase
import utils
from datetime import datetime

class Utils(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_json_dumps(self):
        then = datetime(year=2001, month=1, day=1, hour=23, minute=59)
        struct = {'now': then}
        expected = '{"now": "2001-01-01T23:59:00"}'
        self.assertEqual(utils.json_dumps(struct), expected)

    def test_json_dumps_unhandled_obj(self):
        struct = {'someobj': self}
        self.assertRaises(TypeError, utils.json_dumps, struct)

    def test_run_script(self):
        retcode, stdout = utils.run_script(['echo', '-n', 'foobar'])
        self.assertEqual(retcode, 0)
        self.assertEqual(stdout, 'foobar')

    def test_run_script_stdin(self):
        retcode, stdout = utils.run_script(['xargs', 'echo', '-n'], 'pants-party')
        self.assertEqual(stdout, 'pants-party')
