from django.db import migrations
from django.utils.text import slugify


def seed_lahore_karachi_departments(apps, schema_editor):
    Campus = apps.get_model('admissions', 'Campus')
    Department = apps.get_model('admissions', 'Department')
    Program = apps.get_model('admissions', 'Program')

    lhr = Campus.objects.filter(code='LHR').first()
    khi = Campus.objects.filter(code='KHI').first()
    if not lhr or not khi:
        return

    DEPARTMENT_LIST = [
        ('Department of Computer Science', 'CS'),
        ('Department of Software Engineering', 'SE'),
        ('Department of Artificial Intelligence', 'AI'),
        ('Department of Data Science', 'DS'),
        ('Department of Information Technology', 'IT'),
        ('Department of Cyber Security', 'CYS'),
        ('Department of Electrical Engineering', 'EE'),
        ('Department of Mechanical Engineering', 'ME'),
        ('Department of Civil Engineering', 'CE'),
        ('Department of Chemical Engineering', 'CHE'),
        ('Department of Biomedical Engineering', 'BME'),
        ('Department of Health and Medical Sciences', 'HMS'),
        ('Department of Pharmacy', 'PHARM'),
        ('Department of Management Sciences', 'MGT'),
        ('Department of Accounting and Finance', 'ACF'),
    ]

    for campus_code in ('LHR', 'KHI'):
        campus = Campus.objects.filter(code=campus_code).first()
        if not campus:
            continue
        for name, code in DEPARTMENT_LIST:
            dept_code = f'{code}-{campus_code}'
            dept, _ = Department.objects.update_or_create(
                code=dept_code,
                defaults={
                    'campus': campus,
                    'name': name,
                    'slug': slugify(f'{campus_code}-{code}-{name}'),
                    'description': f'{name} ({campus.city} Campus) provides professional education and modern research facilities.',
                    'is_active': True,
                },
            )
            # Re-link existing programs of this campus to their campus department
            Program.objects.filter(campus=campus, code__startswith=f'{code}-').update(department=dept)


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0009_cleanup_legacy_duplicate_campuses'),
    ]

    operations = [
        migrations.RunPython(seed_lahore_karachi_departments, reverse_code=migrations.RunPython.noop),
    ]
