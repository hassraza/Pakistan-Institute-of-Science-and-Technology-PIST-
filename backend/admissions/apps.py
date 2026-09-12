import os
from django.apps import AppConfig


class AdmissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admissions'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        import admissions.signals  # noqa: F401

