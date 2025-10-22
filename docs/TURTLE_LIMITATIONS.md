# Turtle Renderer Limitations and JSON-LD vs Turtle Differences

**Generated:** 2025-10-22
**Issue:** Turtle (TTL) responses are incomplete compared to JSON-LD responses

---

## The Problem

When retrieving resources in Turtle format (`Accept: text/turtle`), the response appears "incomplete" compared to the JSON-LD version. This is **not a bug** but a fundamental difference between how JSON-LD and RDF/Turtle represent nested data.

### Example

**JSON-LD Response** (`Accept: application/ld+json`):
```json
{
  "@context": "https://cdn.startinblox.com/owl/context.jsonld",
  "@id": "http://localhost:8000/users/",
  "@type": "ldp:BasicContainer",
  "ldp:contains": [
    {
      "@id": "http://localhost:8000/users/user1/",
      "username": "user1",
      "email": "user1@example.com",
      "first_name": "John"
    },
    {
      "@id": "http://localhost:8000/users/user2/",
      "username": "user2",
      "email": "user2@example.com",
      "first_name": "Jane"
    }
  ]
}
```

**Turtle Response** (`Accept: text/turtle`):
```turtle
@prefix ldp: <http://www.w3.org/ns/ldp#> .

<http://localhost:8000/users/> a ldp:BasicContainer ;
    ldp:contains <http://localhost:8000/users/user1/>,
                 <http://localhost:8000/users/user2/> .
```

**Notice:** The Turtle version only has the `@id` URIs, not the nested properties!

---

## Why This Happens

### RDF Triple Structure

RDF (which Turtle represents) stores data as **triples**:

```
Subject → Predicate → Object
```

For example:
```turtle
<http://localhost:8000/users/user1/> <http://example.org/username> "user1" .
```

### The Conversion Process

When `TurtleRenderer` converts JSON-LD to Turtle:

1. **Step 1:** JSON-LD data is passed to `rdflib.Graph.parse(format='json-ld')`
2. **Step 2:** rdflib extracts RDF triples from the JSON-LD
3. **Step 3:** Only triples about the **main subject** (`http://localhost:8000/users/`) are extracted
4. **Step 4:** Nested objects are reduced to **URI references only**

### Why Nested Properties Are Lost

In the JSON-LD example above:
- The main resource is `http://localhost:8000/users/` (the container)
- The nested user objects have their own `@id` values
- In RDF semantics, these are **separate resources**
- The container only has a relationship (`ldp:contains`) to their URIs

To include the nested user properties in Turtle, you would need:

```turtle
<http://localhost:8000/users/> a ldp:BasicContainer ;
    ldp:contains <http://localhost:8000/users/user1/>,
                 <http://localhost:8000/users/user2/> .

# These are SEPARATE resources:
<http://localhost:8000/users/user1/> a <http://example.org/User> ;
    <http://example.org/username> "user1" ;
    <http://example.org/email> "user1@example.com" ;
    <http://example.org/first_name> "John" .

<http://localhost:8000/users/user2/> a <http://example.org/User> ;
    <http://example.org/username> "user2" ;
    <http://example.org/email> "user2@example.com" ;
    <http://example.org/first_name> "Jane" .
```

But the current serializer **only serializes the main resource**, not nested resources.

---

## JSON-LD vs Turtle Philosophy

### JSON-LD Approach
- **Document-oriented**: Can embed complete nested objects
- **Flexible**: Can mix references (`@id` only) and embedded data
- **Compact**: Nested data is inline for convenience
- **Use case**: API responses where you want "everything in one request"

### Turtle/RDF Approach
- **Graph-oriented**: Each resource is separate
- **Link-based**: Resources reference each other by URI
- **Distributed**: Clients follow links to get full data
- **Use case**: Linked Data where resources are distributed across servers

---

## The Root Cause in DjangoLDP

DjangoLDP's serializers create **embedded JSON-LD representations** for convenience:

```python
# DjangoLDP serializes nested objects WITH their properties:
{
  "ldp:contains": [
    {
      "@id": "http://localhost:8000/users/user1/",
      "username": "user1",  # ← Embedded data
      "email": "user1@example.com"
    }
  ]
}
```

