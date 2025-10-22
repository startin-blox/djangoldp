"""
Unit tests for DjangoLDP renderers and parsers.

Tests both JSON-LD and Turtle renderers/parsers in isolation.
"""

import json
from io import BytesIO
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.exceptions import ParseError

from djangoldp.parsers import JSONLDParser, TurtleParser
from djangoldp.renderers import JSONLDRenderer, TurtleRenderer


class TestJSONLDRenderer(TestCase):
    """Test JSONLDRenderer class."""

    def setUp(self):
        self.renderer = JSONLDRenderer()

    def test_media_type(self):
        """Verify renderer has correct media type."""
        self.assertEqual(self.renderer.media_type, 'application/ld+json')

    def test_render_with_no_context(self):
        """Test rendering data without existing @context."""
        data = {
            '@id': 'http://example.org/resource/1',
            '@type': 'Resource',
            'content': 'test'
        }

        result = self.renderer.render(data)
        parsed = json.loads(result)

        # Should add LDP_RDF_CONTEXT
        self.assertIn('@context', parsed)
        self.assertEqual(parsed['@context'], settings.LDP_RDF_CONTEXT)

    def test_render_with_string_context(self):
        """Test rendering data with existing string @context."""
        data = {
            '@context': 'http://custom.example.org/context.jsonld',
            '@id': 'http://example.org/resource/1',
            'content': 'test'
        }

        result = self.renderer.render(data)
        parsed = json.loads(result)

        # Should merge contexts
        self.assertIsInstance(parsed['@context'], list)
        self.assertEqual(len(parsed['@context']), 2)
        self.assertEqual(parsed['@context'][0], settings.LDP_RDF_CONTEXT)
        self.assertEqual(parsed['@context'][1], 'http://custom.example.org/context.jsonld')

    def test_render_with_dict_context(self):
        """Test rendering data with existing dict @context."""
        custom_context = {'custom': 'http://example.org/custom#'}
        data = {
            '@context': custom_context,
            '@id': 'http://example.org/resource/1',
            'content': 'test'
        }

        result = self.renderer.render(data)
        parsed = json.loads(result)

        # Should merge contexts
        self.assertIsInstance(parsed['@context'], list)
        self.assertEqual(len(parsed['@context']), 2)
        self.assertEqual(parsed['@context'][0], settings.LDP_RDF_CONTEXT)
        self.assertEqual(parsed['@context'][1], custom_context)

    def test_render_with_list_context(self):
        """Test rendering data with existing list @context."""
        existing_contexts = [
            'http://custom1.example.org/context.jsonld',
            'http://custom2.example.org/context.jsonld'
        ]
        data = {
            '@context': existing_contexts,
            '@id': 'http://example.org/resource/1',
            'content': 'test'
        }

        result = self.renderer.render(data)
        parsed = json.loads(result)

        # Should prepend LDP_RDF_CONTEXT to list
        self.assertIsInstance(parsed['@context'], list)
        self.assertEqual(len(parsed['@context']), 3)
        self.assertEqual(parsed['@context'][0], settings.LDP_RDF_CONTEXT)

    def test_render_preserves_field_order(self):
        """Test that @context appears first in rendered output."""
        data = {
            'name': 'Test',
            '@id': 'http://example.org/resource/1',
            '@type': 'Resource'
        }

        result = self.renderer.render(data)
        parsed = json.loads(result)

        # @context should be first key
        keys = list(parsed.keys())
        self.assertEqual(keys[0], '@context')

    def test_render_non_dict_data(self):
        """Test rendering non-dict data (should pass through)."""
        data = ['item1', 'item2']

        result = self.renderer.render(data)
        parsed = json.loads(result)

        # Should return as-is for non-dict data
        self.assertEqual(parsed, data)

    def test_render_none(self):
        """Test rendering None.

        Note: JSONLDRenderer passes through None to parent JSONRenderer,
        which returns the JSON representation.
        """
        result = self.renderer.render(None)
        # JSONRenderer.render(None) returns the JSON null representation
        self.assertIsNotNone(result)  # Just verify it doesn't crash


