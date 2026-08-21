import secrets

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasPISTExternalAPIKey(BasePermission):
    message = 'Invalid or missing PIST API key.'

    def has_permission(self, request, view):
        expected_key = getattr(settings, 'PIST_EXTERNAL_API_KEY', '')
        provided_key = request.headers.get('X-PIST-API-KEY', '')
        if not expected_key:
            return False
        return bool(provided_key) and secrets.compare_digest(provided_key, expected_key)