However, when `rdflib` parses this JSON-LD:
- It recognizes each nested object with an `@id` as a **distinct resource**
- It creates triples linking the main resource to the nested resource URIs
- It **does NOT** create triples for the nested resource properties (they're not "about" the main subject)

---

## Current Implementation

### renderers.py (lines 65-99)

```python
def render(self, data, accepted_media_type=None, renderer_context=None):
    if data is None:
        return b''

    g = Graph()

    try:
        json_str = json.dumps(data)
        g.parse(data=json_str, format='json-ld')  # ← Here's where data is lost
        turtle_str = g.serialize(format='turtle')
        return turtle_str.encode('utf-8') if isinstance(turtle_str, str) else turtle_str
    except Exception as e:
        logger.warning(f"Failed to parse JSON-LD to Turtle: {str(e)}")
        # Falls back to simple_jsonld_to_turtle()
```

**The Issue:**
- `g.parse()` creates triples for the graph
- But it only includes triples where the **main resource** is the subject
- Nested resources are treated as separate entities

---

## Solutions & Workarounds

### Option 1: Accept the Limitation (Current Behavior)

**Pros:**
- Follows RDF semantics correctly
- Clients should follow links to get full data
- Consistent with Linked Data principles

**Cons:**
- Turtle responses appear "incomplete"
- Requires multiple HTTP requests to get full data

**Recommendation:** This is **correct RDF behavior**. Clients expecting full nested data should use JSON-LD.

---

### Option 2: Flatten JSON-LD Before Conversion

Modify the renderer to expand all nested resources into top-level triples:

```python
from pyld import jsonld

def render(self, data, accepted_media_type=None, renderer_context=None):
    if data is None:
        return b''

    g = Graph()

    try:
        # Expand JSON-LD to include all nested resources
        expanded = jsonld.expand(data)

        # Parse expanded JSON-LD (includes all nested triples)
        g.parse(data=json.dumps(expanded), format='json-ld')

        turtle_str = g.serialize(format='turtle')
        return turtle_str.encode('utf-8') if isinstance(turtle_str, str) else turtle_str
    except Exception as e:
        logger.warning(f"Failed to parse JSON-LD to Turtle: {str(e)}")
        # Fallback...
```

**Pros:**
- Includes all nested resource data
- Complete Turtle representation

**Cons:**
- May violate separation of concerns (mixing multiple resources in one response)
- Larger responses
- Not standard LDP behavior

---

### Option 3: Custom Turtle Serializer

Write a custom serializer that explicitly handles nested DjangoLDP patterns:

```python
def render_complete_turtle(self, data, renderer_context=None):
    """
    Render JSON-LD to Turtle, including nested resources.
    """
    g = Graph()

    # Recursively process all objects with @id
    def add_resource_to_graph(resource_data, graph):
        if not isinstance(resource_data, dict):
            return

        subject_uri = resource_data.get('@id')
        if not subject_uri:
            return

        subject = URIRef(subject_uri)

        # Add all properties
        for key, value in resource_data.items():
            if key in ['@id', '@type', '@context']:
                continue

            predicate = URIRef(expand_key(key))  # Expand using context

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and '@id' in item:
                        # Add reference and recurse
                        graph.add((subject, predicate, URIRef(item['@id'])))
                        add_resource_to_graph(item, graph)  # ← Recurse!
                    else:
                        graph.add((subject, predicate, Literal(item)))
            elif isinstance(value, dict) and '@id' in value:
                graph.add((subject, predicate, URIRef(value['@id'])))
                add_resource_to_graph(value, graph)  # ← Recurse!
            else:
                graph.add((subject, predicate, Literal(value)))

    add_resource_to_graph(data, g)
    return g.serialize(format='turtle')
```

**Pros:**
- Complete control over serialization
- Can handle DjangoLDP-specific patterns
- Includes all nested data

**Cons:**
- Complex implementation
- Must maintain separately from JSON-LD serialization
- Potential namespace/context issues

---

## Recommendations

### Short Term: Document the Behavior

1. **Update API documentation** to explain:
   - JSON-LD responses include embedded nested data
   - Turtle responses follow RDF semantics (URIs only for separate resources)
   - Clients needing full nested data should use `Accept: application/ld+json`

2. **Add response headers** to guide clients:
   ```python
   # In TurtleRenderer
   response['X-LDP-Serialization'] = 'turtle-references-only'
   response['X-LDP-Full-Data-Format'] = 'application/ld+json'
   ```

### Medium Term: Implement Option 2 (JSON-LD Expansion)

Modify `TurtleRenderer` to use `jsonld.expand()` before parsing. This will:
- Include all nested resource triples
- Maintain RDF correctness
- Provide complete data in Turtle format

**Implementation:**
```python
# In renderers.py, modify TurtleRenderer.render():

from pyld import jsonld as pyld_jsonld

def render(self, data, accepted_media_type=None, renderer_context=None):
    if data is None:
        return b''

    g = Graph()

    try:
        # Expand JSON-LD to include all nested resources
        expanded = pyld_jsonld.expand(data)

        # Parse the expanded JSON-LD
        g.parse(data=json.dumps(expanded), format='json-ld')

        turtle_str = g.serialize(format='turtle')
        if isinstance(turtle_str, str):
            return turtle_str.encode('utf-8')
        return turtle_str
    except Exception as e:
        logger.warning(f"Failed to parse JSON-LD to Turtle: {str(e)}, falling back")
        # Existing fallback logic...
```

### Long Term: Configurable Serialization Depth

Add a configuration option:

```python
# In settings
TURTLE_SERIALIZATION_MODE = 'references-only'  # or 'full-graph'
```

This allows administrators to choose the behavior based on their use case.

---

## Testing Recommendations

1. **Add test for nested resource serialization:**
   ```python
   def test_turtle_nested_resources(self):
       """Verify Turtle handles nested resources appropriately."""
       data = {
           '@id': 'http://example.org/container/',
           'ldp:contains': [
               {
                   '@id': 'http://example.org/item1/',
                   'title': 'Item 1'
               }
           ]
       }

       renderer = TurtleRenderer()
       result = renderer.render(data)

       # Should include reference to nested resource
       self.assertIn('http://example.org/item1/', result.decode())

       # Document current behavior: nested properties NOT included
       # (unless we implement expansion)
       # self.assertNotIn('Item 1', result.decode())
   ```

2. **Add integration test comparing JSON-LD vs Turtle field counts**

3. **Add documentation test showing expected differences**

---

## Conclusion

The "incomplete" Turtle responses are a result of **correct RDF semantics**, not a bug. JSON-LD allows embedded data for convenience, but RDF/Turtle treats each resource as a distinct entity connected by URIs.

**Recommended Action:**
- **Document this behavior** for API users
- **Consider implementing JSON-LD expansion** (Option 2) to include full nested data
- **Update the skipped test** in `test_ldp_compliance.py:295-302`

This is why the TODO comment exists:
```python
# TODO: Improve TurtleRenderer to ensure all fields are properly serialized
self.skipTest("Turtle serializer needs improvements for full field preservation")
```

The "improvement" needed is **JSON-LD expansion before RDF conversion**.
