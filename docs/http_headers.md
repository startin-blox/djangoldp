# HTTP Headers Reference

**Version**: DjangoLDP 5.0+

This document describes all HTTP headers supported by DjangoLDP for W3C LDP compliance, caching, and content negotiation.

---

## Request Headers

### Content Negotiation

| Header | Values | Description |
|--------|--------|-------------|
| `Accept` | `application/ld+json`, `text/turtle` | Preferred response format |
| `Content-Type` | `application/ld+json`, `text/turtle` | Request body format |

**Example:**
```bash
# Request Turtle, send JSON-LD
curl -H "Accept: text/turtle" \
     -H "Content-Type: application/ld+json" \
     -X POST -d '{"username":"test"}' \
     http://localhost:8000/users/
```

### Conditional Requests (RFC 7232)

| Header | Description | Example |
|--------|-------------|---------|
| `If-Match` | Update only if ETag matches | `If-Match: W/"abc123"` |
| `If-None-Match` | Return 304 if unchanged | `If-None-Match: W/"abc123"` |
| `If-Modified-Since` | Return 304 if not modified | `If-Modified-Since: Mon, 21 Oct 2025 12:00:00 GMT` |

**Conditional Update:**
```bash
curl -X PUT \
     -H 'If-Match: W/"abc123"' \
     -H 'Content-Type: application/ld+json' \
     -d '{"username":"updated"}' \
     http://localhost:8000/users/1/
```

**Cache Validation:**
```bash
curl -H 'If-None-Match: W/"abc123"' http://localhost:8000/users/1/
# Returns 304 Not Modified if unchanged
```

### Prefer Header (RFC 7240)

| Value | Behavior |
|-------|----------|
| `return=minimal` | Return 204 No Content after write operations |
| `return=representation` | Return full resource in response (default) |

**Minimal Response:**
```bash
curl -X POST \
     -H 'Prefer: return=minimal' \
     -H 'Content-Type: application/ld+json' \
     -d '{"username":"newuser"}' \
     http://localhost:8000/users/
# Returns: 204 No Content + Location header
```

---

## Response Headers

### LDP Link Headers

DjangoLDP adds Link headers to indicate resource types per W3C LDP specification.

**Container Responses:**
```
Link: <http://www.w3.org/ns/ldp#Resource>; rel="type"
Link: <http://www.w3.org/ns/ldp#RDFSource>; rel="type"
Link: <http://www.w3.org/ns/ldp#Container>; rel="type"
Link: <http://www.w3.org/ns/ldp#BasicContainer>; rel="type"
```

**Resource (Detail) Responses:**
```
Link: <http://www.w3.org/ns/ldp#Resource>; rel="type"
Link: <http://www.w3.org/ns/ldp#RDFSource>; rel="type"
```

**Created Resource (201 Response):**
```
Link: <http://www.w3.org/ns/ldp#Resource>; rel="type"
Location: http://localhost:8000/users/123/
```

### Pagination Link Headers

When pagination is enabled, Link headers follow RFC 8288:

```
Link: <http://localhost:8000/users/?page=1>; rel="first"
Link: <http://localhost:8000/users/?page=10>; rel="last"
Link: <http://localhost:8000/users/?page=3>; rel="prev"
Link: <http://localhost:8000/users/?page=5>; rel="next"
Link: <http://www.w3.org/ns/ldp#BasicContainer>; rel="type"
```

### Caching Headers

| Header | Description | Example |
|--------|-------------|---------|
| `ETag` | Resource version identifier | `ETag: W/"5d41402abc4b2a76b9719d911017c592"` |
| `Last-Modified` | Last modification timestamp | `Last-Modified: Mon, 21 Oct 2025 12:34:56 GMT` |

**ETag Format:**
- Uses weak ETags: `W/"hash"`
- Hash is MD5 of resource data
- Changes when resource is modified

**Container ETags:**
- Based on contained resources
- Changes when any contained resource changes

### Content Headers

| Header | Description | Example |
|--------|-------------|---------|
| `Content-Type` | Response format | `application/ld+json; charset=utf-8` |
| `Accept-Post` | Accepted POST formats | `application/ld+json, text/turtle` |
| `Accept-Patch` | Accepted PATCH formats | `application/ld+json, text/turtle` |
| `Allow` | Allowed HTTP methods | `GET, POST, HEAD, OPTIONS` |

### Preference Response Headers

| Header | Description | Example |
|--------|-------------|---------|
| `Preference-Applied` | Confirms applied preference | `Preference-Applied: return=minimal` |

---

## CORS Headers

### Exposed Headers

All LDP-relevant headers are exposed for JavaScript clients:

```
Access-Control-Expose-Headers: Link, ETag, Last-Modified, Accept-Post, Accept-Patch, Preference-Applied, Location, User, Allow
```

This allows client-side JavaScript to access:

```javascript
const response = await fetch('/users/');

// These are now accessible
const etag = response.headers.get('ETag');
const links = response.headers.get('Link');
const lastModified = response.headers.get('Last-Modified');
```

### CORS Configuration

