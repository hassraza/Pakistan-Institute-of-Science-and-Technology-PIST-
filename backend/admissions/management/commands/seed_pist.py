from __future__ import annotations

from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from admissions.models import (
    Campus, Department, PISTApplicant, Program, Qualification, TestType,
    ProgramEligibility, ProgramTestRequirement, TestCenter, TestSession,
)
from admissions.seed_data import DEPARTMENT_DATA, MIRRORED_CODES, PROGRAM_DATA, QUALIFICATION_GROUP_CODES, QUALIFICATIONS, TEST_TYPES


class Command(BaseCommand):
    help = 'Seed fictional PIST campuses, academic structure, eligibility, test centers, and sessions.'

    def _update(self, model, lookup, defaults, counts):
        _, created = model.objects.update_or_create(defaults=defaults, **lookup)
        counts[model.__name__][('created' if created else 'updated')] += 1

    def _program_slug(self, department, code):
        desired = slugify(code)
        if Program.objects.filter(department=department, slug=desired).exclude(code=code).exists():
            return f'{desired}-program'
        return desired

    @transaction.atomic
    def handle(self, *args, **options):
        counts = {name: {'created': 0, 'updated': 0} for name in (
            'Campus', 'Department', 'Program', 'Qualification', 'TestType',
            'ProgramEligibility', 'ProgramTestRequirement', 'TestCenter', 'TestSession',
        )}
        today = timezone.localdate()
        deadline = today + timedelta(days=45)
        closed_deadline = today - timedelta(days=10)

        campuses = {}
        campus_rows = [
            ('Pakistan Institute of Science and Technology — Islamabad Main Campus', 'Islamabad', 'ISB', 'Plot H-12, Sector H-12, Islamabad, Islamabad Capital Territory, Pakistan', True),
            ('Pakistan Institute of Science and Technology — Lahore Campus', 'Lahore', 'LHR', 'Raiwind Road, Lahore, Punjab, Pakistan', False),
            ('Pakistan Institute of Science and Technology — Karachi Campus', 'Karachi', 'KHI', 'PECHS Block 6, Karachi, Sindh, Pakistan', False),
        ]
        for name, city, code, address, is_main in campus_rows:
            campus, created = Campus.objects.update_or_create(code=code, defaults={
                'name': name, 'city': city, 'address': address,
                'description': f'{name} provides modern teaching, research, and student support facilities.',
                'admissions_open': True, 'is_active': True, 'is_main_campus': is_main,
            })
            counts['Campus']['created' if created else 'updated'] += 1
            campuses[code] = campus
        campuses['ISB'].is_main_campus = True
        campuses['ISB'].save(update_fields=['is_main_campus'])
        for code in ('LHR', 'KHI'):
            if campuses[code].is_main_campus:
                campuses[code].is_main_campus = False
                campuses[code].save(update_fields=['is_main_campus'])

        # Clean up and merge legacy duplicate campuses (e.g. PIST Karachi / PIST Lahore / numeric codes)
        legacy_campuses = Campus.objects.exclude(code__in=['ISB', 'LHR', 'KHI'])
        for legacy in legacy_campuses:
            target_code = 'LHR' if 'lahore' in legacy.name.lower() or 'lhr' in legacy.code.lower() else (
                'KHI' if 'karachi' in legacy.name.lower() or 'khi' in legacy.code.lower() else 'ISB'
            )
            target_campus = campuses[target_code]
            Department.objects.filter(campus=legacy).update(campus=target_campus)
            PISTApplicant.objects.filter(campus=legacy).update(campus=target_campus)
            TestCenter.objects.filter(campus=legacy).update(campus=target_campus)
            legacy.delete()

        departments = {}
        for name, code in DEPARTMENT_DATA:
            department, created = Department.objects.update_or_create(
                code=code,
                defaults={
                    'campus': campuses['ISB'], 'name': name,
                    'slug': slugify(f'ISB-{code}-{name}'),
                    'description': f'{name} develops professional expertise through rigorous teaching, applied research, experienced faculty, and purpose-built facilities.',
                    'is_active': True,
                },
            )
            counts['Department']['created' if created else 'updated'] += 1
            departments[code] = department

        # Seed 15 departments for Lahore and 15 departments for Karachi
        for campus_code in ('LHR', 'KHI'):
            for name, code in DEPARTMENT_DATA[:15]:
                dept_code = f'{code}-{campus_code}'
                dept, created = Department.objects.update_or_create(
                    code=dept_code,
                    defaults={
                        'campus': campuses[campus_code],
                        'name': name,
                        'slug': slugify(f'{campus_code}-{code}-{name}'),
                        'description': f'{name} ({campuses[campus_code].city} Campus) develops professional expertise through rigorous teaching, applied research, and purpose-built facilities.',
                        'is_active': True,
                    },
                )
                counts['Department']['created' if created else 'updated'] += 1
                departments[dept_code] = dept

        qualifications = {}
        for key, name in QUALIFICATIONS.items():
            qualification, created = Qualification.objects.update_or_create(
                name=name,
                defaults={'qualification_group_code': QUALIFICATION_GROUP_CODES.get(key, '')},
            )
            counts['Qualification']['created' if created else 'updated'] += 1
            qualifications[key] = qualification

        tests = {}
        for key, name in TEST_TYPES.items():
            test_type, created = TestType.objects.update_or_create(
                name=name,
                defaults={'description': f'{name} is an admissions assessment used by PIST for eligible applicants.'},
            )
            counts['TestType']['created' if created else 'updated'] += 1
            tests[key] = test_type

        programs = []
        for index, row in enumerate(PROGRAM_DATA, start=1):
            is_open = index % 10 not in {0, 3, 7}
            program, created = Program.objects.update_or_create(
                code=row['code'],
                defaults={
                    'department': departments[row['department']], 'campus': campuses['ISB'],
                    'name': row['name'], 'slug': self._program_slug(departments[row['department']], row['code']),
                    'description': f"{row['name']} provides a structured curriculum in its discipline, combining foundational knowledge, practical learning, and preparation for responsible professional practice.",
                    'eligibility_percentage': row['percentage'],
                    'eligibility_text': f"Minimum {row['percentage']}% in the qualifying examination.",
                    'required_test_type': row['tests'][0].upper() if row['tests'][0] in {'usat', 'ecat', 'mdcat', 'lat'} else 'Other',
                    'required_qualification': qualifications[row['qualification'][0]],
                    'admissions_open': is_open,
                    'application_deadline': deadline if is_open else closed_deadline,
                    'duration': row['duration'], 'degree_level': row['degree'],
                    'career_opportunities': row['careers'],
                },
            )
            counts['Program']['created' if created else 'updated'] += 1
            programs.append(program)
            ProgramEligibility.objects.filter(program=program).exclude(qualification_id__in=[qualifications[key].pk for key in row['qualification']]).delete()
            for key in row['qualification']:
                _, rule_created = ProgramEligibility.objects.update_or_create(
                    program=program, qualification=qualifications[key],
                    defaults={'minimum_percentage': row['percentage']},
                )
                counts['ProgramEligibility']['created' if rule_created else 'updated'] += 1
            ProgramTestRequirement.objects.filter(program=program).exclude(test_type_id__in=[tests[key].pk for key in row['tests']]).delete()
            for key in row['tests']:
                _, requirement_created = ProgramTestRequirement.objects.update_or_create(
                    program=program, test_type=tests[key], defaults={'is_alternative': len(row['tests']) > 1},
                )
                counts['ProgramTestRequirement']['created' if requirement_created else 'updated'] += 1

        for campus_code in ('LHR', 'KHI'):
            for base_code, short_code in MIRRORED_CODES.items():
                base = next(program for program in programs if program.code == base_code)
                code = f'{short_code}-{campus_code}'
                legacy_program = Program.objects.filter(code=f'{code}-{campus_code}').first()
                if legacy_program and not Program.objects.filter(code=code).exists():
                    legacy_program.code = code
                    legacy_program.save(update_fields=['code'])
                program, created = Program.objects.update_or_create(
                    code=code,
                    defaults={
                        'department': departments.get(f"{base.department.code}-{campus_code}", base.department), 'campus': campuses[campus_code],
                        'name': base.name, 'slug': self._program_slug(departments.get(f"{base.department.code}-{campus_code}", base.department), code), 'description': base.description,
                        'eligibility_percentage': base.eligibility_percentage, 'eligibility_text': base.eligibility_text,
                        'required_test_type': base.required_test_type, 'required_qualification': base.required_qualification,
                        'admissions_open': True, 'application_deadline': deadline,
                        'duration': base.duration, 'degree_level': base.degree_level,
                        'career_opportunities': base.career_opportunities,
                    },
                )
                counts['Program']['created' if created else 'updated'] += 1
                for rule in base.eligibility_rules.all():
                    _, rule_created = ProgramEligibility.objects.update_or_create(
                        program=program, qualification=rule.qualification,
                        defaults={'minimum_percentage': rule.minimum_percentage},
                    )
                    counts['ProgramEligibility']['created' if rule_created else 'updated'] += 1
                for requirement in base.test_requirements.all():
                    _, requirement_created = ProgramTestRequirement.objects.update_or_create(
                        program=program, test_type=requirement.test_type,
                        defaults={'is_alternative': requirement.is_alternative},
                    )
                    counts['ProgramTestRequirement']['created' if requirement_created else 'updated'] += 1

        for campus in campuses.values():
            test_center, created = TestCenter.objects.update_or_create(
                campus=campus, name=f'{campus.name} Admission Test Center',
                defaults={'address': campus.address, 'city': campus.city, 'building': 'Academic Block A', 'hall': 'Hall A-101', 'capacity': 240, 'is_active': True},
            )
            counts['TestCenter']['created' if created else 'updated'] += 1
            for program in Program.objects.filter(campus=campus):
                _, session_created = TestSession.objects.update_or_create(
                    test_center=test_center, program=program, test_date=today + timedelta(days=10),
                    defaults={'reporting_time': time(8, 30), 'start_time': time(9, 0), 'building': 'Academic Block A', 'hall': 'Hall 3', 'available_seats': test_center.capacity, 'is_active': True},
                )
                counts['TestSession']['created' if session_created else 'updated'] += 1

        self.stdout.write(self.style.SUCCESS('PIST seed completed.'))
        for model_name, result in counts.items():
            self.stdout.write(f'{model_name}: {result["created"]} created, {result["updated"]} updated')
