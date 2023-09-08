import pytest
from unittest import mock
import datetime
import rpp

def test_before_inception():
    inception = datetime.datetime(year=2001, month=1, day=1)
    with mock.patch('conf.RPP_INCEPTION', inception):
        assert not rpp.before_inception(datetime.datetime(year=2001, month=1, day=1))
        assert rpp.before_inception(datetime.datetime(year=2000, month=12, day=31))

def test_rpp_url():
    with mock.patch("conf.API_URL", "http://example.org"):
        expected = "http://example.org/reviewed-preprints/1234"
        actual = rpp.rpp_url(1234)
        assert actual == expected

def test_snippet():
    expected = {
        'foo': 'bar', # whatever is returned is passed through ...
        # 'indexContent': ..., # ... except indexContent, which we drop.
        'type': 'reviewed-preprint' # 'type' is added.
    }
    fixture = {
        'foo': 'bar',
        'indexContent': {'to': {'be': 'dropped'}}
    }
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json = lambda: fixture
    with mock.patch("utils.requests_get", return_value=mock_response):
        resp = rpp.snippet(1234)
        assert resp == expected

def test_snippet__none_cases():
    "`snippet` will return `None` under certain conditions"
    assert rpp.snippet(None) is None
    assert rpp.snippet(0) is None
    assert rpp.snippet({}) is None
    mock_response = mock.Mock()
    mock_response.status_code = 404
    with mock.patch("utils.requests_get", return_value=mock_response):
        assert rpp.snippet(1234) is None

def test_snippet__fail_cases():
    "`snippet` will raise exceptions under certain conditions"
    mock_response = mock.Mock()
    mock_response.status_code = 500 # api endpoint is down, internal server error
    with mock.patch("utils.requests_get", return_value=mock_response):
        with pytest.raises(ValueError):
            rpp.snippet(1234)
