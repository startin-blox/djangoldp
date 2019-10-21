from django.conf import settings
from django.utils.http import is_safe_url
from django.shortcuts import redirect


class AllowOnlySiteUrl:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if(is_safe_url(request.get_raw_uri(), allowed_hosts=settings.SITE_URL)):
            response = self.get_response(request)
            return response
        else:
            return redirect('{}{}'.format(settings.SITE_URL, request.path))
