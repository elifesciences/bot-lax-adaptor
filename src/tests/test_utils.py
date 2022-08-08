from collections import OrderedDict
from .base import BaseCase
from unittest.mock import patch, call
from src import utils
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
        retcode, stdout = utils.run_script(['echo', '-n', 'foobar'.encode()])
        self.assertEqual(retcode, 0)
        self.assertEqual(stdout, 'foobar')

    def test_run_script_stdin(self):
        retcode, stdout = utils.run_script(['xargs', 'echo', '-n'], 'pants-party'.encode())
        self.assertEqual(stdout, 'pants-party')

    def test_run_script_auto_encodes_utf8_if_required(self):
        retcode, stdout = utils.run_script(['xargs', 'echo', '-n'], 'pants-party')
        self.assertEqual(stdout, 'pants-party')

    def test_video_msid(self):
        cases = [
            (9560, 9560),
            ('9560', '9560'),
            ('09560', '09560'),

            (10009560, '09560'),
            ('10009560', '09560'),

            # *not* what we want for the kitchen sink.
            # see `test_video_msid_2`
            (1234567890, '67890'),
            ('1234567890', '67890'),
        ]
        for given, expected in cases:
            self.assertEqual(expected, utils.video_msid(given))

    def test_video_msid_2(self):
        cases = [
            # all these should still work
            ((9560, None), 9560),
            (('9560', None), '9560'),
            (('09560', None), '09560'),

            ((10009560, None), '09560'),
            (('10009560', None), '09560'),

            # special case handling for the kitchen sink.
            # without a qualifier, the old behaviour is preserved.
            ((1234567890, None), '67890'),
            (('1234567890', None), '67890'),

            # with a qualifier, the kitchen sink now behaves differently.
            ((1234567890, 'elife-1234567890-fig3-video1.mp4'), '1234567890'),
            (('1234567890', 'elife-1234567890-fig3-video1.mp4'), '1234567890'),
        ]
        for (given, video_href), expected in cases:
            actual = utils.video_msid_2(given, video_href)
            self.assertEqual(expected, actual)

    def test_pad_filename(self):
        cases = [
            # no msid present
            (("https://foo.bar/baz.bup", 1234), "https://foo.bar/baz.bup"),

            # regular filename, regular article ID
            (("https://publishing-cdn.elifesciences.org/01234/elife-01234-v1.pdf", 1234),
             "https://publishing-cdn.elifesciences.org/01234/elife-01234-v1.pdf"),

            # regular filename, end2end article ID
            (("https://publishing-cdn.elifesciences.org/01234/elife-01234-v1.pdf", 10001234),
             "https://publishing-cdn.elifesciences.org/01234/elife-10001234-v1.pdf"),

            # kitchensink filename, end2end article ID
            (("https://publishing-cdn.elifesciences.org/1234567890/elife-1234567890-v1.pdf", 67171561234567890),
             "https://publishing-cdn.elifesciences.org/1234567890/elife-67171561234567890-v1.pdf"),
        ]
        for (filename, msid), expected in cases:
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

    @patch('time.sleep')
    def test_call_n_times_with_backoff(self, mock_sleep):

        def _fails_n_times(times):
            total = [0]

            def fn():
                if total[0] == times:
                    return 'result'
                total[0] = total[0] + 1
                raise ValueError('KABOOOM')
            return fn

        fn = _fails_n_times(3)
        func = utils.call_n_times(fn, [ValueError], num_attempts=10, initial_waiting_time=1)
        self.assertEqual(func(), 'result')
        self.assertEqual(mock_sleep.mock_calls, [call(1), call(2), call(4)])

    def test_sortdict(self):
        cases = [
            ({'z': 1, 'g': 1, 'a': 1}, OrderedDict([('a', 1), ('g', 1), ('z', 1)])),

            # nested items are ordered as well
            ({'z': 1, 'a': {'z': 1, 'g': 1, 'a': 1}}, OrderedDict([('a', OrderedDict([('a', 1), ('g', 1), ('z', 1)])), ('z', 1)])),

            # nested lists of dicts are ordered as well
            ({'a': [{'z': 1, 'g': 1, 'a': 1}]}, OrderedDict([('a', [OrderedDict([('a', 1), ('g', 1), ('z', 1)])])]))
        ]
        for given, expected in cases:
            self.assertEqual(utils.json_dumps(expected), utils.json_dumps(utils.sortdict(given)))
            # print(utils.sortdict(given))
            #utils.ensure(expected == utils.sortdict(given), "%s != %s" % (expected, utils.sortdict(given)))
