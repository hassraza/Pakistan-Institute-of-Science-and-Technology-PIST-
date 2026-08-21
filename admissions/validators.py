import base64
import binascii
import re
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile


DATA_URL_PATTERN = re.compile(r'^data:image/(?P<format>png|jpg|jpeg|webp);base64,(?P<data>.+)$', re.IGNORECASE)


def decode_base64_image(value, *, prefix='profile-photo'):
    if not value:
        return None

    if isinstance(value, str) and value.startswith(('http://', 'https://')):
        raise ValidationError('Remote image URLs are not allowed for security reasons.')

    image_format = 'jpg'
    raw_data = value

    if isinstance(value, str):
        match = DATA_URL_PATTERN.match(value)
        if match:
            image_format = 'jpg' if match.group('format').lower() == 'jpeg' else match.group('format').lower()
            raw_data = match.group('data')

    try:
        decoded = base64.b64decode(raw_data)
    except (TypeError, binascii.Error) as exc:
        raise ValidationError('Invalid base64 image payload.') from exc

    if len(decoded) > 5 * 1024 * 1024:
        raise ValidationError('Profile photo must be 5 MB or smaller.')

    return ContentFile(decoded, name=f'{prefix}-{uuid.uuid4().hex}.{image_format}')
