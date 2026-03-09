import logging
import os

from django.http import HttpResponseNotFound, JsonResponse

from .static_helpers import (
    build_file_path,
    extract_content_from_response,
    get_response_from_view,
    is_cache_expired,
    process_content,
    read_json_file,
    save_content_to_file,
)

logger = logging.getLogger("djangoldp")


def serve_static_content(request, path):
    if request.method == "OPTIONS":
        return JsonResponse(
            {},
            safe=False,
            status=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    if request.method != "GET":
        response = get_response_from_view(path, request.method)
        return response

    is_filtered = request.GET.get("search-fields", False)
    output_dir = "ssr" if not is_filtered else "ssr_filtered"

    file_path = build_file_path(output_dir, path)

    if os.path.exists(file_path) and is_cache_expired(file_path):
        os.remove(file_path)

    if not os.path.exists(file_path):
        response = get_response_from_view(path)
        if response and response.status_code == 200:
            content = extract_content_from_response(response)
            processed_content = process_content(content, add_context=True)
            save_content_to_file(file_path, processed_content)

    if os.path.exists(file_path):
        json_content = read_json_file(file_path)
        if json_content:
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

    return HttpResponseNotFound("File not found")
