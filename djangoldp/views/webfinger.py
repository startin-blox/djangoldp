import logging

from django.http import JsonResponse
from django.views import View

from djangoldp.endpoints.webfinger import WebFingerEndpoint, WebFingerError

logger = logging.getLogger('djangoldp')


class WebFingerView(View):
    endpoint_class = WebFingerEndpoint

    def get(self, request, *args, **kwargs):
        return self.on_request(request)

    def on_request(self, request):
        endpoint = self.endpoint_class(request)
        try:
            endpoint.validate_params()

            return JsonResponse(endpoint.response())

        except WebFingerError as error:
            return JsonResponse(error.create_dict(), status=400)

    def post(self, request, *args, **kwargs):
        return self.on_request(request)