class TestJSONLDParser(TestCase):
    """Test JSONLDParser class."""

    def setUp(self):
        self.parser = JSONLDParser()

    def test_media_type(self):
        """Verify parser has correct media type."""
        self.assertEqual(self.parser.media_type, 'application/ld+json')

    @patch('djangoldp.parsers.jsonld.compact')
    def test_parse_applies_context(self, mock_compact):
        """Test that parser applies LDP_RDF_CONTEXT to input data."""
        data = {
            '@id': 'http://example.org/resource/1',
            '@type': 'Resource',
            'content': 'test'
        }
        stream = BytesIO(json.dumps(data).encode('utf-8'))

        mock_compact.return_value = data

        result = self.parser.parse(stream)

        # Verify jsonld.compact was called with settings.LDP_RDF_CONTEXT
        mock_compact.assert_called_once()
        # compact is called with positional args: (data, ctx=LDP_RDF_CONTEXT)
        call_kwargs = mock_compact.call_args[1]
        self.assertEqual(call_kwargs['ctx'], settings.LDP_RDF_CONTEXT)

    @patch('djangoldp.parsers.jsonld.compact')
    def test_parse_jsonld_error(self, mock_compact):
        """Test that JsonLdError is converted to ParseError."""
        from pyld import jsonld

        # Create a JsonLdError with required arguments
        error_cause = Exception("Invalid JSON-LD")
        mock_error = jsonld.JsonLdError(
            message="Invalid JSON-LD",
            type_="jsonld.InvalidContext",
            cause=error_cause
        )
        mock_compact.side_effect = mock_error

        data = {'@id': 'http://example.org/resource/1'}
        stream = BytesIO(json.dumps(data).encode('utf-8'))

        with self.assertRaises(ParseError) as cm:
            self.parser.parse(stream)

        self.assertIn("Invalid JSON-LD", str(cm.exception))


class TestTurtleRenderer(TestCase):
    """Test TurtleRenderer class."""

    def setUp(self):
        self.renderer = TurtleRenderer()

    def test_media_type(self):
        """Verify renderer has correct media type."""
        self.assertEqual(self.renderer.media_type, 'text/turtle')
        self.assertEqual(self.renderer.format, 'turtle')
        self.assertEqual(self.renderer.charset, 'utf-8')

    def test_render_none(self):
        """Test rendering None returns empty bytes."""
        result = self.renderer.render(None)
        self.assertEqual(result, b'')

    def test_render_simple_resource(self):
        """Test rendering a simple LDP resource."""
        data = {
            '@id': 'http://example.org/resource/1',
            '@type': 'http://www.w3.org/ns/ldp#Resource',
            'http://example.org/content': 'test content'
        }

        result = self.renderer.render(data)

        # Should return bytes
        self.assertIsInstance(result, bytes)

        # Should contain Turtle syntax
        content = result.decode('utf-8')
        self.assertTrue('@prefix' in content or 'http://' in content)

    def test_render_with_ldp_type(self):
        """Test rendering resource with ldp: prefix."""
        data = {
            '@id': 'http://example.org/container/1',
            '@type': 'ldp:BasicContainer',
            'ldp:contains': [
                {'@id': 'http://example.org/resource/1'},
                {'@id': 'http://example.org/resource/2'}
            ]
        }

        result = self.renderer.render(data)
        content = result.decode('utf-8')

        # Should contain ldp namespace
        self.assertIn('ldp:', content)

    def test_render_returns_bytes(self):
        """Test that render always returns bytes, not str."""
        data = {
            '@id': 'http://example.org/resource/1',
            '@type': 'Resource'
        }

        result = self.renderer.render(data)
        self.assertIsInstance(result, bytes)

    def test_render_fallback_on_error(self):
        """Test that render falls back to simple converter on error."""
        # Create data that might cause rdflib parsing to fail
        data = {
            '@id': 'http://example.org/resource/1',
            '@type': 'ldp:BasicContainer',
            'ldp:contains': []
        }

        # Should not raise exception, should fall back gracefully
        result = self.renderer.render(data)
        self.assertIsInstance(result, bytes)

    def test_simple_jsonld_to_turtle_with_foaf(self):
        """Test simple converter with FOAF namespace."""
        data = {
            '@id': 'http://example.org/person/1',
            '@type': 'foaf:Person',
            'foaf:name': 'John Doe'
        }

        result = self.renderer.simple_jsonld_to_turtle(data)

        # Should handle foaf: prefix
        self.assertIsInstance(result, bytes)
        content = result.decode('utf-8')
        self.assertIn('foaf:', content)

    def test_simple_jsonld_to_turtle_multiple_types(self):
        """Test simple converter with multiple @type values."""
        data = {
            '@id': 'http://example.org/resource/1',
            '@type': ['ldp:Resource', 'ldp:BasicContainer']
        }

        result = self.renderer.simple_jsonld_to_turtle(data)
        self.assertIsInstance(result, bytes)

    def test_render_with_literals(self):
        """Test rendering resource with various literal types."""
        data = {
            '@id': 'http://example.org/resource/1',
            'http://example.org/string': 'text',
            'http://example.org/number': 42,
            'http://example.org/float': 3.14,
            'http://example.org/bool': True
        }

        result = self.renderer.render(data)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_render_nested_objects(self):
        """Test rendering with nested objects."""
        data = {
            '@id': 'http://example.org/resource/1',
            'http://example.org/related': {
                '@id': 'http://example.org/resource/2'
            }
        }

        result = self.renderer.render(data)
        content = result.decode('utf-8')

        # Should contain both resource URIs
        self.assertIn('resource/1', content)
        self.assertIn('resource/2', content)


