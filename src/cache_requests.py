import requests_cache
import conf

def install_cache_requests():
    requests_cache.install_cache(**{
        'allowable_methods': ('GET', 'HEAD'),
        'cache_name': conf.REQUESTS_CACHE,
        'backend': 'sqlite',
        'fast_save': conf.ASYNC_CACHE_WRITES,
        'extension': '.sqlite3'})

def create_key(prepared_request):
    return requests_cache.core.get_cache().create_key(prepared_request)
