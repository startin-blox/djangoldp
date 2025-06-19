from django.apps import apps
from django.conf import settings

from djangoldp.views.ldp_api import LDPAPIView

from rest_framework.response import Response
from rest_framework import status

import logging

logger = logging.getLogger(__name__)

class InstanceRootContainerView(LDPAPIView):
    def get(self, request, *args, **kwargs):
        return self.on_request(request)

    def on_request(self, request):
        try:
          # Generate a jsonld response with the context and a @graph containing all the models in the system
          response = {
              '@context': settings.LDP_RDF_CONTEXT,
              '@id': request.build_absolute_uri(),
              '@type': 'ldp:Container',
              'ldp:contains': []
          }

          # Iterate over all the apps in the system and their models to add them to the @graph
          for app in apps.get_app_configs():
              app_models = [model.__name__ for model in app.get_models()]
              for model_name in app_models:
                  model = apps.get_model(app.label, model_name)
                  if (model._meta ):
                      if (hasattr(model._meta, 'rdf_type') and hasattr(model, 'get_container_path')):
                          response['ldp:contains'].append({
                              "@id": request.build_absolute_uri(model.get_container_path()),
                              "@type": "ldp:Container"
                          })
          response = Response(response,
                          content_type='application/ld+json',
                          headers={
                            'Access-Control-Allow-Origin': '*',
                            'Cache-Control': 'public, max-age=3600',
                          })

          return response
        except Exception as e:
            logger.exception("Error building LDP container response")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

