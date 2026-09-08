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
from admissions.seed_data import DEPARTMENT_DATA, PROGRAM_DATA, QUALIFICATION_GROUP_CODES, QUALIFICATIONS, TEST_TYPES


class Command(BaseCommand):
    help = 'Seed fictional PIST campus (Islamabad Main Campus), academic structure, eligibility, test centers, and sessions.'

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

        # 1. Islamabad Main Campus (Single Campus Architecture)
        campus_rows = [
            ('Pakistan Institute of Science and Technology — Islamabad Main Campus', 'Islamabad', 'ISB', 'Plot H-12, Sector H-12, Islamabad, Islamabad Capital Territory, Pakistan', True),
        ]
        campuses = {}
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

        # Purge non-Islamabad campuses (LHR, KHI, and any legacy entities)
        isb_campus = campuses['ISB']
        PISTApplicant.objects.exclude(campus=isb_campus).update(campus=isb_campus)
        legacy_campuses = list(Campus.objects.exclude(code='ISB'))
        for legacy in legacy_campuses:
            for stray_p in Program.objects.filter(campus=legacy):
                base_code = stray_p.code.replace('-LHR', '-ISB').replace('-KHI', '-ISB')
                target_p = Program.objects.filter(code=base_code).first() or Program.objects.filter(campus=isb_campus).first()
                if target_p:
                    PISTApplicant.objects.filter(program=stray_p).update(program=target_p)
                stray_p.delete()
            for d in Department.objects.filter(campus=legacy):
                for stray_p in Program.objects.filter(department=d):
                    base_code = stray_p.code.replace('-LHR', '-ISB').replace('-KHI', '-ISB')
                    target_p = Program.objects.filter(code=base_code).first() or Program.objects.filter(campus=isb_campus).first()
                    if target_p:
                        PISTApplicant.objects.filter(program=stray_p).update(program=target_p)
                    stray_p.delete()
                d.delete()
            TestSession.objects.filter(test_center__campus=legacy).delete()
            TestCenter.objects.filter(campus=legacy).delete()
            RollNumberSequence.objects.filter(campus=legacy).delete()
            legacy.delete()

        # 2. Seed 20 Departments for Islamabad
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

        # Clean up legacy/merged or non-Islamabad departments
        valid_codes = set(departments.keys())
        for stray_dept in Department.objects.exclude(code__in=valid_codes):
            target_cs = departments.get('CS')
            if target_cs:
                Program.objects.filter(department=stray_dept).update(department=target_cs)
            stray_dept.delete()

        # 3. Qualifications & Test Types
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

        # 4. Seed 41 Programs for Islamabad Main Campus
        programs = []
        valid_program_codes = set()
        for index, row in enumerate(PROGRAM_DATA, start=1):
            is_open = index % 10 not in {0, 3, 7}
            valid_program_codes.add(row['code'])
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

        # Delete any non-Islamabad programs (such as mirrored -LHR, -KHI)
        stray_programs = Program.objects.exclude(code__in=valid_program_codes)
        for stray_p in stray_programs:
            target_program = Program.objects.filter(code__in=valid_program_codes, department=stray_p.department).first()
            if target_program:
                PISTApplicant.objects.filter(program=stray_p).update(program=target_program)
            stray_p.delete()

        # 5. Test Center & Sessions for Islamabad Main Campus
        test_center, created = TestCenter.objects.update_or_create(
            campus=isb_campus, name=f'{isb_campus.name} Admission Test Center',
            defaults={'address': isb_campus.address, 'city': isb_campus.city, 'building': 'Academic Block A', 'hall': 'Hall 3', 'capacity': 240, 'is_active': True},
        )
        counts['TestCenter']['created' if created else 'updated'] += 1
        for program in Program.objects.filter(campus=isb_campus):
            _, session_created = TestSession.objects.update_or_create(
                test_center=test_center, program=program, test_date=today + timedelta(days=10),
                defaults={'reporting_time': time(8, 30), 'start_time': time(9, 0), 'building': 'Academic Block A', 'hall': 'Hall 3', 'available_seats': test_center.capacity, 'is_active': True},
            )
            counts['TestSession']['created' if session_created else 'updated'] += 1

        self.stdout.write(self.style.SUCCESS('PIST single-campus seed completed.'))
        for model_name, result in counts.items():
            self.stdout.write(f'{model_name}: {result["created"]} created, {result["updated"]} updated')

