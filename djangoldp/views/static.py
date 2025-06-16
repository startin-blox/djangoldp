import json
import logging
import os
import time

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponseNotFound, JsonResponse
from django.urls.resolvers import get_resolver

from rest_framework.renderers import JSONRenderer

logger = logging.getLogger('djangoldp')


def serve_static_content(request, path):

    if request.method != "GET":
        resolver = get_resolver()
        match = resolver.resolve("/" + path)
        request.user = AnonymousUser()
        return match.func(request, *match.args, **match.kwargs)

    server_url = getattr(settings, "BASE_URL", "http://localhost")

    is_filtered = request.GET.get('search-fields', False)

    output_dir = "ssr"
    output_dir_filtered = "ssr_filtered"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    if not os.path.exists(output_dir_filtered):
        os.makedirs(output_dir_filtered, exist_ok=True)

    file_path = os.path.join(output_dir if not is_filtered else output_dir_filtered, path[:-1])
    if not file_path.endswith(".jsonld"):
        file_path += ".jsonld"

    if os.path.exists(file_path):
        current_time = time.time()
        file_mod_time = os.path.getmtime(file_path)
        time_difference = current_time - file_mod_time
        if time_difference > 24 * 60 * 60:
            os.remove(file_path)

    if not os.path.exists(file_path):

        resolver = get_resolver()
        match = resolver.resolve("/" + path)
        request.user = AnonymousUser()
        response = match.func(request, *match.args, **match.kwargs)
        if response.status_code == 200:
            directory = os.path.dirname(file_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            json_content = JSONRenderer().render(response.data)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(
                    json_content.decode("utf-8")
                    .replace('"@id":"' + server_url, '"@id":"' + server_url + "/ssr")
                    .replace(
                        '"@id":"' + server_url + "/ssr/ssr",
                        '"@id":"' + server_url + "/ssr",
                    )[:-1]
                    + ',"@context": "'
                    + getattr(
                        settings,
                        "LDP_RDF_CONTEXT",
                        "https://cdn.startinblox.com/owl/context.jsonld",
                    )
                    + '"}'
                )

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        try:
            json_content = json.loads(content)
            return JsonResponse(
                json_content,
                safe=False,
                status=200,
                content_type="application/ld+json",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=3600",
                },
            )
        except json.JSONDecodeError:
            pass

    return HttpResponseNotFound("File not found")
