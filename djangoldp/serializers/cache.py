from django.conf import settings

# defaults for various DjangoLDP settings (see documentation)
MAX_RECORDS_SERIALIZER_CACHE = getattr(settings, 'MAX_RECORDS_SERIALIZER_CACHE', 10000)


class InMemoryCache:
    def __init__(self):
        self.cache = {}

    def reset(self):
        self.cache = {}

    def has(self, cache_key, container_urlid=None, vary=None):
        return cache_key in self.cache and \
               (container_urlid is None or container_urlid in self.cache[cache_key]) and \
               (vary is None or vary in self.cache[cache_key][container_urlid])

    def get(self, cache_key, container_urlid, vary):
        if self.has(cache_key, container_urlid, vary):
            return self.cache[cache_key][container_urlid][vary]['value']
        else:
            return None

    def set(self, cache_key, container_urlid, vary, value):
        if len(self.cache.keys()) > MAX_RECORDS_SERIALIZER_CACHE:
            self.reset()

        if cache_key not in self.cache:
            self.cache[cache_key] = {}
        if container_urlid not in self.cache[cache_key]:
            self.cache[cache_key][container_urlid] = {}
        self.cache[cache_key][container_urlid][vary] = {'value': value}

    def invalidate(self, cache_key, container_urlid=None, vary=None):
        # can clear cache_key -> container_urlid -> vary, cache_key -> container_urlid or cache_key
        if container_urlid is not None:
            if vary is not None:
                self.cache[cache_key][container_urlid].pop(vary, None)
            else:
                self.cache[cache_key].pop(container_urlid, None)
        else:
            self.cache.pop(cache_key, None)


GLOBAL_SERIALIZER_CACHE = InMemoryCache()
