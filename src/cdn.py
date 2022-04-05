import logging
import http
import requests

LOG = logging.getLogger(__name__)

def url_exists(url, msid=None):
    context = {'msid': msid, 'url': url}

    try:
        resp = http.requests_head(url)
    except requests.ConnectionError:
        LOG.debug("CDN request failed", extra=context)
        return None

    status_code = resp['status_code']

    context['status-code'] = status_code

    if resp['status_code'] == 200:
        return url

    if resp['status_code'] == 404:
        LOG.debug("CDN url not found", extra=context)
        return

    msg = "unhandled status code from CDN"
    LOG.warning(msg, extra=context)
    raise ValueError("%s: %s" % (msg, status_code))
