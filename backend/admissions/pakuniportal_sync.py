from __future__ import annotations

import logging
from typing import Any, Tuple
import requests

from django.conf import settings

logger = logging.getLogger(__name__)


def serialize_program_for_sync(program, action: str = 'upsert') -> dict[str, Any]:
    dept_name = program.department.name if getattr(program, 'department', None) else ''
    eligibility_pct = float(program.eligibility_percentage) if getattr(program, 'eligibility_percentage', None) is not None else 60.0

    return {
        'code': program.code,
        'name': program.name,
        'degree_level': getattr(program, 'degree_level', 'Undergraduate'),
        'department_name': dept_name,
        'duration': getattr(program, 'duration', '4 Years'),
        'eligibility_percentage': eligibility_pct,
        'required_test_type': getattr(program, 'required_test_type', 'USAT'),
        'admissions_open': bool(getattr(program, 'admissions_open', True)),
        'description': getattr(program, 'description', ''),
        'action': action,
    }


def sync_program_to_pakuniportal(
    program,
    action: str = 'upsert',
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: int | None = None,
) -> Tuple[bool, Any]:
    """
    Dispatches a program creation, update, or deletion to PakUniPortal.
    Returns (True, response_data) on success, or (False, error_message) on failure.
    Never raises an uncaught exception to avoid crashing PIST admin workflows.
    """
    if not getattr(settings, 'PAKUNIPORTAL_SYNC_ENABLED', True):
        logger.info('PakUniPortal synchronization is disabled in settings.')
        return True, {'status': 'skipped_disabled'}

    url_base = (base_url or getattr(settings, 'PAKUNIPORTAL_BASE_URL', 'http://127.0.0.1:8000') or '').rstrip('/')
    sync_path = getattr(settings, 'PAKUNIPORTAL_PROGRAM_SYNC_PATH', '/api/v1/pist/programs/sync/').lstrip('/')
    endpoint = f'{url_base}/{sync_path}'

    key = api_key or getattr(settings, 'PAKUNIPORTAL_SYNC_API_KEY', 'pist-integration-secret-key-2026')
    timeout_secs = timeout or getattr(settings, 'PAKUNIPORTAL_SYNC_TIMEOUT', 5)

    payload = serialize_program_for_sync(program, action=action)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-API-KEY': key,
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=timeout_secs)
        if response.status_code == 200:
            logger.info('Successfully synced program %s (%s) to PakUniPortal.', program.name, action)
            try:
                return True, response.json()
            except ValueError:
                return True, {'status': 'success'}
        else:
            logger.warning(
                'PakUniPortal sync returned status %s for program %s: %s',
                response.status_code, program.name, response.text[:200]
            )
            return False, f'HTTP {response.status_code}: {response.text[:100]}'
    except requests.RequestException as exc:
        logger.warning('Failed to sync program %s to PakUniPortal: %s', program.name, exc)
        return False, str(exc)


def bulk_sync_all_programs(
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: int | None = None,
) -> Tuple[bool, Any]:
    """
    Performs a bulk synchronization of all programs in PIST to PakUniPortal.
    """
    from admissions.models import Program

    if not getattr(settings, 'PAKUNIPORTAL_SYNC_ENABLED', True):
        return True, {'status': 'skipped_disabled', 'count': 0}

    programs = list(Program.objects.select_related('department').all())
    if not programs:
        return True, {'status': 'empty', 'count': 0}

    payload = [serialize_program_for_sync(p, action='upsert') for p in programs]

    url_base = (base_url or getattr(settings, 'PAKUNIPORTAL_BASE_URL', 'http://127.0.0.1:8000') or '').rstrip('/')
    sync_path = getattr(settings, 'PAKUNIPORTAL_PROGRAM_SYNC_PATH', '/api/v1/pist/programs/sync/').lstrip('/')
    endpoint = f'{url_base}/{sync_path}'

    key = api_key or getattr(settings, 'PAKUNIPORTAL_SYNC_API_KEY', 'pist-integration-secret-key-2026')
    timeout_secs = timeout or getattr(settings, 'PAKUNIPORTAL_SYNC_TIMEOUT', 10)

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-API-KEY': key,
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=timeout_secs)
        if response.status_code == 200:
            logger.info('Successfully bulk-synced %d programs to PakUniPortal.', len(programs))
            try:
                return True, response.json()
            except ValueError:
                return True, {'status': 'success', 'count': len(programs)}
        else:
            return False, f'HTTP {response.status_code}: {response.text[:150]}'
    except requests.RequestException as exc:
        logger.warning('Failed bulk sync to PakUniPortal: %s', exc)
        return False, str(exc)