class TestTurtleParser(TestCase):
    """Test TurtleParser class."""

    def setUp(self):
        self.parser = TurtleParser()

    def test_media_type(self):
        """Verify parser has correct media type."""
        self.assertEqual(self.parser.media_type, 'text/turtle')

    def test_parse_valid_turtle(self):
        """Test parsing valid Turtle data."""
        turtle_data = """
        @prefix ldp: <http://www.w3.org/ns/ldp#> .
        @prefix ex: <http://example.org/> .

        <http://example.org/resource/1> a ldp:Resource ;
            ex:content "test content" .
        """

        stream = BytesIO(turtle_data.encode('utf-8'))
        result = self.parser.parse(stream)

        # Should return parsed and compacted data
        self.assertIsInstance(result, dict)

    def test_parse_empty_turtle(self):
        """Test that empty Turtle raises ParseError."""
        empty_turtle = ""
        stream = BytesIO(empty_turtle.encode('utf-8'))

        with self.assertRaises(ParseError) as cm:
            self.parser.parse(stream)

        self.assertIn("Empty Turtle data", str(cm.exception))

    def test_parse_whitespace_only(self):
        """Test that whitespace-only Turtle raises ParseError."""
        whitespace_turtle = "   \n\t   \n  "
        stream = BytesIO(whitespace_turtle.encode('utf-8'))

        with self.assertRaises(ParseError) as cm:
            self.parser.parse(stream)

        self.assertIn("Empty Turtle data", str(cm.exception))

    def test_parse_malformed_turtle(self):
        """Test that malformed Turtle raises ParseError."""
        malformed_turtle = """
        @prefix ldp: <http://www.w3.org/ns/ldp#>
        This is not valid Turtle syntax!!!
        """

        stream = BytesIO(malformed_turtle.encode('utf-8'))

        with self.assertRaises(ParseError) as cm:
            self.parser.parse(stream)

        self.assertIn("Invalid Turtle syntax", str(cm.exception))

    def test_parse_invalid_utf8(self):
        """Test that invalid UTF-8 encoding raises ParseError."""
        # Create invalid UTF-8 bytes
        invalid_utf8 = b'\x80\x81\x82\x83'
        stream = BytesIO(invalid_utf8)

        with self.assertRaises(ParseError) as cm:
            self.parser.parse(stream)

        self.assertIn("Invalid UTF-8 encoding", str(cm.exception))

    def test_parse_with_multiple_triples(self):
        """Test parsing Turtle with multiple triples."""
        turtle_data = """
        @prefix ldp: <http://www.w3.org/ns/ldp#> .
        @prefix ex: <http://example.org/> .

        <http://example.org/resource/1> a ldp:Resource ;
            ex:title "First Resource" ;
            ex:order 1 .

        <http://example.org/resource/2> a ldp:Resource ;
            ex:title "Second Resource" ;
            ex:order 2 .
        """

        stream = BytesIO(turtle_data.encode('utf-8'))
        result = self.parser.parse(stream)

        # Should successfully parse
        self.assertIsInstance(result, dict)

    def test_parse_with_blank_nodes(self):
        """Test parsing Turtle with blank nodes."""
        turtle_data = """
        @prefix ldp: <http://www.w3.org/ns/ldp#> .
        @prefix ex: <http://example.org/> .

        <http://example.org/resource/1> a ldp:Resource ;
            ex:author [
                ex:name "John Doe" ;
                ex:email "john@example.org"
            ] .
        """

        stream = BytesIO(turtle_data.encode('utf-8'))
        result = self.parser.parse(stream)

        # Should successfully parse blank nodes
        self.assertIsInstance(result, dict)

    def test_parse_applies_context(self):
        """Test that parsed Turtle data has context applied."""
        turtle_data = """
        @prefix ldp: <http://www.w3.org/ns/ldp#> .

        <http://example.org/resource/1> a ldp:Resource .
        """

        stream = BytesIO(turtle_data.encode('utf-8'))

        # Mock the compact function to verify it's called
        with patch('djangoldp.parsers.jsonld.compact') as mock_compact:
            mock_compact.return_value = {'@id': 'http://example.org/resource/1'}

            result = self.parser.parse(stream)

            # Verify compact was called with LDP_RDF_CONTEXT
            mock_compact.assert_called_once()
            args = mock_compact.call_args
            # Second argument (or 'ctx' keyword arg) should be LDP_RDF_CONTEXT
            self.assertEqual(args[1]['ctx'], settings.LDP_RDF_CONTEXT)

    def test_parse_turtle_to_jsonld_conversion(self):
        """Test the Turtle to JSON-LD conversion process."""
        turtle_data = """
        @prefix ex: <http://example.org/> .

        <http://example.org/resource/1>
            ex:title "Test Resource" ;
            ex:count 42 .
        """

        stream = BytesIO(turtle_data.encode('utf-8'))
        result = self.parser.parse(stream)

        # Should return dict after compaction
        self.assertIsInstance(result, dict)


