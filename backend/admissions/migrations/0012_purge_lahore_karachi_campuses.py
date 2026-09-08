from django.db import migrations


def purge_lahore_karachi(apps, schema_editor):
    Campus = apps.get_model('admissions', 'Campus')
    Department = apps.get_model('admissions', 'Department')
    Program = apps.get_model('admissions', 'Program')
    PISTApplicant = apps.get_model('admissions', 'PISTApplicant')
    TestCenter = apps.get_model('admissions', 'TestCenter')
    TestSession = apps.get_model('admissions', 'TestSession')
    RollNumberSequence = apps.get_model('admissions', 'RollNumberSequence')

    isb = Campus.objects.filter(code='ISB').first()
    if isb:
        isb.is_main_campus = True
        isb.save(update_fields=['is_main_campus'])

        non_isb_campuses = list(Campus.objects.exclude(code='ISB'))
        if not non_isb_campuses:
            return

        # Reassign any applicant linked to non-ISB campus to ISB
        PISTApplicant.objects.exclude(campus=isb).update(campus=isb)

        for c in non_isb_campuses:
            # Reassign applicants on non-ISB programs to the corresponding ISB program if exists
            for stray_p in Program.objects.filter(campus=c):
                base_code = stray_p.code.replace('-LHR', '-ISB').replace('-KHI', '-ISB')
                target_p = Program.objects.filter(code=base_code).first() or Program.objects.filter(campus=isb).first()
                if target_p:
                    PISTApplicant.objects.filter(program=stray_p).update(program=target_p)
                stray_p.delete()

            for d in Department.objects.filter(campus=c):
                for stray_p in Program.objects.filter(department=d):
                    base_code = stray_p.code.replace('-LHR', '-ISB').replace('-KHI', '-ISB')
                    target_p = Program.objects.filter(code=base_code).first() or Program.objects.filter(campus=isb).first()
                    if target_p:
                        PISTApplicant.objects.filter(program=stray_p).update(program=target_p)
                    stray_p.delete()
                d.delete()

            TestSession.objects.filter(test_center__campus=c).delete()
            TestCenter.objects.filter(campus=c).delete()
            RollNumberSequence.objects.filter(campus=c).delete()
            c.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0011_consolidate_computing_departments_into_cs'),
    ]

    operations = [
        migrations.RunPython(purge_lahore_karachi, reverse_code=migrations.RunPython.noop),
    ]
