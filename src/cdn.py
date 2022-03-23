import logging

import requests
import requests_cache

from cache_requests import install_cache_requests
import conf

LOG = logging.getLogger(__name__)

if conf.REQUESTS_CACHING:
    install_cache_requests()

def clear_cache(url):
    conf.REQUESTS_CACHING and requests_cache.get_cache().delete_url(url)

def url_exists(url, msid=None):
    context = {'msid': msid, 'url': url}

    try:
        resp = requests.head(url)
    except requests.ConnectionError:
        LOG.debug("CDN request failed", extra=context)
        return None

    context['status-code'] = resp.status_code

    if resp.status_code == 200:
        return url

    # non-200 response
    # a request outside of the regular workflow may have been made too early
    # a subsequent request would return the 'not found' response
    # https://github.com/elifesciences/issues/issues/4458
    clear_cache(url)

    if resp.status_code == 404:
        LOG.debug("CDN url not found", extra=context)
    else:
        msg = "unhandled status code from CDN"
        LOG.warning(msg, extra=context)
        raise ValueError(msg + ": %s" % resp.status_code)
