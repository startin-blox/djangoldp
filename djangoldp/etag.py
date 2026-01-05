"""
ETag generation utilities for DjangoLDP resources and containers.

Implements W3C LDP compliance for entity tag support.
"""

import hashlib
import json
from typing import Optional, Any
from django.core.exceptions import FieldDoesNotExist
from django.db.models import QuerySet

# Constant for timestamp conversion
TIMESTAMP_TO_MICROSECONDS = 1000000


def normalize_etag(etag_str):
    """
    Normalize ETag for comparison.

    Args:
        etag_str: ETag string from header

    Returns:
        tuple: (is_weak: bool, etag_value: str)
    """
    if not etag_str:
        return False, ""

    etag_str = etag_str.strip()
    is_weak = etag_str.startswith('W/')
    if is_weak:
        etag_str = etag_str[2:]
    return is_weak, etag_str.strip('"')


def generate_etag(obj: Any, serialized_data: Optional[dict] = None) -> str:
    """
    Generate weak ETag for a model instance.
    Uses object's updated_at if available, otherwise hashes serialized content.

    Args:
        obj: Django model instance
        serialized_data: Optional serialized representation of the object

    Returns:
        str: Weak ETag value in format W/"hash"
    """
    # Try timestamp-based ETag first (more efficient)
    if hasattr(obj, 'updated_at') and obj.updated_at:
        try:
            timestamp = obj.updated_at.timestamp()
            timestamp_micro = int(timestamp * TIMESTAMP_TO_MICROSECONDS)
            return f'W/"{timestamp_micro}"'
        except (AttributeError, ValueError, TypeError):
            # Fall through to content-based ETag
            pass

    # Fall back to content-based ETag
    try:
        if serialized_data:
            content = json.dumps(serialized_data, sort_keys=True)
        else:
            # Use pk and model name as minimal identifier
            content = f"{obj.__class__.__name__}:{obj.pk}"
    except (TypeError, ValueError):
        # If serialization fails, use minimal identifier
        content = f"{obj.__class__.__name__}:{obj.pk}"

    # Use SHA256 instead of MD5 for better security
    hash_value = hashlib.sha256(content.encode()).hexdigest()[:32]  # Truncate to 32 chars
    return f'W/"{hash_value}"'  # Weak ETag


def generate_container_etag(queryset: QuerySet, count: int, page_number: Optional[int] = None) -> str:
    """
    Generate weak ETag for a container.
    Based on count, latest modification time, and optional page number.

    Args:
        queryset: Django QuerySet for the container
        count: Number of items in the container (total count, not page size)
        page_number: Optional page number for paginated containers

    Returns:
        str: Weak ETag value for the container in format W/"hash"
    """
    latest_updated = None

    # Check if model has updated_at field using FieldDoesNotExist
    try:
        queryset.model._meta.get_field('updated_at')
        # Field exists, get the latest timestamp
        latest_timestamp = queryset.order_by('-updated_at').values_list('updated_at', flat=True).first()
        if latest_timestamp:
            try:
                latest_updated = latest_timestamp.timestamp()
            except (AttributeError, ValueError, TypeError):
                pass
    except FieldDoesNotExist:
        # Field doesn't exist, continue with fallback
        pass

    if latest_updated:
        timestamp_micro = int(latest_updated * TIMESTAMP_TO_MICROSECONDS)
        etag_content = f"{count}:{timestamp_micro}"
    else:
        # Fallback: use count and deterministic hash of query
        query_str = str(queryset.query)
        # Use SHA256 for deterministic hashing instead of built-in hash()
        query_hash = hashlib.sha256(query_str.encode()).hexdigest()[:16]
        etag_content = f"{count}:{query_hash}"

    # Include page number in ETag if paginated
    if page_number is not None:
        etag_content = f"{etag_content}:page{page_number}"

    # Use SHA256 for final hash
    hash_value = hashlib.sha256(etag_content.encode()).hexdigest()[:32]  # Truncate to 32 chars
    return f'W/"{hash_value}"'
