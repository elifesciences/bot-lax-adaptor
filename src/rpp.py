from datetime import datetime
import requests
import requests_cache
from cache_requests import install_cache_requests
import conf, utils

LOG = conf.multiprocess_log(conf.IIIF_LOG_PATH, __name__)

if conf.REQUESTS_CACHING:
    install_cache_requests()

def before_inception(pubdate):
    "returns `True` if given `pubdate` is before the inception of reviewed-preprints."
    utils.ensure(isinstance(pubdate, datetime), "given pubdate must be a datetime instance")
    return pubdate < conf.RPP_INCEPTION

def rpp_url(msid):
    return f"{conf.API_URL}/reviewed-preprints/{msid}"

def clear_cache(msid):
    "removes a /reviewed-preprint from the requests cache, if requests caching is turned on."
    if conf.REQUESTS_CACHING:
        requests_cache.core.get_cache().delete_url(rpp_url(msid))

def snippet(msid):
    if not msid:
        return
    context = {
        'msid': msid,
    }
    try:
        url = rpp_url(msid)
        LOG.info("Loading URL: %s", url)
        resp = utils.requests_get(url)
    except requests.RequestException as re:
        LOG.debug("request failed fetching RPP", extra=context, exc_info=re)
        return

    context['status-code'] = resp.status_code

    if resp.status_code == 404:
        LOG.debug("RPP not found", extra=context)
        return

    if resp.status_code != 200:
        msg = "unhandled status code fetching RPP"
        LOG.warning(msg, extra=context)
        raise ValueError(msg + ": %s" % resp.status_code)

    try:
        rpp_data = utils.sortdict(resp.json())

        if 'indexContent' in rpp_data:
            del rpp_data['indexContent']

        rpp_data['type'] = 'reviewed-preprint'

        return rpp_data
    except BaseException:
        # clear cache, we don't want bad data hanging around
        clear_cache(msid)
        raise
