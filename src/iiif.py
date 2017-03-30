import requests, requests_cache
import logging
import conf
import utils
from main import pad_filename, iiiflink

LOG = logging.getLogger(__name__)
requests_cache.install_cache(**{
    'cache_name': conf.IIIF_CACHE,
    'backend': 'sqlite',
    'fast_save': True,
    'extension': '.sqlite3'})

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
    return pad_filename(msid, raw_link)

def iiifsource(msid, filename):
    source = {}
    source["mediaType"] = "image/jpeg"
    source["uri"] = iiiflink(msid, filename)+ '/full/full/0/default.jpg'
    source["filename"] = filename
    return source

def basic_info(msid, filename):
    info_data = iiif_info(msid, filename)
    source = iiifsource(msid, filename)
    width = iiif_width(info_data)
    height = iiif_height(info_data)
    return source, width, height

def iiif_info(msid, filename):
    context = {'msid': msid, 'iiif_filename': filename,
               'iiif_info_url': iiif_info_url(msid, filename)}

    try:
        resp = requests.get(iiif_info_url(msid, filename))
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
    except AssertionError:
        # clear cache, we don't want bad data hanging around
        clear_cache(msid, filename)
        raise

def iiif_width(info_data):
    # Return a default of 1 pixel if not found for now
    return info_data.get("width") if info_data.get("width") is not None else 1

def iiif_height(info_data):
    # Return a default of 1 pixel if not found for now
    return info_data.get("height") if info_data.get("height") is not None else 1

def clear_cache(msid, filename):
    requests_cache.core.get_cache().delete_url(iiif_info_url(msid, filename))
