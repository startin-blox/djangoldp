from django.conf import settings
from django.http import JsonResponse
from django.views import View

from djangoldp.models import SiteSetting

from rest_framework import status


class InstanceWebIDView(View):
    def get(self, request, *args, **kwargs):
        return self.on_request(request)

    def on_request(self, request):
        # Generate a jsonld response with the context and a @graph containing all the models in the system
        response = {
            '@context': settings.LDP_RDF_CONTEXT,
            '@graph': []
        }

        # Also add an entry for the main index of the platform located at uri /indexes/
        typeIndexLocation = getattr(
            settings, 'TYPE_INDEX_LOCATION', '/profile/publicTypeIndex')

        response['@graph'] = [
            {
                "@id": request.build_absolute_uri(f"/profile"),
                "@type": "foaf:PersonalProfileDocument",
                "foaf:primaryTopic": request.build_absolute_uri(f"/profile#me"),
            }
        ]

        try:
            config = SiteSetting.get_solo()
        except SiteSetting.DoesNotExist:
            config = SiteSetting(title="Default Title", description="", terms_url="")

        response["@graph"].append({
            "@id": request.build_absolute_uri("/profile#me"),
            "@type": ["sib:HublApplication", "solid:Application", "foaf:Agent"],
            "title": config.title,
            "description": config.description,
            "termsAndConditions": config.terms_url,
            "solid:publicTypeIndex": request.build_absolute_uri(typeIndexLocation),
        })

        return JsonResponse(response,
                        content_type='application/ld+json',
                        status=status.HTTP_200_OK,
                        headers={
                            'Access-Control-Allow-Origin': '*',
                            'Cache-Control': 'public, max-age=3600',
                        })
