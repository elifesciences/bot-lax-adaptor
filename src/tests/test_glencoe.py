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

    def test_metadata_unhandled_response_code(self):
        "metadata logs the body of the response on an unhandled response"
        with patch('utils.requests_get') as mock:
            with patch.object(glencoe, 'LOG') as mock_logger:
                mock.return_value.status_code = 418
                self.assertRaises(ValueError, glencoe.metadata, 1)
                self.assertTrue(mock_logger.error.called)
