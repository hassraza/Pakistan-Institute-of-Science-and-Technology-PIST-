import csv
import json

from django.http import HttpResponse


class ApplicantExportService:
    @staticmethod
    def export_csv(queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="pist-applicants.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Application ID', 'Candidate', 'Campus', 'Program', 'Roll Number', 'Test Date', 'Status', 'Submitted',
        ])
        for applicant in queryset:
            writer.writerow([
                applicant.pk,
                applicant.full_name,
                applicant.campus.code,
                applicant.program.code,
                applicant.roll_number,
                applicant.test_date,
                applicant.status,
                applicant.created_at.isoformat(),
            ])
        return response

    @staticmethod
    def export_json(queryset):
        payload = []
        for applicant in queryset:
            payload.append({
                'application_id': str(applicant.pk),
                'candidate': applicant.full_name,
                'campus': applicant.campus.code,
                'program': applicant.program.code,
                'roll_number': applicant.roll_number,
                'test_date': applicant.test_date.isoformat() if applicant.test_date else None,
                'status': applicant.status,
                'submitted': applicant.created_at.isoformat(),
            })
        return HttpResponse(json.dumps(payload, indent=2), content_type='application/json')
