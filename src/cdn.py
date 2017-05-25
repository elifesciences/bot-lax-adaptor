import requests, requests_cache
from cache_requests import install_cache_requests
import logging
import conf

LOG = logging.getLogger(__name__)

if conf.REQUESTS_CACHING:
    install_cache_requests()

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
    elif resp.status_code == 404:
        LOG.debug("CDN url not found", extra=context)
    else:
        msg = "unhandled status code from CDN"
        LOG.warn(msg, extra=context)
        raise ValueError(msg + ": %s" % resp.status_code)

    return None

def clear_cache(url):
    requests_cache.core.get_cache().delete_url(url)
