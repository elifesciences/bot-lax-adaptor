import requests_cache
import conf


def install_cache_requests():
    requests_cache.install_cache(**{
        'allowable_methods': ('GET', 'HEAD'),
        'cache_name': conf.REQUESTS_CACHE,
        'backend': 'sqlite',
        'fast_save': conf.ASYNC_CACHE_WRITES,
        'extension': '.sqlite3'})
