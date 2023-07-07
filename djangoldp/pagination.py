from rest_framework.pagination import LimitOffsetPagination
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class LDPOffsetPagination(LimitOffsetPagination):
    def get_paginated_response(self, data):
        next_url = self.get_next_link()
        previous_url = self.get_previous_link()

        links = []
        for url, label in ((previous_url, 'prev'), (next_url, 'next')):
            if url is not None:
                links.append('<{}>; rel="{}"'.format(url, label))

        headers = {'Link': ', '.join(links)} if links else {}
        return Response(data, headers=headers)


class LDPPagination(PageNumberPagination):
    page_query_param = 'p'
    page_size_query_param = 'limit'

    def get_paginated_response(self, data):
        next_url = self.get_next_link()
        previous_url = self.get_previous_link()

        links = []
        for url, label in ((previous_url, 'prev'), (next_url, 'next')):
            if url is not None:
                links.append('<{}>; rel="{}"'.format(url, label))

        headers = {'Link': ', '.join(links)} if links else {}
        return Response(data, headers=headers)
