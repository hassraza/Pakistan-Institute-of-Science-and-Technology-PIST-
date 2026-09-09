import os
from django.apps import AppConfig


class MainConfig(AppConfig):
    name = 'main'
    path = os.path.dirname(os.path.abspath(__file__))
