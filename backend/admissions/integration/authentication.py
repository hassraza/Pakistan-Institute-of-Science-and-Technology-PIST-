from __future__ import annotations

import secrets
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission


def get_expected_api_key() -> str:
    """Retrieve the expected external integration API key from settings."""
    return getattr(settings, 'PIST_EXTERNAL_API_KEY', '') or 'pist-integration-secret-key-2026'


class APIKeyAuthentication(BaseAuthentication):
    """
    Authenticates requests using the 'X-API-KEY' HTTP header.
    Rejects requests missing the header or with an invalid key with 401 Unauthorized.
    """

    def authenticate_header(self, request):
        return 'ApiKey'

    def authenticate(self, request):
        api_key = request.headers.get('X-API-KEY') or request.META.get('HTTP_X_API_KEY')

        # Fallback to X-PIST-API-KEY if provided for backwards compatibility
        if not api_key:
            api_key = request.headers.get('X-PIST-API-KEY') or request.META.get('HTTP_X_PIST_API_KEY')

        if not api_key:
            raise exceptions.AuthenticationFailed('Authentication credentials were not provided. Missing X-API-KEY header.')

        expected_key = get_expected_api_key()
        if not secrets.compare_digest(api_key.strip(), expected_key.strip()):
            raise exceptions.AuthenticationFailed('Invalid API key provided.')

        # Return (user, auth) tuple; user is None for system-to-system API key auth
        return (None, api_key)


class HasAPIKeyPermission(BasePermission):
    """
    Permission check that enforces valid X-API-KEY header.
    """
    message = 'Invalid or missing API key.'

    def has_permission(self, request, view):
        api_key = request.headers.get('X-API-KEY') or request.META.get('HTTP_X_API_KEY')
        if not api_key:
            api_key = request.headers.get('X-PIST-API-KEY') or request.META.get('HTTP_X_PIST_API_KEY')

        if not api_key:
            return False

        expected_key = get_expected_api_key()
        return secrets.compare_digest(api_key.strip(), expected_key.strip())


try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class APIKeyAuthenticationScheme(OpenApiAuthenticationExtension):
        target_class = 'admissions.integration.authentication.APIKeyAuthentication'
        name = 'ApiKeyAuth'

        def get_security_definition(self, auto_schema):
            return {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API-KEY',
                'description': 'Secret key passed in the X-API-KEY request header for PakUniPortal integration.',
            }
except ImportError:
    pass
