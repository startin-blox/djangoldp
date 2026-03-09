import json
import os
import time
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.urls.resolvers import get_resolver
from rest_framework.renderers import JSONRenderer

BASE_URL = getattr(settings, "BASE_URL", "http://localhost")
PARSED_BASE_URL = urlparse(BASE_URL)
RDF_CONTEXT = getattr(
    settings,
    "LDP_RDF_CONTEXT",
    "https://cdn.startinblox.com/owl/context.jsonld",
)
_resolver_cache = None


def get_resolver_cached():
    global _resolver_cache
    if _resolver_cache is None:
        _resolver_cache = get_resolver()
    return _resolver_cache


def rewrite_ids(data):
    if isinstance(data, dict):
        if "@id" in data:
            original_id = data["@id"]
            if original_id.startswith(BASE_URL) and "/ssr" not in original_id:
                path = urlparse(original_id).path
                if path.startswith(PARSED_BASE_URL.path):
                    path = path[len(PARSED_BASE_URL.path) :]
                data["@id"] = urljoin(BASE_URL, "/ssr" + path)
            elif "/ssr/ssr" in original_id:
                data["@id"] = original_id.replace("/ssr/ssr", "/ssr")
        for value in data.values():
            rewrite_ids(value)
    elif isinstance(data, list):
        for item in data:
            rewrite_ids(item)
    return data


def get_response_from_view(path, method="GET", depth=None):
    resolver = get_resolver_cached()
    from urllib.parse import parse_qs

    from django.test import RequestFactory

    query_string = None
    if "?" in path:
        path, query_string = path.split("?", 1)

    match = None
    resolve_path = "/" + path

    try:
        match = resolver.resolve(resolve_path)
    except Exception:
        try:
            match = resolver.resolve(resolve_path + "/")
            resolve_path = resolve_path + "/"
        except Exception:
            return None

    factory = RequestFactory()

    get_params = {}
    if query_string:
        parsed_params = parse_qs(query_string)
        get_params = {k: v[0] if len(v) == 1 else v for k, v in parsed_params.items()}

    extra_headers = {
        "HTTP_HOST": PARSED_BASE_URL.netloc,
        "SERVER_NAME": PARSED_BASE_URL.hostname,
        "SERVER_PORT": PARSED_BASE_URL.port
        or (443 if PARSED_BASE_URL.scheme == "https" else 80),
        "HTTP_X_FORWARDED_PROTO": PARSED_BASE_URL.scheme,
    }

    if depth is not None:
        extra_headers["HTTP_DEPTH"] = str(depth)

    if method == "GET":
        request = factory.get(resolve_path, data=get_params, **extra_headers)
    else:
        request = factory.post(
            resolve_path, data=get_params if method == "POST" else None, **extra_headers
        )

    request.user = AnonymousUser()
    request.META["HTTP_X_FORWARDED_PROTO"] = PARSED_BASE_URL.scheme
    response = match.func(request, *match.args, **match.kwargs)
    return response


def extract_content_from_response(response):
    if hasattr(response, "data"):
        return JSONRenderer().render(response.data).decode("utf-8")
    else:
        return response.content.decode("utf-8")


def build_file_path(output_dir, path):
    file_path = os.path.join(output_dir, path.rstrip("/"))
    if "?" in file_path:
        file_path = file_path.split("?")[0]
    if not file_path.endswith(".jsonld"):
        file_path += ".jsonld"
    return file_path


def save_content_to_file(file_path, content):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def is_cache_expired(file_path, max_age_hours=24):
    if not os.path.exists(file_path):
        return True
    current_time = time.time()
    file_mod_time = os.path.getmtime(file_path)
    return current_time - file_mod_time > max_age_hours * 60 * 60


def read_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, IOError):
        return None


def process_content(content, add_context=True):
    try:
        data = json.loads(content)
        rewrite_ids(data)
        if add_context and isinstance(data, dict) and "@context" not in data:
            data["@context"] = RDF_CONTEXT
        return json.dumps(data)
    except json.JSONDecodeError:
        return content


def ensure_directory(directory):
    os.makedirs(directory, exist_ok=True)


def get_model_from_path(path):
    from django.apps import apps

    path_stripped = path.rstrip("/").split("?")[0]

    for model in apps.get_models():
        if hasattr(model._meta, "static_version"):
            container_path = model.get_container_path()
            if container_path.startswith("/"):
                container_path = container_path[1:]
            if container_path in path_stripped or path_stripped.startswith(
                container_path
            ):
                return model

    return None
