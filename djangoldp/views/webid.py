from django.conf import settings

from djangoldp.models import SiteSetting
from djangoldp.views.ldp_api import LDPAPIView

from rest_framework import status
from rest_framework.response import Response


class InstanceWebIDView(LDPAPIView):
    def get(self, request, *args, **kwargs):
        return self.on_request(request)

    def get_profile_data(self, request):
        # Also add an entry for the main index of the platform located at uri /indexes/
        typeIndexLocation = getattr(
            settings, "TYPE_INDEX_LOCATION", "/profile/publicTypeIndex"
        )

        try:
            config = SiteSetting.get_solo()
        except SiteSetting.DoesNotExist:
            config = SiteSetting(title="Default Title", description="", terms_url="")

        return {
            "@id": request.build_absolute_uri("/profile#me"),
            "@type": ["sib:HublApplication", "solid:Application", "foaf:Agent"],
            "dcterms:title": config.title,
            "dcterms:description": config.description,
            "dcterms:license": config.terms_url,
            "solid:publicTypeIndex": request.build_absolute_uri(typeIndexLocation),
        }

    def get_full_webid_data(self, request):
        # Generate a jsonld response with the context and a @graph containing all the models in the system
        response = {"@graph": []}

        response["@graph"] = [
            {
                "@id": request.build_absolute_uri("/profile"),
                "@type": "foaf:PersonalProfileDocument",
                "foaf:primaryTopic": request.build_absolute_uri("/profile#me"),
            },
            self.get_profile_data(request),
        ]
        return response

    def on_request(self, request):
        return Response(
            self.get_full_webid_data(request),
            content_type="application/ld+json",
            status=status.HTTP_200_OK,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
            },
        )
