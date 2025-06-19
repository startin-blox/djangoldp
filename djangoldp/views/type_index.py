from django.apps import apps
from django.conf import settings

from djangoldp.views.ldp_api import LDPAPIView

from rest_framework.response import Response


class PublicTypeIndexView(LDPAPIView):
    def get(self, request, *args, **kwargs):
        return self.on_request(request)

    def on_request(self, request):
        # Generate a jsonld response with the context and a @graph containing all the models in the system
        response = {
            '@context': settings.LDP_RDF_CONTEXT,
            '@graph': [{
              "@id": request.build_absolute_uri('publicTypeIndex'),
              "@type": "solid:TypeIndex"
            }]
        }

        # Iterate over all the apps and add their indexes entry-points to the graph
        for app in apps.get_app_configs():
            app_models = [model.__name__ for model in app.get_models()]
            for model_name in app_models:
                model = apps.get_model(app.label, model_name)
                if (model._meta and hasattr(model._meta, 'indexed_fields')):
                    if (hasattr(model._meta, 'rdf_type') and hasattr(model, 'get_container_path')):
                        response['@graph'].append({
                            "@type": "solid:TypeIndexRegistration",
                            "solid:forClass": "idx:Index",
                            '@id': request.build_absolute_uri(f"publicTypeIndex#indexes-{model.get_container_path()[1:-1]}"),
                            "solid:instance": request.build_absolute_uri('/indexes' + model.get_container_path() + 'index')
                        })

        # Iterate over all the apps in the system and their models to add them to the @graph
        for app in apps.get_app_configs():
            app_models = [model.__name__ for model in app.get_models()]
            for model_name in app_models:
                model = apps.get_model(app.label, model_name)
                if (model._meta ):
                    if (hasattr(model._meta, 'rdf_type') and hasattr(model, 'get_container_path')):
                        response['@graph'].append({
                            "@id": request.build_absolute_uri(f"publicTypeIndex#{model.get_container_path()[1:-1]}"),
                            "@type": "solid:TypeIndexRegistration",
                            "solid:forClass": model._meta.rdf_type,
                            "solid:instanceContainer": request.build_absolute_uri(model.get_container_path())
                        })

        return Response(response,
                        content_type='application/ld+json',
                        headers={
                          'Access-Control-Allow-Origin': '*',
                          'Cache-Control': 'public, max-age=3600',
                        })
