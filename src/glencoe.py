import logging
import requests_cache
from cache_requests import install_cache_requests
import conf, utils
from utils import ensure, lmap, lfilter, sortdict
from collections import OrderedDict

LOG = logging.getLogger(__name__)

if conf.REQUESTS_CACHING:
    install_cache_requests()

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


SOURCES = OrderedDict([
    ('mp4', 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"'),
    ('webm', 'video/webm; codecs="vp8.0, vorbis"'),
    ('ogv', 'video/ogg; codecs="theora, vorbis"'),
])

def glencoe_url(msid):
    doi = "10.7554/eLife." + utils.pad_msid(msid)
    url = "https://movie-usa.glencoesoftware.com/metadata/" + doi
    return url

def validate_gc_data(gc_data):
    # we've had one case like this
    ensure(gc_data != {}, "glencoe returned successfully, but response is empty")

    # we also can't guarantee all of the sources will always be present
    known_sources = SOURCES.keys()
    for v_id, v_data in gc_data.items():

        available_sources = lfilter(lambda mtype: mtype + "_href" in v_data, known_sources)

        # fail if we have partial data
        msg = "number of available sources less than known sources for %r. missing: %s" % \
            (v_id, ", ".join(set(known_sources) - set(available_sources)))
        ensure(len(available_sources) == len(known_sources), msg)

def clear_cache(msid):
    requests_cache.core.get_cache().delete_url(glencoe_url(msid))

def metadata(msid):
    # 2018-10-19: it's now possible for glencoe to be queried about an article before media
    # has been deposited by elife-bot. only successful responses will be cached
    url = glencoe_url(msid)
    resp = utils.requests_get(url)
    context = {'msid': msid, 'glencoe-url': url, 'status-code': resp.status_code}

    if resp.status_code != 200:
        clear_cache(msid)

        if resp.status_code == 404:
            LOG.debug("article has no videos", extra=context)
            return {}

        msg = "unhandled status code from Glencoe"
        context["response"] = resp # TODO: object handling?
        LOG.error(msg, extra=context)
        raise ValueError("%s: %s" % (msg, resp.status_code))

    try:
        gc_data = sortdict(resp.json())
        validate_gc_data(gc_data)
        return gc_data
    except AssertionError:
        # clear cache, we don't want bad data hanging around
        clear_cache(msid)
        raise

def expand_videos(msid, video):
    gc_data = metadata(msid) # cached on first hit
    gc_id_str = ", ".join(gc_data.keys())

    v_id = video['id']
    ensure(gc_data, "glencoe doesn't know %r, it doesn't have any media")
    ensure(v_id in gc_data, "glencoe doesn't know %r, only %r" % (v_id, gc_id_str))

    video_data = gc_data[v_id]
    video_data = utils.subdict(video_data, ['jpg_href', 'width', 'height'])
    video_data = utils.renkeys(video_data, [('jpg_href', 'image')])

    func = lambda mtype: OrderedDict([
        ('mediaType', SOURCES[mtype]),
        ('uri', gc_data[v_id][mtype + "_href"])
    ])
    video_data['sources'] = lmap(func, SOURCES)
    video.update(video_data)

    del video['uri'] # returned by elife-tools, not part of spec

    # Add placeholder, the video thumbnail image
    video["placeholder"] = OrderedDict()
    video["placeholder"]["uri"] = video["image"].split('/')[-1]
    video["placeholder"]["alt"] = ""

    return video
