from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from admissions.models import Campus, Department, Program, TestCenter, TestSession


class Command(BaseCommand):
    help = 'Seed fictional PIST campuses, departments, programs, test centers, and test sessions.'

    campus_rows = [
        {
            'name': 'PIST Islamabad Campus',
            'city': 'Islamabad',
            'code': 'ISB',
            'address': 'H-12, Islamabad',
            'description': 'Primary campus for science, engineering, and management programs.',
        },
        {
            'name': 'PIST Lahore Campus',
            'city': 'Lahore',
            'code': 'LHR',
            'address': 'Raiwind Road, Lahore',
            'description': 'Regional campus serving central Punjab applicants.',
        },
        {
            'name': 'PIST Karachi Campus',
            'city': 'Karachi',
            'code': 'KHI',
            'address': 'PECHS Block 6, Karachi',
            'description': 'Southern campus with modern teaching and testing facilities.',
        },
    ]

    departments = [
        {
            'name': 'Department of Computer Science',
            'description': 'Programs focused on software engineering, AI, and computing foundations.',
            'programs': [
                ('BS Computer Science', 'BSCS', 'USAT', 'Minimum 60% in FSc Pre-Engineering / ICS or equivalent.'),
                ('BS Software Engineering', 'BSSE', 'USAT', 'Minimum 60% in FSc Pre-Engineering / ICS or equivalent.'),
                ('BS Artificial Intelligence', 'BSAI', 'USAT', 'Minimum 60% in FSc Pre-Engineering / ICS or equivalent.'),
            ],
        },
        {
            'name': 'Department of Electrical & Mechanical Engineering',
            'description': 'Engineering programs for students preparing for technical and industrial careers.',
            'programs': [
                ('BS Electrical Engineering', 'BSEE', 'ECAT', 'Minimum 60% in FSc Pre-Engineering or equivalent.'),
                ('BS Mechanical Engineering', 'BSME', 'ECAT', 'Minimum 60% in FSc Pre-Engineering or equivalent.'),
            ],
        },
        {
            'name': 'Department of Health & Medical Sciences',
            'description': 'Professional health and medical pathways aligned with competitive entry requirements.',
            'programs': [
                ('MBBS', 'MBBS', 'MDCAT', 'Minimum 70% in FSc Pre-Medical or equivalent.'),
                ('Pharm-D', 'PHD', 'MDCAT', 'Minimum 60% in FSc Pre-Medical or equivalent.'),
            ],
        },
        {
            'name': 'Department of Management Sciences',
            'description': 'Business, finance, and management degree programs for future professionals.',
            'programs': [
                ('BBA', 'BBA', 'USAT', 'Minimum 50% in FSc or equivalent.'),
                ('BS Accounting & Finance', 'BAF', 'USAT', 'Minimum 50% in FSc or equivalent.'),
            ],
        },
    ]

    def handle(self, *args, **options):
        with transaction.atomic():
            campuses = {}
            for campus_row in self.campus_rows:
                campus, _ = Campus.objects.update_or_create(
                    code=campus_row['code'],
                    defaults=campus_row,
                )
                campuses[campus.code] = campus

            for campus in campuses.values():
                for department_row in self.departments:
                    department_slug = f'{campus.code}-{department_row["name"]}'.lower().replace('&', 'and').replace(' ', '-')
                    department, _ = Department.objects.update_or_create(
                        campus=campus,
                        slug=department_slug,
                        defaults={
                            'name': department_row['name'],
                            'description': department_row['description'],
                            'is_active': True,
                        },
                    )

                    for program_name, program_code, required_test, eligibility_text in department_row['programs']:
                        program_slug = f'{campus.code}-{program_code}'.lower()
                        Program.objects.update_or_create(
                            department=department,
                            code=program_code,
                            defaults={
                                'name': program_name,
                                'slug': program_slug,
                                'description': f'{program_name} at {campus.name}.',
                                'eligibility_percentage': 60 if program_code not in {'MBBS'} else 70,
                                'eligibility_text': eligibility_text,
                                'required_test_type': required_test,
                                'admissions_open': True,
                                'application_deadline': timezone.now().date() + timedelta(days=21),
                                'duration': '4 Years' if program_code not in {'MBBS'} else '5 Years',
                                'degree_level': 'Bachelor',
                            },
                        )

                test_center, _ = TestCenter.objects.update_or_create(
                    campus=campus,
                    name=f'{campus.name} Admission Test Center',
                    defaults={
                        'address': campus.address,
                        'building': 'Academic Block A',
                        'hall': 'Hall A-101',
                        'capacity': 240,
                        'is_active': True,
                    },
                )

                for program in Program.objects.filter(department__campus=campus).select_related('department'):
                    TestSession.objects.update_or_create(
                        test_center=test_center,
                        program=program,
                        test_date=timezone.now().date() + timedelta(days=10),
                        defaults={
                            'reporting_time': timezone.datetime.strptime('08:30', '%H:%M').time(),
                            'available_seats': test_center.capacity,
                            'is_active': True,
                        },
                    )

        self.stdout.write(self.style.SUCCESS('PIST seed data created or updated successfully.'))
