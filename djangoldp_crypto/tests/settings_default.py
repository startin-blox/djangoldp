"""This module contains YAML configurations for djangoldp_crypto testing."""

yaml_config = """
dependencies:

ldppackages:
  - djangoldp_crypto.tests

server:
  INSTALLED_APPS:
    - djangoldp_crypto
"""
