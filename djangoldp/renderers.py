"""
DjangoLDP Renderers for content negotiation.

Provides renderers for:
- JSON-LD (application/ld+json)
- Turtle (text/turtle)
"""

import json
import logging
from collections import OrderedDict

from django.conf import settings
from pyld import jsonld
from rest_framework.renderers import JSONRenderer, BaseRenderer
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS

logger = logging.getLogger('djangoldp')


class JSONLDRenderer(JSONRenderer):
    """
    Renders data into JSON-LD format by applying the configured context.

    Uses pyld library for JSON-LD processing: https://github.com/digitalbazaar/pyld
    """
    media_type = 'application/ld+json'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render data to JSON-LD by ensuring proper @context.

        Merges the LDP_RDF_CONTEXT from settings with any existing @context in the data.
        """
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


class TurtleRenderer(BaseRenderer):
    """
    Renderer which serializes JSON-LD data to Turtle format using rdflib.

    Turtle (Terse RDF Triple Language) is a compact RDF serialization format.
    See: https://www.w3.org/TR/turtle/
    """
    media_type = 'text/turtle'
    format = 'turtle'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render JSON-LD data to Turtle format using rdflib.

        Tries JSON-LD expansion first to include nested resources, but falls back
        to direct parsing if expansion fails (e.g., network timeout on @context fetch).

        Falls back to a simple converter if rdflib parsing fails entirely.
        Always returns bytes (UTF-8 encoded).
        """
        if data is None:
            return b''

        # Create RDF graph
        g = Graph()

        # Strategy 1: Try expansion to include all nested resources
        try:
            # Expand JSON-LD to include all nested resources as triples
            # This converts embedded objects into separate resource descriptions
            # Set a timeout to avoid hanging on @context URL fetches
            logger.debug("Attempting JSON-LD expansion for Turtle rendering")

            # Configure jsonld expansion with timeout (2 seconds)
            document_loader = jsonld.requests_document_loader(timeout=2.0)
            options = {
                'documentLoader': document_loader
            }
            expanded = jsonld.expand(data, options)
            logger.debug(f"Expansion successful, expanded data has {len(expanded)} top-level items")

            # Check if expansion actually worked (expanded data should not have prefixed terms)
            expanded_str = json.dumps(expanded)
            if 'ldp:' in expanded_str or 'foaf:' in expanded_str or '@context' in expanded_str:
                # Expansion failed - data still has prefixes or context
                logger.warning("Expansion did not resolve all prefixes - @context fetch likely failed")
                raise Exception("Incomplete expansion - prefixes still present")

            # Parse the expanded JSON-LD into RDF graph
            # Now all nested resource properties become triples
            g.parse(data=expanded_str, format='json-ld')
            logger.debug(f"Parsed expanded JSON-LD into graph with {len(g)} triples")

            # Check if we got meaningful data
            if len(g) > 0:
                # Serialize graph to Turtle - always return bytes
                turtle_str = g.serialize(format='turtle')
                if isinstance(turtle_str, str):
                    return turtle_str.encode('utf-8')
                return turtle_str
            else:
                # Expansion produced empty graph - try direct parsing
                raise Exception("Expansion produced empty graph")

        except Exception as expansion_error:
            # Expansion failed (e.g., @context URL timeout) - try direct parsing
            logger.warning(f"JSON-LD expansion failed ({str(expansion_error)}), trying direct parse")

            # Strategy 2: Try direct parsing without expansion
            try:
                json_str = json.dumps(data)
                g.parse(data=json_str, format='json-ld')

                if len(g) > 0:
                    turtle_str = g.serialize(format='turtle')
                    if isinstance(turtle_str, str):
                        return turtle_str.encode('utf-8')
                    return turtle_str
                else:
                    raise Exception("Direct parsing produced empty graph")

            except Exception as parse_error:
                # Both expansion and direct parsing failed
                logger.warning(f"Direct JSON-LD parse also failed ({str(parse_error)}), using simple converter")

                # Strategy 3: Fallback to simple manual conversion
                try:
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

        Handles common LDP patterns when full rdflib parsing fails.
        Enhanced with better namespace handling and recursive nested resource processing.
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

        def add_resource_triples(resource_data, graph):
            """Recursively add resource and nested resources to graph."""
            if not isinstance(resource_data, dict):
                return

            subject_uri = resource_data.get('@id', '_:blank')
            if subject_uri == '_:blank':
                return  # Skip blank nodes in simple converter

            subject = URIRef(subject_uri)

            # Add type
            if '@type' in resource_data:
                types = resource_data['@type'] if isinstance(resource_data['@type'], list) else [resource_data['@type']]
                for type_uri in types:
                    if type_uri.startswith('ldp:'):
                        graph.add((subject, RDF.type, LDP[type_uri[4:]]))
                    elif type_uri.startswith('foaf:'):
                        graph.add((subject, RDF.type, FOAF[type_uri[5:]]))
                    else:
                        graph.add((subject, RDF.type, URIRef(type_uri)))

            # Add properties
            for key, value in resource_data.items():
                if key not in ['@id', '@type', '@context']:
                    predicate_uri = key
                    if key.startswith('ldp:'):
                        predicate = LDP[key[4:]]
                    elif key.startswith('foaf:'):
                        predicate = FOAF[key[5:]]
                    else:
                        predicate = URIRef(key)

                    # Handle arrays
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict) and '@id' in item:
                                # Add reference
                                graph.add((subject, predicate, URIRef(item['@id'])))
                                # Recursively process nested resource
                                add_resource_triples(item, graph)
                            else:
                                # Simple literal in array
                                graph.add((subject, predicate, Literal(item)))

                    # Handle simple literals
                    elif isinstance(value, (str, int, float, bool)):
                        graph.add((subject, predicate, Literal(value)))

                    # Handle nested objects with @id
                    elif isinstance(value, dict) and '@id' in value:
                        graph.add((subject, predicate, URIRef(value['@id'])))
                        # Recursively process nested resource
                        add_resource_triples(value, graph)

        # Process the main resource and all nested resources
        add_resource_triples(data, g)

        turtle_result = g.serialize(format='turtle')
        if isinstance(turtle_result, bytes):
            return turtle_result
        return turtle_result.encode('utf-8') if isinstance(turtle_result, str) else turtle_result
