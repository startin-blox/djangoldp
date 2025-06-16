import logging
from collections import OrderedDict

from django.conf import settings
from pyld import jsonld
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

logger = logging.getLogger('djangoldp')


# renders into JSONLD format by applying context to the data
# https://github.com/digitalbazaar/pyld
class JSONLDRenderer(JSONRenderer):
    media_type = 'application/ld+json'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, dict):
            context = data.get("@context")
            if isinstance(context, list):
                context_value = [settings.LDP_RDF_CONTEXT] + context
            elif isinstance(context, str) or isinstance(context, dict):
                context_value = [settings.LDP_RDF_CONTEXT, context]
            else:
                context_value = settings.LDP_RDF_CONTEXT

            ordered_data = OrderedDict()
            ordered_data["@context"] = context_value
            for key, value in data.items():
                if key != "@context":
                    ordered_data[key] = value
            data = ordered_data

        return super(JSONLDRenderer, self).render(data, accepted_media_type, renderer_context)


# https://github.com/digitalbazaar/pyld
class JSONLDParser(JSONParser):
    #TODO: It current only works with pyld 1.0. We need to check our support of JSON-LD
    media_type = 'application/ld+json'

    def parse(self, stream, media_type=None, parser_context=None):
        data = super(JSONLDParser, self).parse(stream, media_type, parser_context)
        # compact applies the context to the data and makes it a format which is easier to work with
        # see: http://json-ld.org/spec/latest/json-ld/#compacted-document-form
        try:
            return jsonld.compact(data, ctx=settings.LDP_RDF_CONTEXT)
        except jsonld.JsonLdError as e:
            raise ParseError(str(e.cause))


# an authentication class which exempts CSRF authentication
class NoCSRFAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return

