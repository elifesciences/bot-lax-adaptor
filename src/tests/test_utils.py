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
        expected = '{"now": "2001-01-01T23:59:00Z"}'
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

    def test_video_msid(self):
        self.assertEqual(9560, utils.video_msid(9560))
        self.assertEqual('9560', utils.video_msid('9560'))
        self.assertEqual('09560', utils.video_msid('09560'))
        self.assertEqual('09560', utils.video_msid('10009560'))
        self.assertEqual('09560', utils.video_msid(10009560))

    def test_pad_filename(self):
        cases = [
            ((1234, "https://foo.bar/baz.bup"), "https://foo.bar/baz.bup"),
            ((10001234, "https://publishing-cdn.elifesciences.org/01234/elife-01234-v1.pdf"), "https://publishing-cdn.elifesciences.org/01234/elife-10001234-v1.pdf"),
        ]
        for (msid, filename), expected in cases:
            self.assertEqual(utils.pad_filename(msid, filename), expected)

    def test_call_n_times(self):
        def fn(sideaffected):
            if sideaffected != [2]:
                sideaffected[0] += 1
                raise ValueError('KABOOOM')
            return True

        # called once, it explodes
        sideeffect = [0]
        self.assertRaises(ValueError, fn, sideeffect)

        # called with call_n_times, it eventually returns True
        sideeffect = [0]
        func = utils.call_n_times(fn, [ValueError])
        self.assertTrue(func(sideeffect))

        # function is only called when we explicitly call it
        sideeffect = [0]
        func = utils.call_n_times(fn, [ValueError], num_attempts=1)
        func(sideeffect) # call once
        self.assertRaises(ValueError, fn, sideeffect) # call again
        self.assertEqual(func(sideeffect), True) # call a final time
