import os
import requests
import requests_cache
from cache_requests import install_cache_requests
import conf, utils

LOG = conf.multiprocess_log(conf.IIIF_LOG_PATH, __name__)

if conf.REQUESTS_CACHING:
    install_cache_requests()

'''
iiif_resp = {
    "profile": [
        "http://iiif.io/api/image/2/level2.json", {
            "supports": ["canonicalLinkHeader", "profileLinkHeader", "mirroring", "rotationArbitrary", "regionSquare", "sizeAboveFull"],
            "qualities": ["default", "color", "gray", "bitonal"],
            "formats": ["jpg", "png", "gif", "webp"]
        }
    ],
    "protocol": "http://iiif.io/api/image",
    "sizes": [],
    "height": 2803,
    "width": 2386,
    "@context": "http://iiif.io/api/image/2/context.json",
    "@id": "https://iiif.elifesciences.org/lax/24125%2Felife-24125-fig1-v2.jpg"
}
'''

def iiif_info_url(msid, filename):
    kwargs = {
        'padded-msid': utils.pad_msid(msid),
        'fname': filename
    }
    raw_link = (conf.IIIF % kwargs)
    return utils.pad_filename(msid, raw_link)

def basic_info(msid, filename):
    if 'FORCED_IIIF' in os.environ and int(os.environ['FORCED_IIIF']):
        return 1, 1
    info_data = iiif_info(msid, filename)
    return info_data.get("width"), info_data.get("height")

def iiif_info(msid, filename):
    context = {
        'msid': msid,
        'iiif_filename': filename,
        'iiif_info_url': iiif_info_url(msid, filename)
    }
    try:
        url = iiif_info_url(msid, filename)
        LOG.info("Loading IIIF info URL: %s", url)
        resp = utils.requests_get(url)
    except requests.ConnectionError:
        LOG.debug("IIIF request failed", extra=context)
        return {}

    context['status-code'] = resp.status_code

    if resp.status_code == 404:
        LOG.debug("IIIF image not found", extra=context)
        return {}

    elif resp.status_code != 200:
        msg = "unhandled status code from IIIF"
        LOG.warning(msg, extra=context)
        raise ValueError(msg + ": %s" % resp.status_code)

    try:
        info_data = utils.sortdict(resp.json())
        return info_data
    except BaseException:
        # clear cache, we don't want bad data hanging around
        clear_cache(msid, filename)
        raise

def clear_cache(msid, filename):
    requests_cache.get_cache().delete_url(iiif_info_url(msid, filename))
