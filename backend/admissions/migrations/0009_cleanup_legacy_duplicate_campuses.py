from django.db import migrations


def merge_and_delete_legacy_campuses(apps, schema_editor):
    Campus = apps.get_model('admissions', 'Campus')
    Department = apps.get_model('admissions', 'Department')
    Program = apps.get_model('admissions', 'Program')
    PISTApplicant = apps.get_model('admissions', 'PISTApplicant')
    TestCenter = apps.get_model('admissions', 'TestCenter')

    legacy_campuses = list(Campus.objects.exclude(code__in=['ISB', 'LHR', 'KHI']))
    if not legacy_campuses:
        return

    isb = Campus.objects.filter(code='ISB').first()
    lhr = Campus.objects.filter(code='LHR').first()
    khi = Campus.objects.filter(code='KHI').first()
    campuses = {'ISB': isb, 'LHR': lhr, 'KHI': khi}

    # Find legacy/duplicate campuses
    legacy_campuses = Campus.objects.exclude(code__in=['ISB', 'LHR', 'KHI'])
    for legacy in legacy_campuses:
        name_lower = legacy.name.lower()
        code_lower = legacy.code.lower()
        target_code = 'LHR' if 'lahore' in name_lower or 'lhr' in code_lower else (
            'KHI' if 'karachi' in name_lower or 'khi' in code_lower else 'ISB'
        )
        target = campuses[target_code]

        # Reassign departments, programs, applicants, test centers
        Department.objects.filter(campus=legacy).update(campus=target)
        Program.objects.filter(campus=legacy).update(campus=target)
        PISTApplicant.objects.filter(campus=legacy).update(campus=target)
        TestCenter.objects.filter(campus=legacy).update(campus=target)
        legacy.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0008_testcenter_city'),
    ]

    operations = [
        migrations.RunPython(merge_and_delete_legacy_campuses, reverse_code=migrations.RunPython.noop),
    ]
