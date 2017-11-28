import logging
import os

import requests
import requests_cache

from src.cache_requests import install_cache_requests
import src.conf as conf
import src.utils as utils

LOG = logging.getLogger(__name__)

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
    "@id": "https://prod--iiif.elifesciences.org/lax%3A24125%2Felife-24125-fig1-v2.jpg"
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
    info_data = iiif_info(msid, filename)
    width = iiif_width(info_data)
    height = iiif_height(info_data)
    if 'FORCED_IIIF' in os.environ and int(os.environ['FORCED_IIIF']):
        return 1, 1
    return width, height

def iiif_info(msid, filename):
    context = {
        'msid': msid,
        'iiif_filename': filename,
        'iiif_info_url': iiif_info_url(msid, filename)
    }
    try:
        resp = utils.requests_get(iiif_info_url(msid, filename))
    except requests.ConnectionError:
        LOG.debug("IIIF request failed", extra=context)
        return {}

    context['status-code'] = resp.status_code

    if resp.status_code == 404:
        LOG.debug("IIIF image not found", extra=context)
        return {}

    elif resp.status_code != 200:
        msg = "unhandled status code from IIIF"
        LOG.warn(msg, extra=context)
        raise ValueError(msg + ": %s" % resp.status_code)

    try:
        info_data = resp.json()
        return info_data
    except BaseException:
        # clear cache, we don't want bad data hanging around
        clear_cache(msid, filename)
        raise

def iiif_width(info_data):
    return info_data.get("width")

def iiif_height(info_data):
    return info_data.get("height")

def clear_cache(msid, filename):
    requests_cache.core.get_cache().delete_url(iiif_info_url(msid, filename))
