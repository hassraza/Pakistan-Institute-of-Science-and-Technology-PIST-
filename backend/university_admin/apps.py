import os
from django.apps import AppConfig


class UniversityAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'university_admin'
    path = os.path.dirname(os.path.abspath(__file__))