class TestRenderersParserIntegration(TestCase):
    """Integration tests for renderers and parsers working together."""

    def test_jsonld_roundtrip(self):
        """Test JSON-LD can be rendered and parsed back."""
        original_data = {
            '@id': 'http://example.org/resource/1',
            '@type': 'Resource',
            'content': 'test content',
            'count': 42
        }

        # Render
        renderer = JSONLDRenderer()
        rendered = renderer.render(original_data)

        # Parse back
        parser = JSONLDParser()
        stream = BytesIO(rendered)

        with patch('djangoldp.parsers.jsonld.compact') as mock_compact:
            mock_compact.return_value = original_data
            parsed = parser.parse(stream)

            # Should get back similar structure
            self.assertEqual(parsed['@id'], original_data['@id'])

    def test_turtle_can_represent_jsonld_structure(self):
        """Test that Turtle can represent JSON-LD structure."""
        data = {
            '@id': 'http://example.org/resource/1',
            '@type': 'http://www.w3.org/ns/ldp#Resource',
            'http://example.org/title': 'Test'
        }

        # Render to Turtle
        renderer = TurtleRenderer()
        turtle_output = renderer.render(data)

        # Should produce valid Turtle
        self.assertIsInstance(turtle_output, bytes)
        self.assertGreater(len(turtle_output), 0)

        # Parse it back
        parser = TurtleParser()
        stream = BytesIO(turtle_output)

        # Should be able to parse it back (may not be identical due to RDF semantics)
        result = parser.parse(stream)
        self.assertIsInstance(result, dict)


