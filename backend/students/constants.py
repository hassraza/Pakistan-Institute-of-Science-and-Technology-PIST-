from django.conf import settings


def student_setting(name, default):
    return getattr(settings, name, default)
