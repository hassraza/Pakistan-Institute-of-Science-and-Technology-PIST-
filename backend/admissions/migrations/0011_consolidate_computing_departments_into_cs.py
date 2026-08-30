from django.db import migrations


def consolidate_computing_departments(apps, schema_editor):
    Department = apps.get_model('admissions', 'Department')
    Program = apps.get_model('admissions', 'Program')

    cs_isb = Department.objects.filter(code='CS').first()
    cs_lhr = Department.objects.filter(code='CS-LHR').first()
    cs_khi = Department.objects.filter(code='CS-KHI').first()

    targets = {'ISB': cs_isb, 'LHR': cs_lhr, 'KHI': cs_khi}

    for legacy_code in ('AI', 'DS', 'IT', 'CYS'):
        for campus_code in ('ISB', 'LHR', 'KHI'):
            target_cs = targets.get(campus_code) or cs_isb
            if not target_cs:
                continue
            code_to_check = legacy_code if campus_code == 'ISB' else f'{legacy_code}-{campus_code}'
            for old_d in Department.objects.filter(code=code_to_check):
                Program.objects.filter(department=old_d).update(department=target_cs)
                old_d.delete()

    # Also clean up stray departments that have no programs or non-standard slugs (e.g. TREYSKDHBC, djsjkASL)
    for stray_d in Department.objects.filter(name__icontains='Computer Science').exclude(code__in=['CS', 'CS-LHR', 'CS-KHI']):
        if cs_isb:
            Program.objects.filter(department=stray_d).update(department=cs_isb)
        stray_d.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0010_seed_lahore_karachi_departments'),
    ]

    operations = [
        migrations.RunPython(consolidate_computing_departments, reverse_code=migrations.RunPython.noop),
    ]
