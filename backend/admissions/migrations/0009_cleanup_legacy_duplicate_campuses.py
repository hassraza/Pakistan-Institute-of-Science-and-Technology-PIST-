from django.db import migrations


def merge_and_delete_legacy_campuses(apps, schema_editor):
    Campus = apps.get_model('admissions', 'Campus')
    Department = apps.get_model('admissions', 'Department')
    Program = apps.get_model('admissions', 'Program')
    PISTApplicant = apps.get_model('admissions', 'PISTApplicant')
    TestCenter = apps.get_model('admissions', 'TestCenter')

    # Ensure canonical campuses exist
    isb, _ = Campus.objects.get_or_create(code='ISB', defaults={
        'name': 'Pakistan Institute of Science and Technology — Islamabad Main Campus',
        'city': 'Islamabad', 'address': 'Plot H-12, Sector H-12, Islamabad, Islamabad Capital Territory, Pakistan',
        'is_main_campus': True, 'is_active': True,
    })
    lhr, _ = Campus.objects.get_or_create(code='LHR', defaults={
        'name': 'Pakistan Institute of Science and Technology — Lahore Campus',
        'city': 'Lahore', 'address': 'Raiwind Road, Lahore, Punjab, Pakistan',
        'is_main_campus': False, 'is_active': True,
    })
    khi, _ = Campus.objects.get_or_create(code='KHI', defaults={
        'name': 'Pakistan Institute of Science and Technology — Karachi Campus',
        'city': 'Karachi', 'address': 'PECHS Block 6, Karachi, Sindh, Pakistan',
        'is_main_campus': False, 'is_active': True,
    })

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
