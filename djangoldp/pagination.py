from rest_framework.pagination import LimitOffsetPagination
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import logging

logger = logging.getLogger('djangoldp')


class LDPOffsetPagination(LimitOffsetPagination):
    """
    LDP-compliant offset-based pagination.

    Provides Link headers with proper rel types as per W3C LDP Paging specification:
    - first: Link to first page
    - last: Link to last page (when determinable)
    - prev: Link to previous page
    - next: Link to next page
    """

    def get_paginated_response(self, data):
        """
        Generate paginated response with W3C LDP-compliant Link headers.

        Returns:
            Response: DRF Response with Link headers for pagination navigation
        """
        next_url = self.get_next_link()
        previous_url = self.get_previous_link()

        links = []

        # Add first link (offset=0)
        if self.request:
            first_url = self.request.build_absolute_uri(self.request.path)
            # Remove offset parameter or set to 0
            if '?' in first_url:
                first_url = first_url.split('?')[0]
            links.append('<{}>; rel="first"'.format(first_url))

        # Add prev link
        if previous_url is not None:
            links.append('<{}>; rel="prev"'.format(previous_url))

        # Add next link
        if next_url is not None:
            links.append('<{}>; rel="next"'.format(next_url))

        # Try to calculate last link if we have total count
        if self.count and self.limit:
            try:
                last_offset = (self.count // self.limit) * self.limit
                if last_offset >= self.count:
                    last_offset = max(0, self.count - self.limit)

                last_url = self.request.build_absolute_uri(self.request.path)
                separator = '&' if '?' in last_url else '?'
                last_url = '{}{}limit={}&offset={}'.format(
                    last_url.split('?')[0] + '?',
                    '',
                    self.limit,
                    last_offset
                )
                links.append('<{}>; rel="last"'.format(last_url))
            except Exception as e:
                logger.warning(f"Could not generate last link: {e}")

        headers = {'Link': ', '.join(links)} if links else {}
        return Response(data, headers=headers)


class LDPPagination(PageNumberPagination):
    """
    LDP-compliant page number-based pagination.

    Provides Link headers with proper rel types as per W3C LDP Paging specification:
    - first: Link to first page
    - last: Link to last page
    - prev: Link to previous page
    - next: Link to next page

    Additionally marks paginated responses with ldp:Page type.
    """

    page_query_param = 'p'
    page_size_query_param = 'limit'

    def get_paginated_response(self, data):
        """
        Generate paginated response with W3C LDP-compliant Link headers.

        Includes:
        - Navigation links (first, prev, next, last)
        - ldp:Page type indicator

        Returns:
            Response: DRF Response with Link headers for pagination navigation
        """
        next_url = self.get_next_link()
        previous_url = self.get_previous_link()

        links = []

        # Add first link (page 1)
        if self.request:
            first_url = self.request.build_absolute_uri(self.request.path)
            # Remove page parameter or set to 1
            if '?' in first_url:
                first_url = first_url.split('?')[0]
            links.append('<{}>; rel="first"'.format(first_url))

        # Add prev link
        if previous_url is not None:
            links.append('<{}>; rel="prev"'.format(previous_url))

        # Add next link
        if next_url is not None:
            links.append('<{}>; rel="next"'.format(next_url))

        # Add last link if we can determine total pages
        if hasattr(self, 'page') and self.page is not None:
            try:
                # Get the paginator from the page object
                paginator = self.page.paginator
                num_pages = paginator.num_pages

                if num_pages > 1:
                    last_url = self.request.build_absolute_uri(self.request.path)
                    separator = '&' if '?' in last_url else '?'
                    # Build last URL with page parameter
                    if '?' in last_url:
                        last_url = last_url.split('?')[0]
                    last_url = '{}?{}={}'.format(last_url, self.page_query_param, num_pages)
                    links.append('<{}>; rel="last"'.format(last_url))
            except Exception as e:
                logger.warning(f"Could not generate last link: {e}")

        # Add ldp:Page type to indicate this is a paginated response
        links.append('<http://www.w3.org/ns/ldp#Page>; rel="type"')

        headers = {'Link': ', '.join(links)} if links else {}
        return Response(data, headers=headers)
