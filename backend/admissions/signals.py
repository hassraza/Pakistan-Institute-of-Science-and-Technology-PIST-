import logging
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from admissions.models import Program
from admissions.pakuniportal_sync import sync_program_to_pakuniportal

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Program)
def program_post_save_sync(sender, instance, created, raw=False, **kwargs):
    """
    Automatically dispatch created or updated programs to PakUniPortal.
    """
    if raw:
        return
    try:
        sync_program_to_pakuniportal(instance, action='upsert')
    except Exception as exc:
        logger.warning('Error in program post_save sync: %s', exc)


@receiver(post_delete, sender=Program)
def program_post_delete_sync(sender, instance, **kwargs):
    """
    Automatically notify PakUniPortal when a program is deleted in PIST.
    """
    try:
        sync_program_to_pakuniportal(instance, action='delete')
    except Exception as exc:
        logger.warning('Error in program post_delete sync: %s', exc)
