import requests, requests_cache
import logging
#from os.path import join
import conf

LOG = logging.getLogger(__name__)
requests_cache.install_cache(**{
    'cache_name': conf.GLENCOE_CACHE,
    'backend': 'sqlite',
    'fast_save': True,
    'extension': '.sqlite3'})

'''
glencoe_resp = {
    "media1": {
        "source_href": "https://static-movie-usa.glencoesoftware.com/source/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.wmv",
        "doi": "10.7554/eLife.00569.019",
        "flv_href": "https://static-movie-usa.glencoesoftware.com/flv/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.flv",
        "uuid": "55f163d5-f0d9-415b-8ae8-ec75ed83b026",
        "title": "",
        "video_id": "media1",
        "solo_href": "https://movie-usa.glencoesoftware.com/video/10.7554/eLife.00569/media1",
        "height": 480,
        "ogv_href": "https://static-movie-usa.glencoesoftware.com/ogv/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.ogv",
        "width": 640,
        "href": "elife-00569-media1.wmv",
        "webm_href": "https://static-movie-usa.glencoesoftware.com/webm/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.webm",
        "jpg_href": "https://static-movie-usa.glencoesoftware.com/jpg/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.jpg",
        "duration": 54.487,
        "mp4_href": "https://static-movie-usa.glencoesoftware.com/mp4/10.7554/659/0f10378e095dde7aaf579af504c4bfdc6fb86550/elife-00569-media1.mp4",
        "legend": "",
        "size": 20452423
    }
}
'''

def metadata(msid):
    padded_msid = str(msid).zfill(5)
    doi = "10.7554/eLife." + padded_msid
    url = "https://movie-usa.glencoesoftware.com/metadata/" + doi

    resp = requests.get(url)

    context = {'msid': msid, 'url': url, 'status-code': resp.status_code}
    if resp.status_code == 404:
        LOG.debug("article has no videos", extra=context)
        return {}

    elif resp.status_code != 200:
        msg = "unhandled status code from Glencoe"
        LOG.warn(msg, extra=context)
        raise ValueError(msg + ": %s" % resp.status_code)

    return resp.json()
