from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import redirect
from djangoldp.models import Model
from django.http import HttpResponse

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
        if request.method == 'OPTIONS':
            # Return an empty 200 response for OPTIONS requests
            # The CORS headers will be added by AllowRequestedCORSMiddleware later
            response = HttpResponse(status=200)
        else:
            response = self.get_response(request)

        response["Access-Control-Allow-Origin"] = request.headers.get('origin')
        response["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD"
        response["Access-Control-Allow-Headers"] = \
            getattr(settings, 'OIDC_ACCESS_CONTROL_ALLOW_HEADERS',
                    "authorization, Content-Type, if-match, accept, DPoP, cache-control, prefer")
        response["Access-Control-Expose-Headers"] = "Location, User"
        response["Access-Control-Allow-Credentials"] = 'true'

        return response


class OptionsResponseMiddleware:
    """Middleware that returns a 200 response for OPTIONS requests.
    
    This should be placed BEFORE the AllowRequestedCORSMiddleware in the stack
    to ensure OPTIONS requests receive proper CORS headers.
    
    This middleware is not enabled by default. To use it, add
    'djangoldp.middleware.OptionsResponseMiddleware' to your MIDDLEWARE setting
    before 'djangoldp.middleware.AllowRequestedCORSMiddleware'.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'OPTIONS':
            # Return an empty 200 response for OPTIONS requests
            # The CORS headers will be added by AllowRequestedCORSMiddleware later
            return HttpResponse(status=200)
        
        # For all other requests, proceed as normal
        return self.get_response(request)