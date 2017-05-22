from .base import BaseCase
import utils
import sqlite3

class One(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_db_locked_recovery(self):

        def requests_get(sideaffected):
            if sideaffected[0] != 1:
                sideaffected[0] += 1
                raise sqlite3.OperationalError("EARTH SHATTERING KABOOOOOM")
            return 'success'

        # the function with the side effect will fail immediately
        sideeffect = [0]
        self.assertRaises(sqlite3.OperationalError, requests_get, sideeffect)

        # the wrapped function with the side effect will fail with a ValueError after 1 attempt
        sideeffect = [0]
        wrapped_requests_get = utils.do_safe_from(requests_get, [sqlite3.OperationalError], num_attempts=1)
        self.assertRaises(ValueError, wrapped_requests_get, sideeffect)

        # the wrapped function with the side effect will return 'success' after 2 attempts
        sideeffect = [0]
        wrapped_requests_get = utils.do_safe_from(requests_get, [sqlite3.OperationalError], num_attempts=2)
        self.assertEqual(wrapped_requests_get(sideeffect), 'success')
