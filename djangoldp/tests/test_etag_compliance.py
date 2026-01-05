"""
Comprehensive tests for ETag and Conditional Request implementation.

Tests compliance with:
- RFC 7232 (Conditional Requests)
- W3C LDP specification
- HTTP caching best practices
"""

import json
from datetime import datetime, timedelta
from time import sleep

from django.contrib.auth import get_user_model
from django.utils.http import http_date
from rest_framework.test import APIClient, APIRequestFactory, APITestCase

from djangoldp.etag import generate_etag, generate_container_etag, normalize_etag
from djangoldp.serializers import GLOBAL_SERIALIZER_CACHE
from djangoldp.tests.models import Post


class TestETagCompliance(APITestCase):
    """Test ETag generation and conditional request handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        GLOBAL_SERIALIZER_CACHE.reset()

    def tearDown(self):
        """Clean up after tests."""
        GLOBAL_SERIALIZER_CACHE.reset()

    # ===== ETag Presence Tests =====

    def test_etag_present_on_get(self):
        """Verify ETag header is present on GET requests."""
        post = Post.objects.create(content="test content")
        response = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
        self.assertIsNotNone(response['ETag'])
        self.assertTrue(len(response['ETag']) > 0)

    def test_etag_present_on_post(self):
        """Verify ETag header is present on POST (create) responses."""
        data = {'https://cdn.startinblox.com/owl#content': 'new post content'}
        response = self.client.post(
            '/posts/',
            data=json.dumps(data),
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn('ETag', response)
        self.assertIsNotNone(response['ETag'])
        self.assertTrue(len(response['ETag']) > 0)

    def test_etag_present_on_put(self):
        """Verify ETag header is present on PUT (update) responses."""
        post = Post.objects.create(content="original content")

        # Get the current ETag
        get_response = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )
        etag = get_response['ETag']

        # Update with If-Match
        data = {'https://cdn.startinblox.com/owl#content': 'updated content'}
        response = self.client.put(
            f'/posts/{post.pk}/',
            data=json.dumps(data),
            content_type='application/ld+json',
            HTTP_IF_MATCH=etag
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
        self.assertIsNotNone(response['ETag'])
        self.assertTrue(len(response['ETag']) > 0)
        # New ETag should be different from old one
        self.assertNotEqual(response['ETag'], etag)

    def test_etag_format_valid(self):
        """Verify ETag format follows RFC 7232 (weak ETag format)."""
        post = Post.objects.create(content="test content")
        response = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )

        etag = response['ETag']
        # Should be weak ETag format: W/"value"
        self.assertTrue(etag.startswith('W/"'))
        self.assertTrue(etag.endswith('"'))
        # Extract the value
        is_weak, etag_value = normalize_etag(etag)
        self.assertTrue(is_weak)
        self.assertTrue(len(etag_value) > 0)

    # ===== If-Match Tests =====

    def test_if_match_success(self):
        """Test If-Match succeeds when ETag matches."""
        post = Post.objects.create(content="original content")

        # Get current ETag
        get_response = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )
        etag = get_response['ETag']

        # Update with matching ETag
        data = {'https://cdn.startinblox.com/owl#content': 'updated content'}
        response = self.client.put(
            f'/posts/{post.pk}/',
            data=json.dumps(data),
            content_type='application/ld+json',
            HTTP_IF_MATCH=etag
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['content'], 'updated content')

    def test_if_match_failure(self):
        """Test If-Match fails with 412 when ETag doesn't match."""
        post = Post.objects.create(content="original content")

        # Use a non-matching ETag
        data = {'https://cdn.startinblox.com/owl#content': 'updated content'}
        response = self.client.put(
            f'/posts/{post.pk}/',
            data=json.dumps(data),
            content_type='application/ld+json',
            HTTP_IF_MATCH='W/"wrong-etag"'
        )

        self.assertEqual(response.status_code, 412)
        self.assertIn('detail', response.data)
        # Verify content wasn't updated
        post.refresh_from_db()
        self.assertEqual(post.content, 'original content')

    def test_if_match_star(self):
        """Test If-Match with * matches any existing resource."""
        post = Post.objects.create(content="original content")

        # Update with If-Match: *
        data = {'https://cdn.startinblox.com/owl#content': 'updated content'}
        response = self.client.put(
            f'/posts/{post.pk}/',
            data=json.dumps(data),
            content_type='application/ld+json',
            HTTP_IF_MATCH='*'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['content'], 'updated content')

    # ===== If-None-Match Tests =====

    def test_if_none_match_get_304(self):
        """Test If-None-Match returns 304 for GET when ETag matches."""
        post = Post.objects.create(content="test content")

        # Get current ETag
        get_response = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )
        etag = get_response['ETag']

        # Request again with If-None-Match
        response = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json',
            HTTP_IF_NONE_MATCH=etag
        )

        self.assertEqual(response.status_code, 304)
        # 304 responses should not have a body
        self.assertEqual(len(response.content), 0)

    def test_if_none_match_put_412(self):
        """Test If-None-Match returns 412 for PUT when ETag matches."""
        post = Post.objects.create(content="original content")

        # Get current ETag
        get_response = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )
        etag = get_response['ETag']

        # Try to update with If-None-Match (should fail)
        data = {'https://cdn.startinblox.com/owl#content': 'updated content'}
        response = self.client.put(
            f'/posts/{post.pk}/',
            data=json.dumps(data),
            content_type='application/ld+json',
            HTTP_IF_NONE_MATCH=etag
        )

        self.assertEqual(response.status_code, 412)
        # Verify content wasn't updated
        post.refresh_from_db()
        self.assertEqual(post.content, 'original content')

    # ===== If-Modified-Since Tests =====

    def test_if_modified_since_304(self):
        """Test If-Modified-Since returns 304 when resource hasn't changed."""
        import time

        post = Post.objects.create(content="test content")

        # Get the resource to obtain Last-Modified
        response1 = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )
        self.assertEqual(response1.status_code, 200)

        # Response should have Last-Modified header
        self.assertIn('Last-Modified', response1)
        last_modified = response1['Last-Modified']

        # Make another GET request with If-Modified-Since set to the Last-Modified value
        response2 = self.client.get(
            f'/posts/{post.pk}/',
            HTTP_IF_MODIFIED_SINCE=last_modified,
            content_type='application/ld+json'
        )

        # Should return 304 Not Modified since the resource hasn't changed
        self.assertEqual(response2.status_code, 304)

        # 304 responses should have no body
        self.assertEqual(len(response2.content), 0)

        # Wait at least 1 second to ensure updated_at changes
        # (HTTP dates only have second precision, not microsecond)
        time.sleep(1.1)

        # Update the resource
        post.content = "updated content"
        post.save()

        # Make another request with the old If-Modified-Since value
        response3 = self.client.get(
            f'/posts/{post.pk}/',
            HTTP_IF_MODIFIED_SINCE=last_modified,
            content_type='application/ld+json'
        )

        # Should return 200 with full content since resource has been modified
        self.assertEqual(response3.status_code, 200)
        self.assertGreater(len(response3.content), 0)

        # Should have a new Last-Modified header
        self.assertIn('Last-Modified', response3)
        self.assertNotEqual(response3['Last-Modified'], last_modified)

    # ===== ETag Stability Tests =====

    def test_etag_changes_on_update(self):
        """Verify ETag changes when resource is updated."""
        post = Post.objects.create(content="original content")

        # Get initial ETag
        response1 = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )
        etag1 = response1['ETag']

        # Update the resource
        post.content = "updated content"
        post.save()

        # Get new ETag
        response2 = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )
        etag2 = response2['ETag']

        # ETags should be different
        self.assertNotEqual(etag1, etag2)

    def test_etag_stable_for_unchanged(self):
        """Verify ETag remains stable when resource hasn't changed."""
        post = Post.objects.create(content="test content")

        # Get ETag twice
        response1 = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )
        etag1 = response1['ETag']

        response2 = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )
        etag2 = response2['ETag']

        # ETags should be the same
        self.assertEqual(etag1, etag2)

    # ===== Container ETag Tests =====

    def test_container_etag_present(self):
        """Verify container (list) responses include ETag."""
        Post.objects.create(content="post 1")
        Post.objects.create(content="post 2")

        response = self.client.get('/posts/', content_type='application/ld+json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('ETag', response)
        self.assertIsNotNone(response['ETag'])

    def test_container_etag_changes_on_add(self):
        """Verify container ETag changes when items are added."""
        Post.objects.create(content="post 1")

        # Get initial container ETag
        response1 = self.client.get('/posts/', content_type='application/ld+json')
        etag1 = response1['ETag']

        # Add another post
        Post.objects.create(content="post 2")

        # Get new container ETag
        response2 = self.client.get('/posts/', content_type='application/ld+json')
        etag2 = response2['ETag']

        # ETags should be different
        self.assertNotEqual(etag1, etag2)

    # ===== Concurrent Update Prevention Tests =====

    def test_concurrent_update_prevention(self):
        """Test that If-Match prevents lost updates in concurrent scenarios."""
        post = Post.objects.create(content="original content")

        # Client A gets the resource
        response_a = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )
        etag_a = response_a['ETag']

        # Client B gets the resource
        response_b = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )
        etag_b = response_b['ETag']

        # Both should have the same ETag
        self.assertEqual(etag_a, etag_b)

        # Client A updates successfully
        data_a = {'https://cdn.startinblox.com/owl#content': 'updated by A'}
        response_a_update = self.client.put(
            f'/posts/{post.pk}/',
            data=json.dumps(data_a),
            content_type='application/ld+json',
            HTTP_IF_MATCH=etag_a
        )
        self.assertEqual(response_a_update.status_code, 200)
        new_etag = response_a_update['ETag']

        # Client B tries to update with stale ETag (should fail)
        data_b = {'https://cdn.startinblox.com/owl#content': 'updated by B'}
        response_b_update = self.client.put(
            f'/posts/{post.pk}/',
            data=json.dumps(data_b),
            content_type='application/ld+json',
            HTTP_IF_MATCH=etag_b  # Using stale ETag
        )

        # Should fail with 412 Precondition Failed
        self.assertEqual(response_b_update.status_code, 412)

        # Verify only Client A's update was applied
        post.refresh_from_db()
        self.assertEqual(post.content, 'updated by A')

    # ===== Malformed ETag Handling Tests =====

    def test_malformed_etag_handling(self):
        """Test that malformed ETags are handled gracefully."""
        post = Post.objects.create(content="test content")

        # Try various malformed ETags
        malformed_etags = [
            'not-a-valid-etag',
            'W/"incomplete',
            '""',
            'W/',
        ]

        for malformed_etag in malformed_etags:
            data = {'https://cdn.startinblox.com/owl#content': 'updated content'}
            response = self.client.put(
                f'/posts/{post.pk}/',
                data=json.dumps(data),
                content_type='application/ld+json',
                HTTP_IF_MATCH=malformed_etag
            )

            # Should fail with 412 (doesn't match) but not crash
            # The server should handle malformed ETags gracefully
            self.assertIn(response.status_code, [200, 412])


