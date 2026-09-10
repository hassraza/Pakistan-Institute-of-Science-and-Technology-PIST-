from __future__ import annotations

import re
from django.contrib.auth import get_user_model
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from students.models import StudentProfile, Notification
from admissions.models import Program, PISTApplicant


class StudentCreateInputSerializer(serializers.Serializer):
    """
    Serializer for creating a new student account inside PIST.
    Accepts both standard PIST payload and PakUniPortal rich payload.
    """
    # Name fields (either full_name or first_name/last_name)
    full_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        help_text="Student's full legal name."
    )
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    # Email & Username
    email = serializers.EmailField(
        help_text="Student's contact email address (used for notifications and login)."
    )
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)

    # Phone fields (either phone or phone_number)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=30, required=False, allow_blank=True)

    # CNIC fields (either cnic or cnic_number)
    cnic = serializers.CharField(max_length=30, required=False, allow_blank=True)
    cnic_number = serializers.CharField(max_length=30, required=False, allow_blank=True)

    # Extended Profile fields sent by PakUniPortal
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    province = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    nationality = serializers.CharField(max_length=80, required=False, allow_blank=True)
    passport_number = serializers.CharField(max_length=40, required=False, allow_blank=True)

    def validate(self, attrs):
        # 1. Resolve full name
        full_name = (attrs.get('full_name') or '').strip()
        if not full_name:
            first = (attrs.get('first_name') or '').strip()
            last = (attrs.get('last_name') or '').strip()
            full_name = f"{first} {last}".strip()
        if not full_name or len(full_name) < 3:
            raise serializers.ValidationError({'full_name': 'Full name must be at least 3 characters long.'})
        attrs['resolved_full_name'] = full_name

        # 2. Resolve phone
        phone = (attrs.get('phone') or attrs.get('phone_number') or '').strip()
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 10:
            raise serializers.ValidationError({'phone': 'Please provide a valid phone number (at least 10 digits).'})
        attrs['resolved_phone'] = phone

        # 3. Resolve CNIC
        cnic_raw = (attrs.get('cnic') or attrs.get('cnic_number') or '').strip()
        normalized_cnic = cnic_raw.replace('-', '').replace(' ', '')
        if not normalized_cnic.isdigit() or len(normalized_cnic) != 13:
            raise serializers.ValidationError({'cnic': 'CNIC must contain exactly 13 digits.'})
        formatted_cnic = f'{normalized_cnic[:5]}-{normalized_cnic[5:12]}-{normalized_cnic[12]}'
        attrs['resolved_cnic'] = formatted_cnic

        # 4. Normalize email
        attrs['resolved_email'] = attrs['email'].strip().lower()

        return attrs


class StudentCreateOutputSerializer(serializers.Serializer):
    """
    Credentials and student identity returned after account creation.
    Provides aliases matching both PIST and PakUniPortal keys.
    """
    student_id = serializers.CharField(help_text="Unique student identifier.")
    pist_student_id = serializers.CharField(help_text="Alias for PakUniPortal integration.")
    id = serializers.CharField(help_text="Alias for PakUniPortal integration.")
    username = serializers.CharField(help_text="Automatically generated unique username.")
    pist_username = serializers.CharField(help_text="Alias for PakUniPortal integration.")
    password = serializers.CharField(help_text="Automatically generated secure random password.")
    pist_password = serializers.CharField(help_text="Alias for PakUniPortal integration.")


class ApplicationCreateInputSerializer(serializers.Serializer):
    """
    Serializer for submitting a new university application.
    """
    student_id = serializers.CharField(
        help_text="Student ID (can be numeric user ID, PIST student code e.g. PIST-STU-2026-0001, or UUID)."
    )
    program_id = serializers.CharField(
        help_text="Program ID (numeric ID, code e.g. BSCS-ISB, or slug)."
    )


