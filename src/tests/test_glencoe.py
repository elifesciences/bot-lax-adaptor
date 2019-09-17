import requests
from tests import base
from src import glencoe
from unittest.mock import patch

class Cmd(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_metadata_not_found(self):
        with patch('utils.requests_get') as mock:
            mock.return_value.status_code = 404
            self.assertEqual({}, glencoe.metadata(1))

    def test_metadata_found_eventually(self):
        resp = requests.Response()
        resp._content = b'{}' # successful but empty response
        resp.status_code = 404
        resp.call_count = 0

        def new_send(*args):
            if resp.call_count == 2:
                resp.status_code = 200
            resp.call_count += 1
            return resp

        with patch('utils._requests_get_send', new=new_send):
            with self.assertRaises(AssertionError) as ae:
                glencoe.metadata(1)
                # we successfully got a response after 2 404s (even though it was empty)
                self.assertEqual(resp.call_count, 2)
                self.assertEqual(str(ae), "glencoe returned successfully, but response is empty")

    def test_metadata_unhandled_response_code(self):
        "metadata logs the body of the response on an unhandled response"
        with patch('utils.requests_get') as mock:
            with patch.object(glencoe, 'LOG') as mock_logger:
                mock.return_value.status_code = 418
                self.assertRaises(ValueError, glencoe.metadata, 1)
                self.assertTrue(mock_logger.error.called)