Default CORS headers in DjangoLDP:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: authorization, Content-Type, if-match, accept, DPoP
```

Configure additional headers in settings:

```python
# settings.py
OIDC_ACCESS_CONTROL_ALLOW_HEADERS = 'authorization, Content-Type, if-match, accept, DPoP, X-Custom-Header'
```

---

## OPTIONS Method

The OPTIONS method returns available actions and formats:

**Container OPTIONS:**
```bash
curl -X OPTIONS http://localhost:8000/users/
```

Response:
```
HTTP/1.1 200 OK
Allow: GET, POST, HEAD, OPTIONS
Accept-Post: application/ld+json, text/turtle
Link: <http://www.w3.org/ns/ldp#BasicContainer>; rel="type"
Link: <http://www.w3.org/ns/ldp#Resource>; rel="type"
Link: <http://www.w3.org/ns/ldp#RDFSource>; rel="type"
Content-Length: 0
```

**Resource OPTIONS:**
```bash
curl -X OPTIONS http://localhost:8000/users/1/
```

Response:
```
HTTP/1.1 200 OK
Allow: GET, PUT, PATCH, DELETE, HEAD, OPTIONS
Accept-Patch: application/ld+json, text/turtle
Link: <http://www.w3.org/ns/ldp#Resource>; rel="type"
Link: <http://www.w3.org/ns/ldp#RDFSource>; rel="type"
Content-Length: 0
```

---

## Status Codes

### Successful Responses

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | GET, PUT, PATCH with body |
| 201 | Created | POST creating new resource |
| 204 | No Content | DELETE, or write with `Prefer: return=minimal` |
| 304 | Not Modified | GET with valid If-None-Match or If-Modified-Since |

### Client Errors

| Code | Meaning | When Used |
|------|---------|-----------|
| 400 | Bad Request | Invalid request body |
| 404 | Not Found | Resource doesn't exist |
| 405 | Method Not Allowed | HTTP method not supported |
| 406 | Not Acceptable | Unsupported Accept type |
| 412 | Precondition Failed | If-Match ETag doesn't match |
| 415 | Unsupported Media Type | Unsupported Content-Type |

---

## Complete Examples

### Create Resource with All Headers

```bash
curl -X POST \
     -H 'Content-Type: application/ld+json' \
     -H 'Accept: application/ld+json' \
     -H 'Prefer: return=representation' \
     -d '{"username": "newuser", "email": "new@example.com"}' \
     http://localhost:8000/users/
```

Response:
```
HTTP/1.1 201 Created
Content-Type: application/ld+json; charset=utf-8
Location: http://localhost:8000/users/123/
ETag: W/"abc123"
Last-Modified: Mon, 21 Oct 2025 12:34:56 GMT
Preference-Applied: return=representation
Link: <http://www.w3.org/ns/ldp#Resource>; rel="type"

{"@id": "http://localhost:8000/users/123/", "username": "newuser", ...}
```

### Conditional Update

```bash
# First, get current ETag
curl -I http://localhost:8000/users/123/
# ETag: W/"abc123"

# Update with condition
curl -X PUT \
     -H 'If-Match: W/"abc123"' \
     -H 'Content-Type: application/ld+json' \
     -H 'Prefer: return=minimal' \
     -d '{"username": "updated"}' \
     http://localhost:8000/users/123/
```

Response (success):
```
HTTP/1.1 204 No Content
ETag: W/"def456"
Preference-Applied: return=minimal
```

Response (conflict):
```
HTTP/1.1 412 Precondition Failed
Content-Type: application/json

{"detail": "ETag mismatch - resource was modified"}
```

### Cache Validation Flow

```bash
# Initial request
curl -i http://localhost:8000/users/
# Returns: ETag: W/"container-hash"

# Subsequent request (cached)
curl -H 'If-None-Match: W/"container-hash"' http://localhost:8000/users/
# Returns: 304 Not Modified (if unchanged)
# Returns: 200 OK with new ETag (if changed)
```

---

## JavaScript Client Example

```javascript
class LDPClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.etags = new Map();
  }

  async get(path, format = 'application/ld+json') {
    const url = `${this.baseUrl}${path}`;
    const headers = { 'Accept': format };

    // Use cached ETag if available
    const cachedEtag = this.etags.get(url);
    if (cachedEtag) {
      headers['If-None-Match'] = cachedEtag;
    }

    const response = await fetch(url, { headers });

    if (response.status === 304) {
      console.log('Using cached version');
      return null; // Use cached data
    }

    // Cache the new ETag
    const newEtag = response.headers.get('ETag');
    if (newEtag) {
      this.etags.set(url, newEtag);
    }

    return response.json();
  }

  async update(path, data) {
    const url = `${this.baseUrl}${path}`;
    const etag = this.etags.get(url);

    const headers = {
      'Content-Type': 'application/ld+json',
      'Prefer': 'return=representation'
    };

    // Conditional update
    if (etag) {
      headers['If-Match'] = etag;
    }

    const response = await fetch(url, {
      method: 'PUT',
      headers,
      body: JSON.stringify(data)
    });

    if (response.status === 412) {
      throw new Error('Resource was modified by another user');
    }

    // Update cached ETag
    const newEtag = response.headers.get('ETag');
    if (newEtag) {
      this.etags.set(url, newEtag);
    }

    return response.json();
  }

  async create(containerPath, data, minimal = false) {
    const url = `${this.baseUrl}${containerPath}`;

    const headers = {
      'Content-Type': 'application/ld+json',
      'Prefer': minimal ? 'return=minimal' : 'return=representation'
    };

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });

    const location = response.headers.get('Location');
    const etag = response.headers.get('ETag');

    if (etag && location) {
      this.etags.set(location, etag);
    }

    if (response.status === 204) {
      return { location };
    }

    return {
      location,
      data: await response.json()
    };
  }
}

// Usage
const client = new LDPClient('http://localhost:8000');

// GET with caching
const users = await client.get('/users/');

// Create with minimal response
const { location } = await client.create('/users/', { username: 'test' }, true);

// Conditional update
await client.update('/users/1/', { username: 'updated' });
```

---

## Related Documentation

- [BRANCH_CHANGELOG.md](BRANCH_CHANGELOG.md) - Version history
- [turtle_serialization.md](turtle_serialization.md) - Turtle format guide
- [LDP_COMPLIANCE_STATUS.md](../LDP_COMPLIANCE_STATUS.md) - W3C compliance status
