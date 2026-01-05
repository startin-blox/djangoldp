"""
DjangoLDP Parsers for content negotiation.

Provides parsers for:
- JSON-LD (application/ld+json)
- Turtle (text/turtle)
"""

import json
import logging

from django.conf import settings
from pyld import jsonld
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser, BaseParser
from rdflib import Graph

logger = logging.getLogger('djangoldp')


class JSONLDParser(JSONParser):
    """
    Parser which handles JSON-LD input and applies the configured context.

    Uses pyld library for JSON-LD processing: https://github.com/digitalbazaar/pyld

    Note: Currently only works with pyld 1.0. We need to check support for newer versions.
    """
    media_type = 'application/ld+json'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parse JSON-LD input and compact it using the configured context.

        Compacting applies the context to the data and makes it easier to work with.
        See: http://json-ld.org/spec/latest/json-ld/#compacted-document-form
        """
        data = super(JSONLDParser, self).parse(stream, media_type, parser_context)

        try:
            return jsonld.compact(data, ctx=settings.LDP_RDF_CONTEXT)
        except jsonld.JsonLdError as e:
            raise ParseError(str(e.cause))


class TurtleParser(BaseParser):
    """
    Parser which handles Turtle format input.

    Turtle (Terse RDF Triple Language) is a compact RDF serialization format.
    See: https://www.w3.org/TR/turtle/

    Converts Turtle to JSON-LD and applies the configured context.
    """
    media_type = 'text/turtle'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parse Turtle input to JSON-LD and apply context.

        Process:
        1. Decode UTF-8 Turtle input
        2. Parse Turtle into RDF graph using rdflib
        3. Convert RDF graph to JSON-LD
        4. Apply LDP context for compaction

        Raises:
            ParseError: If Turtle is malformed or cannot be processed
        """
        # Decode input stream
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
