from datetime import datetime
import requests
import requests_cache
from cache_requests import install_cache_requests
import conf, utils

LOG = conf.multiprocess_log(conf.IIIF_LOG_PATH, __name__)

if conf.REQUESTS_CACHING:
    install_cache_requests()

def before_inception(pubdate):
    "returns `True` if given `pubdate` datetime is before EPP's inception."
    utils.ensure(isinstance(pubdate, datetime), "given pubdate must be a datetime instance")
    return pubdate < conf.EPP_INCEPTION

def epp_url(msid):
    return f"{conf.API_URL}/reviewed-preprints/{msid}"

def clear_cache(msid):
    requests_cache.core.get_cache().delete_url(epp_url(msid))

def snippet(msid):
    if not msid:
        return
    context = {
        'msid': msid,
    }
    try:
        url = epp_url(msid)
        LOG.info("Loading EPP URL: %s", url)
        resp = utils.requests_get(url)
    except requests.RequestException as re:
        LOG.debug("EPP request failed", extra=context, exc_info=re)
        return

    context['status-code'] = resp.status_code

    if resp.status_code == 404:
        LOG.debug("EPP not found", extra=context)
        return

    if resp.status_code != 200:
        msg = "unhandled status code from EPP"
        LOG.warning(msg, extra=context)
        raise ValueError(msg + ": %s" % resp.status_code)

    try:
        epp_data = utils.sortdict(resp.json())

        if 'indexContent' in epp_data:
            del epp_data['indexContent']

        epp_data['type'] = 'reviewed-preprint'

        utils.validate([epp_data], conf.RELATED_SCHEMA)

        return epp_data
    except BaseException:
        # clear cache, we don't want bad data hanging around
        clear_cache(msid)
        raise
