import logging
from collections import OrderedDict

from django.conf import settings
from pyld import jsonld
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer, BaseRenderer
from rest_framework.parsers import BaseParser
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS
import json

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


class TurtleRenderer(BaseRenderer):
    """
    Renderer which serializes to Turtle format.
    """
    media_type = 'text/turtle'
    format = 'turtle'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render JSON-LD data to Turtle format using rdflib.
        """
        if data is None:
            return b''

        # Create RDF graph
        g = Graph()

        # Parse JSON-LD into graph
        try:
            json_str = json.dumps(data)
            g.parse(data=json_str, format='json-ld')
            # Serialize graph to Turtle - always return bytes
            turtle_str = g.serialize(format='turtle')
            if isinstance(turtle_str, str):
                return turtle_str.encode('utf-8')
            return turtle_str
        except Exception as e:
            # Log the error for debugging
            logger.warning(f"Failed to parse JSON-LD to Turtle: {str(e)}, falling back to simple converter")
            try:
                # Fallback: manual conversion for simple cases
                fallback_result = self.simple_jsonld_to_turtle(data)
                if isinstance(fallback_result, str):
                    return fallback_result.encode('utf-8')
                return fallback_result
            except Exception as fallback_error:
                logger.error(f"Fallback Turtle serialization failed: {str(fallback_error)}")
                # Return minimal valid Turtle on complete failure
                return b'# Serialization error\n'

    def simple_jsonld_to_turtle(self, data):
        """
        Simple fallback converter for basic JSON-LD to Turtle.
        Enhanced with better namespace handling.
        """
        g = Graph()

        # Define common namespaces
        LDP = Namespace("http://www.w3.org/ns/ldp#")
        FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        DCTERMS = Namespace("http://purl.org/dc/terms/")

        # Bind namespaces for better output
        g.bind("ldp", LDP)
        g.bind("foaf", FOAF)
        g.bind("dcterms", DCTERMS)
        g.bind("rdf", RDF)
        g.bind("rdfs", RDFS)

        if isinstance(data, dict):
            subject_uri = data.get('@id', '_:blank')
            subject = URIRef(subject_uri) if subject_uri != '_:blank' else URIRef('urn:blank')

            # Add type
            if '@type' in data:
                types = data['@type'] if isinstance(data['@type'], list) else [data['@type']]
                for type_uri in types:
                    if type_uri.startswith('ldp:'):
                        g.add((subject, RDF.type, LDP[type_uri[4:]]))
                    elif type_uri.startswith('foaf:'):
                        g.add((subject, RDF.type, FOAF[type_uri[5:]]))
                    else:
                        g.add((subject, RDF.type, URIRef(type_uri)))

            # Add properties
            for key, value in data.items():
                if key not in ['@id', '@type', '@context']:
                    # Handle containers
                    if key == 'ldp:contains' and isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict) and '@id' in item:
                                g.add((subject, LDP.contains, URIRef(item['@id'])))
                    # Handle simple literals
                    elif isinstance(value, (str, int, float, bool)):
                        predicate = URIRef(key) if not key.startswith('ldp:') else LDP[key[4:]]
                        g.add((subject, predicate, Literal(value)))
                    # Handle nested objects with @id
                    elif isinstance(value, dict) and '@id' in value:
                        predicate = URIRef(key) if not key.startswith('ldp:') else LDP[key[4:]]
                        g.add((subject, predicate, URIRef(value['@id'])))

        turtle_result = g.serialize(format='turtle')
        if isinstance(turtle_result, bytes):
            return turtle_result
        return turtle_result.encode('utf-8') if isinstance(turtle_result, str) else turtle_result


class TurtleParser(BaseParser):
    """
    Parser which handles Turtle format.
    """
    media_type = 'text/turtle'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parse Turtle input to JSON-LD and apply context.
        """
        try:
            turtle_data = stream.read().decode('utf-8')
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode Turtle data: {str(e)}")
            raise ParseError(f"Invalid UTF-8 encoding in Turtle data: {str(e)}")

        if not turtle_data or not turtle_data.strip():
            raise ParseError("Empty Turtle data received")

        # Parse Turtle into RDF graph
        g = Graph()
        try:
            g.parse(data=turtle_data, format='turtle')
        except Exception as e:
            logger.error(f"Failed to parse Turtle data: {str(e)}")
            raise ParseError(f"Invalid Turtle syntax: {str(e)}")

        # Convert to JSON-LD
        try:
            jsonld_str = g.serialize(format='json-ld')
            jsonld_data = json.loads(jsonld_str)
        except Exception as e:
            logger.error(f"Failed to convert Turtle to JSON-LD: {str(e)}")
            raise ParseError(f"Failed to convert Turtle to JSON-LD: {str(e)}")

        # Apply context like JSONLDParser does
        try:
            return jsonld.compact(jsonld_data, ctx=settings.LDP_RDF_CONTEXT)
        except jsonld.JsonLdError as e:
            logger.error(f"Failed to apply JSON-LD context: {str(e.cause)}")
            raise ParseError(f"Failed to apply context: {str(e.cause)}")
        except Exception as e:
            logger.error(f"Unexpected error applying context: {str(e)}")
            raise ParseError(f"Failed to apply context: {str(e)}")