class TestETagUtilities(APITestCase):
    """Test ETag utility functions."""

    def test_normalize_etag_weak(self):
        """Test normalizing weak ETags."""
        etag = 'W/"abc123"'
        is_weak, normalized = normalize_etag(etag)
        self.assertTrue(is_weak)
        self.assertEqual(normalized, 'abc123')

    def test_normalize_etag_strong(self):
        """Test normalizing strong ETags."""
        etag = '"abc123"'
        is_weak, normalized = normalize_etag(etag)
        self.assertFalse(is_weak)
        self.assertEqual(normalized, 'abc123')

    def test_normalize_etag_no_quotes(self):
        """Test normalizing ETags without quotes."""
        etag = 'abc123'
        is_weak, normalized = normalize_etag(etag)
        self.assertFalse(is_weak)
        self.assertEqual(normalized, 'abc123')

    def test_normalize_etag_empty(self):
        """Test normalizing empty ETags."""
        is_weak, normalized = normalize_etag('')
        self.assertFalse(is_weak)
        self.assertEqual(normalized, '')

        is_weak, normalized = normalize_etag(None)
        self.assertFalse(is_weak)
        self.assertEqual(normalized, '')

    def test_generate_etag_format(self):
        """Test that generated ETags use weak format consistently."""
        post = Post.objects.create(content="test content")
        etag = generate_etag(post)

        # Should be weak ETag format
        self.assertTrue(etag.startswith('W/"'))
        self.assertTrue(etag.endswith('"'))

    def test_generate_container_etag_format(self):
        """Test that container ETags use weak format."""
        Post.objects.create(content="post 1")
        Post.objects.create(content="post 2")

        queryset = Post.objects.all()
        count = queryset.count()
        etag = generate_container_etag(queryset, count)

        # Should be weak ETag format
        self.assertTrue(etag.startswith('W/"'))
        self.assertTrue(etag.endswith('"'))

    def test_generate_container_etag_with_pagination(self):
        """Test that container ETags include page number when paginated."""
        Post.objects.create(content="post 1")
        Post.objects.create(content="post 2")

        queryset = Post.objects.all()
        count = queryset.count()

        # Generate ETags for different pages
        etag_page1 = generate_container_etag(queryset, count, page_number=1)
        etag_page2 = generate_container_etag(queryset, count, page_number=2)

        # ETags should be different for different pages
        self.assertNotEqual(etag_page1, etag_page2)

    def test_generate_etag_deterministic(self):
        """Test that ETag generation is deterministic."""
        post = Post.objects.create(content="test content")

        # Generate ETag multiple times
        etag1 = generate_etag(post)
        etag2 = generate_etag(post)
        etag3 = generate_etag(post)

        # All should be the same
        self.assertEqual(etag1, etag2)
        self.assertEqual(etag2, etag3)
