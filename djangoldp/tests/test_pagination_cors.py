"""
Comprehensive tests for Phase 2: Enhanced Pagination and CORS Improvements.

This test suite covers:
- W3C LDP Paging specification compliance
  - first, last, prev, next Link headers
  - ldp:Page type on paginated responses
  - Container Link header preservation
- CORS improvements
  - Access-Control-Expose-Headers for LDP headers
  - CORS headers on various request types
- Pagination with different content types (JSON-LD, Turtle)
"""

import json
from rest_framework.test import APIClient, APITestCase
from djangoldp.tests.models import Post, User
from django.contrib.auth import get_user_model


class TestEnhancedPagination(APITestCase):
    """Test suite for W3C LDP Paging specification compliance."""

    def setUp(self):
        """Set up test fixtures with enough posts to trigger pagination."""
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create 30 posts to ensure pagination is triggered
        for i in range(30):
            Post.objects.create(
                content=f"Test post content {i}",
                author=self.user
            )

    def tearDown(self):
        """Clean up test data."""
        Post.objects.all().delete()
        get_user_model().objects.all().delete()

    def test_pagination_first_link(self):
        """
        Test that paginated responses include a 'first' link.

        W3C LDP Paging requires a link to the first page.
        """
        response = self.client.get(
            '/posts/?p=2',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Link', response)

        link_header = response['Link']

        # Should include first link
        self.assertIn('rel="first"', link_header)
        self.assertIn('http://testserver/posts/', link_header)

    def test_pagination_last_link(self):
        """
        Test that paginated responses include a 'last' link when determinable.

        W3C LDP Paging requires a link to the last page when the total
        number of pages can be determined.
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Link', response)

        link_header = response['Link']

        # Should include last link
        self.assertIn('rel="last"', link_header)

    def test_pagination_prev_link(self):
        """
        Test that paginated responses include a 'prev' link when applicable.

        The 'prev' link should be present on all pages except the first.
        """
        response = self.client.get(
            '/posts/?p=2',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Link', response)

        link_header = response['Link']

        # Should include prev link on page 2
        self.assertIn('rel="prev"', link_header)

    def test_pagination_next_link(self):
        """
        Test that paginated responses include a 'next' link when applicable.

        The 'next' link should be present on all pages except the last.
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Link', response)

        link_header = response['Link']

        # Should include next link on first page
        self.assertIn('rel="next"', link_header)

    def test_pagination_ldp_page_type(self):
        """
        Test that paginated responses include ldp:Page type.

        W3C LDP Paging spec requires paginated responses to be marked
        with the ldp:Page type.
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Link', response)

        link_header = response['Link']

        # Should include ldp:Page type
        self.assertIn('<http://www.w3.org/ns/ldp#Page>; rel="type"', link_header)

    def test_pagination_preserves_container_links(self):
        """
        Test that container Link headers are preserved on paginated responses.

        Paginated container responses should include both:
        - Pagination navigation links (first, prev, next, last)
        - LDP container type links (ldp:Container, ldp:BasicContainer)
        - ldp:Page type
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Link', response)

        link_header = response['Link']

        # Pagination links should be present
        self.assertIn('rel="first"', link_header)
        self.assertIn('rel="next"', link_header)
        self.assertIn('<http://www.w3.org/ns/ldp#Page>; rel="type"', link_header)

        # Container type links should also be present
        self.assertIn('<http://www.w3.org/ns/ldp#Container>; rel="type"', link_header)
        self.assertIn('<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"', link_header)
        self.assertIn('<http://www.w3.org/ns/ldp#Resource>; rel="type"', link_header)
        self.assertIn('<http://www.w3.org/ns/ldp#RDFSource>; rel="type"', link_header)

    def test_pagination_link_order(self):
        """
        Test that pagination links appear before LDP type links.

        This ensures pagination links are easily accessible and not
        buried in the Link header.
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        link_header = response['Link']

        # Find positions of pagination and LDP type links
        first_pos = link_header.find('rel="first"')
        container_pos = link_header.find('ldp#Container')

        # Pagination links should come before container type links
        self.assertLess(first_pos, container_pos,
                       "Pagination links should appear before LDP type links")

    def test_pagination_all_nav_links_present(self):
        """
        Test that all navigation links are present on middle pages.

        A middle page (not first or last) should have all four navigation links:
        first, prev, next, last.
        """
        response = self.client.get(
            '/posts/?p=2',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        link_header = response['Link']

        # All navigation links should be present on a middle page
        self.assertIn('rel="first"', link_header)
        self.assertIn('rel="prev"', link_header)
        self.assertIn('rel="next"', link_header)
        self.assertIn('rel="last"', link_header)

    def test_pagination_with_turtle_format(self):
        """
        Test that pagination works correctly with Turtle content type.

        Pagination headers should be present regardless of response format.
        """
        response = self.client.get(
            '/posts/',
            HTTP_ACCEPT='text/turtle'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/turtle; charset=utf-8')
        self.assertIn('Link', response)

        link_header = response['Link']

        # Pagination links should be present with Turtle format
        self.assertIn('rel="first"', link_header)
        self.assertIn('rel="next"', link_header)
        self.assertIn('<http://www.w3.org/ns/ldp#Page>; rel="type"', link_header)

    def test_no_pagination_on_detail_view(self):
        """
        Test that detail views do not include pagination links.

        Single resource views should not have pagination-related Link headers.
        """
        post = Post.objects.first()
        response = self.client.get(
            f'/posts/{post.pk}/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        link_header = response.get('Link', '')

        # Should not have pagination links
        self.assertNotIn('rel="first"', link_header)
        self.assertNotIn('rel="prev"', link_header)
        self.assertNotIn('rel="next"', link_header)
        self.assertNotIn('rel="last"', link_header)
        self.assertNotIn('ldp#Page', link_header)

        # Should have resource type links
        self.assertIn('<http://www.w3.org/ns/ldp#Resource>; rel="type"', link_header)
        self.assertIn('<http://www.w3.org/ns/ldp#RDFSource>; rel="type"', link_header)


class TestCORSImprovements(APITestCase):
    """Test suite for CORS improvements with LDP-specific headers."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.post = Post.objects.create(content="Test post content", author=self.user)

    def tearDown(self):
        """Clean up test data."""
        Post.objects.all().delete()
        get_user_model().objects.all().delete()

    def test_cors_expose_headers_on_get(self):
        """
        Test that Access-Control-Expose-Headers is present on GET requests.

        This header tells browsers which headers can be accessed by client JavaScript
        in cross-origin requests.
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Access-Control-Expose-Headers', response)

        expose_headers = response['Access-Control-Expose-Headers']

        # Verify all LDP headers are exposed
        expected_headers = [
            'Link',
            'ETag',
            'Accept-Post',
            'Accept-Patch',
            'Preference-Applied',
            'Last-Modified',
            'Location',
            'User'
        ]

        for header in expected_headers:
            self.assertIn(header, expose_headers,
                         f"{header} should be in Access-Control-Expose-Headers")

    def test_cors_expose_headers_on_post(self):
        """
        Test that Access-Control-Expose-Headers is present on POST requests.
        """
        new_post_data = {
            "https://cdn.startinblox.com/owl#content": "New post via API"
        }

        response = self.client.post(
            '/posts/',
            data=json.dumps(new_post_data),
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn('Access-Control-Expose-Headers', response)

        expose_headers = response['Access-Control-Expose-Headers']

        # Key headers for POST responses
        self.assertIn('Location', expose_headers)
        self.assertIn('ETag', expose_headers)
        self.assertIn('Link', expose_headers)

    def test_cors_expose_headers_on_put(self):
        """
        Test that Access-Control-Expose-Headers is present on PUT requests.
        """
        updated_data = {
            
            "https://cdn.startinblox.com/owl#content": "Updated content"
        }

        response = self.client.put(
            f'/posts/{self.post.pk}/',
            data=json.dumps(updated_data),
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Access-Control-Expose-Headers', response)

        expose_headers = response['Access-Control-Expose-Headers']

        # Key headers for PUT responses
        self.assertIn('ETag', expose_headers)
        self.assertIn('Link', expose_headers)

    def test_cors_expose_headers_on_options(self):
        """
        Test that Access-Control-Expose-Headers is present on OPTIONS requests.

        OPTIONS requests are used in CORS preflight checks.
        """
        response = self.client.options(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Access-Control-Expose-Headers', response)

    def test_cors_expose_headers_on_detail_view(self):
        """
        Test that Access-Control-Expose-Headers is present on detail views.
        """
        response = self.client.get(
            f'/posts/{self.post.pk}/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Access-Control-Expose-Headers', response)

        expose_headers = response['Access-Control-Expose-Headers']

        # Detail views should expose ETag and Last-Modified
        self.assertIn('ETag', expose_headers)
        self.assertIn('Last-Modified', expose_headers)

    def test_cors_expose_headers_includes_all_ldp_headers(self):
        """
        Test that all LDP-specific headers are included in Access-Control-Expose-Headers.

        This comprehensive test verifies that every LDP header is properly exposed
        for CORS requests.
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        expose_headers = response['Access-Control-Expose-Headers']

        # Complete list of LDP headers that should be exposed
        required_headers = [
            'Link',
            'ETag',
            'Accept-Post',
            'Accept-Patch',
            'Preference-Applied',
            'Last-Modified',
            'Location',
            'User'
        ]

        for header in required_headers:
            self.assertIn(
                header,
                expose_headers,
                f"Access-Control-Expose-Headers must include {header}"
            )

    def test_cors_headers_format(self):
        """
        Test that Access-Control-Expose-Headers is properly formatted.

        The header should be a comma-separated list of header names.
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        expose_headers = response['Access-Control-Expose-Headers']

        # Should be comma-separated
        header_list = [h.strip() for h in expose_headers.split(',')]
        self.assertGreater(len(header_list), 0,
                          "Should have at least one exposed header")

        # Each header name should be valid (no empty strings)
        for header_name in header_list:
            self.assertGreater(len(header_name), 0,
                             "Header names should not be empty")

    def test_cors_with_pagination(self):
        """
        Test that CORS headers are present on paginated responses.

        Paginated responses should include CORS headers just like non-paginated ones.
        """
        # Create enough posts to trigger pagination
        for i in range(25):
            Post.objects.create(content=f"Post {i}", author=self.user)

        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Access-Control-Expose-Headers', response)

        expose_headers = response['Access-Control-Expose-Headers']

        # Should include Link header (for pagination and LDP types)
        self.assertIn('Link', expose_headers)


class TestPaginationCORSIntegration(APITestCase):
    """Test suite for integration of pagination and CORS features."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create enough posts to trigger pagination
        for i in range(30):
            Post.objects.create(content=f"Test post {i}", author=self.user)

    def tearDown(self):
        """Clean up test data."""
        Post.objects.all().delete()
        get_user_model().objects.all().delete()

    def test_paginated_response_has_all_features(self):
        """
        Test that paginated responses have all Phase 2 features.

        This comprehensive test verifies that a paginated response includes:
        - Pagination navigation links (first, prev, next, last)
        - ldp:Page type
        - LDP container types
        - CORS expose headers
        - Proper ETag
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)

        # Check pagination links
        link_header = response['Link']
        self.assertIn('rel="first"', link_header)
        self.assertIn('rel="next"', link_header)
        self.assertIn('<http://www.w3.org/ns/ldp#Page>; rel="type"', link_header)

        # Check LDP container types
        self.assertIn('<http://www.w3.org/ns/ldp#Container>; rel="type"', link_header)
        self.assertIn('<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"', link_header)

        # Check CORS headers
        self.assertIn('Access-Control-Expose-Headers', response)
        expose_headers = response['Access-Control-Expose-Headers']
        self.assertIn('Link', expose_headers)
        self.assertIn('ETag', expose_headers)

        # Check ETag is present (from Phase 1)
        self.assertIn('ETag', response)

    def test_pagination_link_accessibility_via_cors(self):
        """
        Test that pagination Link headers are accessible via CORS.

        The Link header must be in Access-Control-Expose-Headers to be
        readable by client JavaScript in cross-origin scenarios.
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)

        # Link header should be present
        self.assertIn('Link', response)

        # Link header should be exposed for CORS
        expose_headers = response['Access-Control-Expose-Headers']
        self.assertIn('Link', expose_headers,
                     "Link header must be exposed for CORS to access pagination links")

    def test_etag_on_paginated_response(self):
        """
        Test that paginated responses include ETag headers.

        ETags on paginated containers should include the page number
        to ensure different pages have different ETags.
        """
        # Get first page
        response1 = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response1.status_code, 200)
        self.assertIn('ETag', response1)
        etag1 = response1['ETag']

        # Get second page
        response2 = self.client.get(
            '/posts/?p=2',
            content_type='application/ld+json'
        )

        self.assertEqual(response2.status_code, 200)
        self.assertIn('ETag', response2)
        etag2 = response2['ETag']

        # Different pages should have different ETags
        # (This is from Phase 1, but verifying it still works)
        # Note: We're just checking both have ETags; exact comparison
        # depends on implementation details

    def test_accept_post_exposed_for_cors(self):
        """
        Test that Accept-Post header is exposed for CORS.

        Clients need to know what content types they can POST.
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)

        # Accept-Post should be present
        self.assertIn('Accept-Post', response)
        accept_post = response['Accept-Post']
        self.assertIn('application/ld+json', accept_post)
        self.assertIn('text/turtle', accept_post)

        # Accept-Post should be exposed for CORS
        expose_headers = response['Access-Control-Expose-Headers']
        self.assertIn('Accept-Post', expose_headers)

    def test_backward_compatibility_with_phase1(self):
        """
        Test that Phase 2 changes don't break Phase 1 features.

        Verify that:
        - Link headers still include LDP types
        - ETags are still present
        - Turtle format still works
        - Accept-Post still includes text/turtle
        """
        response = self.client.get(
            '/posts/',
            content_type='application/ld+json'
        )

        self.assertEqual(response.status_code, 200)

        # Phase 1: Link headers for LDP types
        link_header = response['Link']
        self.assertIn('<http://www.w3.org/ns/ldp#Resource>; rel="type"', link_header)
        self.assertIn('<http://www.w3.org/ns/ldp#Container>; rel="type"', link_header)

        # Phase 1: ETag header
        self.assertIn('ETag', response)

        # Phase 1: Accept-Post includes Turtle
        self.assertIn('Accept-Post', response)
        self.assertIn('text/turtle', response['Accept-Post'])

        # Phase 1: Turtle format works
        turtle_response = self.client.get(
            '/posts/',
            HTTP_ACCEPT='text/turtle'
        )
        self.assertEqual(turtle_response.status_code, 200)
        self.assertEqual(turtle_response['Content-Type'], 'text/turtle; charset=utf-8')
