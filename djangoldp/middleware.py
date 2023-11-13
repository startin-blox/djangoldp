from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import redirect
from djangoldp.models import Model


class AllowOnlySiteUrl:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if(url_has_allowed_host_and_scheme(request.get_raw_uri(), allowed_hosts=settings.SITE_URL) or response.status_code != 200):
            return response
        else:
            return redirect('{}{}'.format(settings.SITE_URL, request.path), permanent=True)


class AllowRequestedCORSMiddleware:
    '''A CORS Middleware which allows the domains requested by the request'''
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response["Access-Control-Allow-Origin"] = request.headers.get('origin')
        response["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD"
        response["Access-Control-Allow-Headers"] = \
            getattr(settings, 'OIDC_ACCESS_CONTROL_ALLOW_HEADERS',
                    "authorization, Content-Type, if-match, accept, DPoP, cache-control, prefer")
        response["Access-Control-Expose-Headers"] = "Location, User"
        response["Access-Control-Allow-Credentials"] = 'true'

        return response