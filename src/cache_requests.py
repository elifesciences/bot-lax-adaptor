import requests_cache
import conf

def install_cache_requests():
    requests_cache.install_cache(**conf.REQUESTS_CACHE_CONFIG)

def clear_expired():
    "removes expired entries from requests_cache if installed. returns path to database regardless of installation"
    if hasattr(requests_cache.core.requests.Session(), 'remove_expired_responses'):
        requests_cache.core.remove_expired_responses()
    # path to database is used by 'clear-expired-requests-cache.sh' to then VACUUM db
    return conf.REQUESTS_CACHE_DB
