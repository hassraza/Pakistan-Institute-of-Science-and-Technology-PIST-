from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}


def validate_academic_document(file):
    if not file:
        return
    extension = Path(file.name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError('Unsupported file type. Please upload a PDF, JPG, JPEG, or PNG file.')

    max_size_mb = getattr(settings, 'ACADEMIC_DOCUMENT_MAX_SIZE_MB', 5)
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f'File exceeds maximum size of {max_size_mb} MB.')

    position = file.tell()
    header = file.read(8)
    file.seek(position)
    if extension == '.pdf':
        valid_signature = header.startswith(b'%PDF')
    else:
        try:
            image = Image.open(file)
            image.verify()
            valid_signature = image.format in {'JPEG', 'PNG'}
        except (UnidentifiedImageError, OSError):
            valid_signature = False
        finally:
            file.seek(position)
    if not valid_signature:
        raise ValidationError('The uploaded file content does not match a valid PDF, JPG, JPEG, or PNG image.')
