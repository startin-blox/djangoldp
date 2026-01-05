# Turtle Serialization Guide

**Version**: DjangoLDP 5.0+
**W3C Specification**: [RDF 1.1 Turtle](https://www.w3.org/TR/turtle/)

This guide explains how to use Turtle (TTL) serialization in DjangoLDP for RDF-based data exchange.

---

## Overview

Turtle (Terse RDF Triple Language) is a text-based format for representing RDF data. DjangoLDP supports Turtle as an alternative to JSON-LD, allowing clients to request and submit data in either format.

### When to Use Turtle

| Use Case | Recommended Format |
|----------|-------------------|
| Web applications (JavaScript) | JSON-LD |
| RDF tooling (Protege, rdflib) | Turtle |
| Human readability | Turtle |
| Nested data preservation | JSON-LD |
| SPARQL integration | Turtle |
| Linked Data crawlers | Either |

---

## Content Negotiation

### Requesting Turtle

Use the `Accept` header to request Turtle format:

```bash
# Request Turtle format
curl -H "Accept: text/turtle" http://localhost:8000/users/

# Request JSON-LD format (default)
curl -H "Accept: application/ld+json" http://localhost:8000/users/
```

### Supported Media Types

| Media Type | Format | Description |
|------------|--------|-------------|
| `application/ld+json` | JSON-LD | Default, full nested data |
| `text/turtle` | Turtle | RDF triple format |
| `application/json` | JSON | Falls back to JSON-LD |

---

## Response Examples

### Container Response (List)

**Request:**
```bash
curl -H "Accept: text/turtle" http://localhost:8000/users/
```

**Response:**
```turtle
@prefix ldp: <http://www.w3.org/ns/ldp#> .
@prefix hd: <http://happy-dev.fr/owl/#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://localhost:8000/users/> a ldp:BasicContainer ;
    ldp:contains <http://localhost:8000/users/1/>,
                 <http://localhost:8000/users/2/> .

<http://localhost:8000/users/1/> a hd:user ;
    hd:username "alice" ;
    hd:email "alice@example.com" ;
    hd:first_name "Alice" .

<http://localhost:8000/users/2/> a hd:user ;
    hd:username "bob" ;
    hd:email "bob@example.com" ;
    hd:first_name "Bob" .
```

### Resource Response (Detail)

**Request:**
```bash
curl -H "Accept: text/turtle" http://localhost:8000/users/1/
```

**Response:**
```turtle
@prefix hd: <http://happy-dev.fr/owl/#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://localhost:8000/users/1/> a hd:user ;
    hd:username "alice" ;
    hd:email "alice@example.com" ;
    hd:first_name "Alice" ;
    hd:last_name "Smith" ;
    hd:created_at "2025-01-01T00:00:00Z"^^xsd:dateTime .
```

---

## Sending Turtle Data

### Creating Resources (POST)

```bash
curl -X POST \
  -H "Content-Type: text/turtle" \
  -d '@prefix hd: <http://happy-dev.fr/owl/#> .
      <> a hd:user ;
         hd:username "newuser" ;
         hd:email "newuser@example.com" ;
         hd:first_name "New" ;
         hd:last_name "User" .' \
  http://localhost:8000/users/
```

**Notes:**
- Use `<>` as the subject (represents the resource being created)
- The server assigns the actual URI
- Response includes `Location` header with the new resource URI

### Updating Resources (PUT)

```bash
curl -X PUT \
  -H "Content-Type: text/turtle" \
  -H "If-Match: W/\"abc123\"" \
  -d '@prefix hd: <http://happy-dev.fr/owl/#> .
      <http://localhost:8000/users/1/> a hd:user ;
         hd:username "alice_updated" ;
         hd:email "alice.new@example.com" .' \
  http://localhost:8000/users/1/
```

**Notes:**
- Use the full URI as the subject
- Include `If-Match` header for conditional updates
- PUT replaces the entire resource

### Partial Updates (PATCH)

```bash
curl -X PATCH \
  -H "Content-Type: text/turtle" \
  -d '@prefix hd: <http://happy-dev.fr/owl/#> .
      <http://localhost:8000/users/1/> hd:email "newemail@example.com" .' \
  http://localhost:8000/users/1/
```

---

## Turtle Syntax Quick Reference

### Basic Structure

```turtle
# Prefix declarations
@prefix ldp: <http://www.w3.org/ns/ldp#> .
@prefix hd: <http://happy-dev.fr/owl/#> .

# Subject-predicate-object triples
<http://example.org/resource> a hd:SomeType ;
    hd:property1 "value1" ;
    hd:property2 "value2" .
```

### Common Patterns

```turtle
# Type declaration
<resource> a hd:Type .
# Equivalent to: <resource> rdf:type hd:Type .

# Multiple predicates (same subject)
<resource> hd:prop1 "val1" ;
           hd:prop2 "val2" .

# Multiple objects (same predicate)
<resource> hd:tags "tag1", "tag2", "tag3" .

# Typed literals
<resource> hd:count "42"^^xsd:integer .
<resource> hd:date "2025-01-01"^^xsd:date .

# Language-tagged strings
<resource> hd:name "Hello"@en .
<resource> hd:name "Bonjour"@fr .

# Blank nodes
<resource> hd:address [
    hd:street "123 Main St" ;
    hd:city "Paris"
] .

# References to other resources
<resource> hd:creator <http://example.org/users/1/> .
```

---

## RDF Context Configuration

### Default Context

DjangoLDP uses a JSON-LD context for vocabulary resolution:

```python
# settings.py
LDP_RDF_CONTEXT = 'https://cdn.happy-dev.fr/owl/hdcontext.jsonld'
```

### Model RDF Types

Configure RDF types in your model Meta:

```python
from djangoldp.models import Model
from django.db import models

class Project(Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    class Meta(Model.Meta):
        rdf_type = 'hd:project'  # Maps to the ontology
        container_path = 'projects'
```

### Custom Context

Add additional context mappings per model:

```python
class Project(Model):
    # ...

    class Meta(Model.Meta):
        rdf_type = 'hd:project'
        rdf_context = {
            'customField': 'http://example.org/vocab#customField'
        }
```

---

## Nested Resources

### Understanding Nested Data

In Turtle/RDF, nested objects become separate resources linked by URI references:

**JSON-LD (embedded):**
```json
{
  "@id": "http://localhost:8000/projects/1/",
  "name": "My Project",
  "owner": {
    "@id": "http://localhost:8000/users/1/",
    "username": "alice"
  }
}
```

**Turtle (linked):**
```turtle
<http://localhost:8000/projects/1/> a hd:project ;
    hd:name "My Project" ;
    hd:owner <http://localhost:8000/users/1/> .

<http://localhost:8000/users/1/> a hd:user ;
    hd:username "alice" .
```

### Serialization Behavior

DjangoLDP's Turtle renderer includes nested resource data:

1. **Primary resource** - Full serialization
2. **Referenced resources** - Included with their properties
3. **Deep nesting** - Recursively processed

See `docs/TURTLE_LIMITATIONS.md` for detailed technical explanation.

---

## Programmatic Usage

### Python Client (rdflib)

```python
from rdflib import Graph
import requests

# Fetch Turtle data
response = requests.get(
    'http://localhost:8000/users/',
    headers={'Accept': 'text/turtle'}
)

# Parse into RDF graph
g = Graph()
g.parse(data=response.text, format='turtle')

# Query the graph
for subject, predicate, obj in g:
    print(f"{subject} {predicate} {obj}")

# SPARQL query
results = g.query("""
    PREFIX hd: <http://happy-dev.fr/owl/#>
    SELECT ?user ?username
    WHERE {
        ?user a hd:user ;
              hd:username ?username .
    }
""")

for row in results:
    print(f"User: {row.user}, Username: {row.username}")
```

### JavaScript Client

```javascript
// Using N3.js library
import { Parser, Writer } from 'n3';

// Fetch Turtle
const response = await fetch('http://localhost:8000/users/', {
  headers: { 'Accept': 'text/turtle' }
});
const turtleText = await response.text();

// Parse
const parser = new Parser();
const quads = parser.parse(turtleText);

// Process quads
quads.forEach(quad => {
  console.log(quad.subject.value, quad.predicate.value, quad.object.value);
});
```

---

## Error Handling

### Parse Errors

If the server cannot parse incoming Turtle:

```
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "detail": "Turtle parse error: Expected '.' at line 3"
}
```

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| Missing prefix | Undefined namespace | Add `@prefix` declaration |
| Unterminated triple | Missing `.` or `;` | Check triple termination |
| Invalid URI | Malformed `<>` syntax | Use valid URI format |
| Type mismatch | Wrong literal datatype | Check `^^xsd:type` |

---

## Performance Considerations

### Serialization Speed

| Format | Relative Speed | Notes |
|--------|----------------|-------|
| JSON-LD | Fastest | Native Python dict |
| Turtle | ~2-3x slower | RDF graph conversion |

### When to Choose Turtle

- RDF tool interoperability is required
- Human readability is important
- SPARQL endpoint integration
- Semantic web applications

### Optimization Tips

1. **Use JSON-LD for APIs** - Faster for web applications
2. **Cache Turtle responses** - ETags supported
3. **Limit nesting depth** - Configure `Meta.depth`
4. **Paginate large containers** - Reduces response size

---

## Testing

### Unit Tests

```python
from django.test import TestCase

class TurtleSerializationTests(TestCase):
    def test_turtle_content_negotiation(self):
        response = self.client.get(
            '/users/',
            HTTP_ACCEPT='text/turtle'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'text/turtle; charset=utf-8'
        )
        self.assertIn(b'@prefix', response.content)

    def test_turtle_post(self):
        turtle_data = '''
            @prefix hd: <http://happy-dev.fr/owl/#> .
            <> a hd:user ;
               hd:username "testuser" .
        '''
        response = self.client.post(
            '/users/',
            data=turtle_data,
            content_type='text/turtle'
        )
        self.assertEqual(response.status_code, 201)
```

### Integration Tests

Run the renderer/parser test suite:

```bash
python -m unittest djangoldp.tests.test_renderers_parsers
```

---

## Troubleshooting

### Empty or Minimal Turtle Response

**Symptom:** Turtle response only contains URIs, no properties.

**Cause:** Context resolution failed (network timeout).

**Solution:** Check `LDP_RDF_CONTEXT` URL is accessible.

### Prefix Resolution Errors

**Symptom:** Properties show full URIs instead of prefixed names.

**Cause:** Missing or incorrect context configuration.

**Solution:** Verify `LDP_RDF_CONTEXT` includes required vocabulary.

### Encoding Issues

**Symptom:** Special characters corrupted.

**Solution:** Ensure UTF-8 encoding:
```bash
curl -H "Accept: text/turtle; charset=utf-8" http://localhost:8000/users/
```

---

## Related Documentation

- [TURTLE_LIMITATIONS.md](TURTLE_LIMITATIONS.md) - Technical details on Turtle vs JSON-LD
- [BRANCH_CHANGELOG.md](BRANCH_CHANGELOG.md) - Version history
- [create_model.md](create_model.md) - Model configuration with RDF types