class ApplicationCreateOutputSerializer(serializers.Serializer):
    """
    Details of the created university application.
    """
    application_id = serializers.IntegerField(help_text="Numeric application ID.")
    pist_application_id = serializers.IntegerField(help_text="Alias for PakUniPortal integration.")
    id = serializers.IntegerField(help_text="Alias for PakUniPortal integration.")
    student_id = serializers.CharField(help_text="Student identifier.")
    program_id = serializers.IntegerField(help_text="Applied program numeric ID.")
    program_name = serializers.CharField(help_text="Program full title.")
    program_code = serializers.CharField(help_text="Program degree code.")
    status = serializers.CharField(help_text="Application status (e.g. submitted).")
    application_status = serializers.CharField(help_text="Alias for PakUniPortal status.")
    application_number = serializers.CharField(help_text="PIST application reference code.")
    roll_number = serializers.CharField(allow_null=True, required=False, help_text="Roll number if issued.")
    created_at = serializers.DateTimeField(help_text="Application submission timestamp.")


class ApplicationStatusOutputSerializer(serializers.Serializer):
    """
    Current status of an application.
    """
    application_id = serializers.IntegerField(help_text="Numeric application identifier.")
    pist_application_id = serializers.IntegerField(help_text="Alias for PakUniPortal integration.")
    id = serializers.IntegerField(help_text="Alias for PakUniPortal integration.")
    status = serializers.CharField(help_text="Application status string (e.g. submitted, under_review, accepted).")
    application_status = serializers.CharField(help_text="Alias for PakUniPortal status.")


class NotificationOutputSerializer(serializers.ModelSerializer):
    """
    Serializer for student notifications with field aliases for PakUniPortal.
    """
    notification_id = serializers.IntegerField(source='id', read_only=True)
    body = serializers.CharField(source='message', read_only=True)
    type = serializers.SerializerMethodField()
    notification_type = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ")

    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_id',
            'title',
            'message',
            'body',
            'type',
            'notification_type',
            'is_read',
            'created_at',
        ]

    @extend_schema_field(serializers.CharField())
    def get_type(self, obj):
        return 'admission'

    @extend_schema_field(serializers.CharField())
    def get_notification_type(self, obj):
        return 'admission'


class RollSlipOutputSerializer(serializers.Serializer):
    """
    Roll slip details for entry test admission.
    """
    roll_number = serializers.CharField(help_text="Issued candidate roll number.", allow_blank=True)
    rollNumber = serializers.CharField(source='roll_number', help_text="CamelCase alias for PakUniPortal.", allow_blank=True)
    test_date = serializers.CharField(allow_null=True, allow_blank=True, help_text="Scheduled entry test date (YYYY-MM-DD).")
    venue = serializers.CharField(allow_blank=True, help_text="Assigned examination venue and hall.")
    slip_url = serializers.CharField(allow_blank=True, required=False, help_text="Direct URL to view/print QR-verified roll slip.")
    qr_url = serializers.CharField(allow_blank=True, required=False, help_text="Direct URL to QR code image.")


class DocumentUploadInputSerializer(serializers.Serializer):
    """
    Serializer for uploading student documents from external portals.
    """
    student_id = serializers.CharField(
        help_text="Student identifier (can be numeric ID, PIST student ID, UUID, or CNIC)."
    )
    document_type = serializers.CharField(
        help_text="Type of document (e.g. CNIC, MATRIC, FSC, PHOTO, ENTRY_TEST)."
    )
    file = serializers.FileField(
        help_text="Binary file upload (PDF, PNG, JPG)."
    )


class DocumentUploadOutputSerializer(serializers.Serializer):
    """
    Response details after a document is uploaded.
    """
    success = serializers.BooleanField()
    document_id = serializers.CharField(required=False, allow_blank=True)
    document_type = serializers.CharField()
    file_name = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    """
    Standard error response.
    """
    detail = serializers.CharField(help_text="Error message description.")
    code = serializers.CharField(required=False, help_text="Machine-readable error code.")
