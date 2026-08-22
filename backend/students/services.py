from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import StudentIdSequence


@transaction.atomic
def generate_student_id():
    """Allocate the next per-year ID while holding the year's counter row lock."""
    year = timezone.localdate().year
    sequence, _ = StudentIdSequence.objects.select_for_update().get_or_create(year=year)
    sequence.last_value += 1
    sequence.save(update_fields=['last_value'])
    prefix = getattr(settings, 'STUDENT_ID_PREFIX', 'PIST-STU')
    return f'{prefix}-{year}-{sequence.last_value:04d}'
