import logging

from rest_framework.views import APIView

from djangoldp.utils import is_authenticated_user
from djangoldp.views.commons import NoCSRFAuthentication, JSONLDRenderer

logger = logging.getLogger('djangoldp')


class LDPAPIView(APIView):
    '''extends rest framework APIView to support Solid standards'''
    authentication_classes = (NoCSRFAuthentication,)
    renderer_classes = (JSONLDRenderer,)

    def dispatch(self, request, *args, **kwargs):
        '''overriden dispatch method to append some custom headers'''
        response = super().dispatch(request, *args, **kwargs)

        if response.status_code in [201, 200] and getattr(response, 'data') and isinstance(response.data, dict) and '@id' in response.data:
            response["Location"] = str(response.data['@id'])
        else:
            pass

        if is_authenticated_user(request.user):
            try:
                response['User'] = request.user.urlid
            except AttributeError:
                pass

        return response
