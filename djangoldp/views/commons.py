"""
Common view utilities and authentication classes.

Note: Renderers and parsers have been moved to separate modules:
- djangoldp.renderers (JSONLDRenderer, TurtleRenderer)
- djangoldp.parsers (JSONLDParser, TurtleParser)

Backward compatibility imports are provided below for existing code.
"""

from rest_framework.authentication import SessionAuthentication

# Backward compatibility: import renderers and parsers from their new locations
from djangoldp.renderers import JSONLDRenderer, TurtleRenderer
from djangoldp.parsers import JSONLDParser, TurtleParser

# Re-export for backward compatibility
__all__ = [
    'NoCSRFAuthentication',
    'JSONLDRenderer',
    'TurtleRenderer',
    'JSONLDParser',
    'TurtleParser',
]


class NoCSRFAuthentication(SessionAuthentication):
    """
    An authentication class which exempts CSRF authentication.

    Used for LDP endpoints that need to accept requests from external
    federated servers without CSRF tokens.
    """
    def enforce_csrf(self, request):
        return