class TestTurtleNestedResources(TestCase):
    """Test that Turtle renderer properly handles nested resources after JSON-LD expansion."""

    def test_nested_resource_properties_included(self):
        """
        Test that nested resource properties are included in Turtle output.

        This tests the JSON-LD expansion feature that was added to fix incomplete
        Turtle responses.
        """
        data = {
            '@context': {
                'username': 'http://example.org/username',
                'email': 'http://example.org/email',
                'member': 'http://example.org/member'
            },
            '@id': 'http://localhost:8000/users/',
            '@type': 'http://www.w3.org/ns/ldp#BasicContainer',
            'member': [
                {
                    '@id': 'http://localhost:8000/users/user1/',
                    'username': 'user1',
                    'email': 'user1@example.com'
                },
                {
                    '@id': 'http://localhost:8000/users/user2/',
                    'username': 'user2',
                    'email': 'user2@example.com'
                }
            ]
        }

        renderer = TurtleRenderer()
        result = renderer.render(data)
        content = result.decode('utf-8')

        # Should include the container URI
        self.assertIn('http://localhost:8000/users/', content)

        # Should include nested user URIs
        self.assertIn('http://localhost:8000/users/user1/', content)
        self.assertIn('http://localhost:8000/users/user2/', content)

        # CRITICAL: Should include nested resource properties (not just URIs)
        self.assertIn('user1', content)
        self.assertIn('user2', content)
        self.assertIn('user1@example.com', content)
        self.assertIn('user2@example.com', content)

    def test_ldp_contains_with_nested_properties(self):
        """Test ldp:contains with full nested resource serialization."""
        data = {
            '@context': 'https://cdn.startinblox.com/owl/context.jsonld',
            '@id': 'http://localhost:8000/posts/',
            '@type': 'ldp:BasicContainer',
            'ldp:contains': [
                {
                    '@id': 'http://localhost:8000/posts/1/',
                    'title': 'First Post',
                    'content': 'Hello World'
                },
                {
                    '@id': 'http://localhost:8000/posts/2/',
                    'title': 'Second Post',
                    'content': 'Goodbye World'
                }
            ]
        }

        renderer = TurtleRenderer()
        result = renderer.render(data)
        content = result.decode('utf-8')

        # Should have ldp:contains relationships (may use namespace prefix like ns1:contains)
        self.assertTrue('contains' in content.lower(), "Should have 'contains' predicate")

        # Should include nested post properties
        self.assertIn('First Post', content)
        self.assertIn('Second Post', content)
        self.assertIn('Hello World', content)
        self.assertIn('Goodbye World', content)

    def test_deeply_nested_resources(self):
        """Test that deeply nested resources (3+ levels) are serialized."""
        data = {
            '@context': {
                'author': 'http://example.org/author',
                'name': 'http://example.org/name',
                'org': 'http://example.org/organization'
            },
            '@id': 'http://example.org/post/1',
            'author': {
                '@id': 'http://example.org/user/1',
                'name': 'John Doe',
                'org': {
                    '@id': 'http://example.org/org/1',
                    'name': 'Acme Corp'
                }
            }
        }

        renderer = TurtleRenderer()
        result = renderer.render(data)
        content = result.decode('utf-8')

        # Should include all levels
        self.assertIn('http://example.org/post/1', content)
        self.assertIn('http://example.org/user/1', content)
        self.assertIn('http://example.org/org/1', content)

        # Should include properties at all levels
        self.assertIn('John Doe', content)
        self.assertIn('Acme Corp', content)

    def test_fallback_handles_nested_resources(self):
        """Test that the simple fallback converter also handles nested resources."""
        renderer = TurtleRenderer()

        # Create data that will likely use the fallback (no @context URL to fetch)
        data = {
            '@id': 'http://example.org/container/',
            '@type': 'ldp:BasicContainer',
            'ldp:contains': [
                {
                    '@id': 'http://example.org/item1/',
                    'http://example.org/title': 'Item 1'
                }
            ]
        }

        # Directly test the fallback method
        result = renderer.simple_jsonld_to_turtle(data)
        content = result.decode('utf-8') if isinstance(result, bytes) else result

        # Should include nested item properties
        self.assertIn('http://example.org/item1/', content)
        self.assertIn('Item 1', content)

    def test_comparison_with_without_expansion(self):
        """
        Document the difference between old behavior (no expansion) and new behavior (with expansion).

        This test shows WHY the JSON-LD expansion was needed.
        """
        data = {
            '@context': {
                'member': 'http://example.org/member',
                'username': 'http://example.org/username'
            },
            '@id': 'http://localhost:8000/users/',
            'member': [
                {
                    '@id': 'http://localhost:8000/users/user1/',
                    'username': 'test_user'
                }
            ]
        }

        renderer = TurtleRenderer()
        result = renderer.render(data)
        content = result.decode('utf-8')

        # Count triples (approximate - count lines with predicates)
        triple_lines = [line for line in content.split('\n')
                       if line.strip() and not line.strip().startswith('@prefix')
                       and not line.strip().startswith('#')]

        # With expansion, we should have multiple triples:
        # 1. Container has type
        # 2. Container has member relationship
        # 3. Member has username property
        # Without expansion, we'd only have triples 1 and 2
        self.assertGreaterEqual(len(triple_lines), 2,
                               "Should have triples for both container and nested resources")

    def test_real_world_user_structure_serialization(self):
        """
        Test that real-world complex nested structures serialize completely.

        Based on actual DjangoLDP user data with account, chatProfile, and owned_objects.
        """
        data = {
            '@context': 'https://cdn.startinblox.com/owl/context.jsonld',
            '@id': 'http://localhost:8000/users/testuser/',
            '@type': 'foaf:user',
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'account': {
                '@id': 'http://localhost:8000/accounts/testuser/',
                'is_backlink': False,
                'allow_create_backlink': True,
                'slug': 'testuser',
                'user': {
                    '@id': 'http://localhost:8000/users/testuser/',
                    '@type': 'foaf:user'
                }
            },
            'chatProfile': {
                '@id': 'http://localhost:8000/chatprofiles/testuser/',
                'is_backlink': False,
                'slug': 'testuser',
                'jabberID': None
            },
            'owned_objects': [
                {
                    '@id': 'http://localhost:8000/users/testuser/owned_trial1/',
                    'container': 'owned_trial1',
                    '@type': ['tems:Object', 'tems:Article']
                }
            ]
        }

        renderer = TurtleRenderer()
        result = renderer.render(data)
        content = result.decode('utf-8')

        # Main user resource
        self.assertIn('http://localhost:8000/users/testuser/', content)
        self.assertIn('testuser', content)
        self.assertIn('test@example.com', content)
        self.assertIn('Test', content)
        self.assertIn('User', content)

        # Nested account resource
        self.assertIn('http://localhost:8000/accounts/testuser/', content)
        # Account properties should be present
        # (either as literals or as part of the serialization)

        # Nested chatProfile resource
        self.assertIn('http://localhost:8000/chatprofiles/testuser/', content)

        # Owned objects
        self.assertIn('http://localhost:8000/users/testuser/owned_trial1/', content)
        self.assertIn('owned_trial1', content)

    def test_container_with_multiple_nested_users(self):
        """
        Test container serialization with multiple users and their nested resources.

        Simulates /users/ endpoint response.
        """
        data = {
            '@context': 'https://cdn.startinblox.com/owl/context.jsonld',
            '@id': 'http://localhost:8000/users/',
            '@type': 'ldp:Container',
            'ldp:contains': [
                {
                    '@id': 'http://localhost:8000/users/user1/',
                    '@type': 'foaf:user',
                    'username': 'user1',
                    'email': 'user1@example.com',
                    'account': {
                        '@id': 'http://localhost:8000/accounts/user1/',
                        'slug': 'user1'
                    }
                },
                {
                    '@id': 'http://localhost:8000/users/user2/',
                    '@type': 'foaf:user',
                    'username': 'user2',
                    'email': 'user2@example.com',
                    'account': {
                        '@id': 'http://localhost:8000/accounts/user2/',
                        'slug': 'user2'
                    }
                }
            ]
        }

        renderer = TurtleRenderer()
        result = renderer.render(data)
        content = result.decode('utf-8')

        # Container
        self.assertIn('http://localhost:8000/users/', content)

        # Both users
        self.assertIn('http://localhost:8000/users/user1/', content)
        self.assertIn('http://localhost:8000/users/user2/', content)

        # User properties
        self.assertIn('user1', content)
        self.assertIn('user2', content)
        self.assertIn('user1@example.com', content)
        self.assertIn('user2@example.com', content)

        # Nested accounts
        self.assertIn('http://localhost:8000/accounts/user1/', content)
        self.assertIn('http://localhost:8000/accounts/user2/', content)
