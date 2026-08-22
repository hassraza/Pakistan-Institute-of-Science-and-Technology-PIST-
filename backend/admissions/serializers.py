from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import ApplicantTestScore, Campus, PISTApplicant, Program
from .validators import decode_base64_image


class ApplicantTestScoreSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=Program.TEST_TYPE_CHOICES)
    score = serializers.DecimalField(max_digits=6, decimal_places=2)
    max_score = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=Decimal('100'))


class ExternalApplicationSerializer(serializers.Serializer):
    source_application_id = serializers.CharField(max_length=80)
    full_name = serializers.CharField(max_length=200)
    father_name = serializers.CharField(max_length=200)
    cnic = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    address = serializers.CharField(max_length=255)
    profile_photo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    matric_marks = serializers.IntegerField(min_value=0)
    matric_total = serializers.IntegerField(min_value=1)
    fsc_marks = serializers.IntegerField(min_value=0)
    fsc_total = serializers.IntegerField(min_value=1)
    tests = ApplicantTestScoreSerializer(many=True)
    campus_code = serializers.CharField(max_length=12)
    program_code = serializers.CharField(max_length=30)
    nationality = serializers.CharField(max_length=80, required=False, allow_blank=True)
    passport_number = serializers.CharField(max_length=40, required=False, allow_blank=True)
    visa_information = serializers.CharField(max_length=120, required=False, allow_blank=True)
    international_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    country = serializers.CharField(max_length=80, required=False, allow_blank=True)

    def validate_cnic(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('CNIC is required.')
        return value

    def validate(self, attrs):
        matric_total = attrs['matric_total']
        fsc_total = attrs['fsc_total']
        if attrs['matric_marks'] > matric_total:
            raise serializers.ValidationError({'matric_marks': ['Matric marks cannot exceed total marks.']})
        if attrs['fsc_marks'] > fsc_total:
            raise serializers.ValidationError({'fsc_marks': ['FSc marks cannot exceed total marks.']})

        try:
            attrs['campus'] = Campus.objects.get(code=attrs['campus_code'], is_active=True)
        except Campus.DoesNotExist as exc:
            raise serializers.ValidationError({'campus_code': ['Campus not found or inactive.']}) from exc

        try:
            attrs['program'] = Program.objects.select_related('department', 'department__campus').get(code=attrs['program_code'])
        except Program.DoesNotExist as exc:
            raise serializers.ValidationError({'program_code': ['Program not found.']}) from exc

        program_campus_id = attrs['program'].campus_id or attrs['program'].department.campus_id
        if program_campus_id != attrs['campus'].id:
            raise serializers.ValidationError({'program_code': ['Program does not belong to the selected campus.']})

        photo_value = attrs.get('profile_photo')
        if photo_value:
            try:
                attrs['profile_photo_file'] = decode_base64_image(photo_value)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'profile_photo': list(exc.messages)}) from exc
        else:
            attrs['profile_photo_file'] = None

        return attrs


class ApplicantSerializer(serializers.ModelSerializer):
    matric_percentage = serializers.SerializerMethodField()
    fsc_percentage = serializers.SerializerMethodField()
    test_scores = ApplicantTestScoreSerializer(many=True, read_only=True)

    class Meta:
        model = PISTApplicant
        fields = [
            'id', 'full_name', 'father_name', 'cnic', 'email', 'phone', 'address', 'profile_photo',
            'matric_marks', 'matric_total', 'fsc_marks', 'fsc_total', 'matric_percentage', 'fsc_percentage',
            'test_type', 'test_score', 'campus', 'program', 'roll_number', 'test_date', 'reporting_time',
            'test_venue', 'test_building', 'test_hall', 'status', 'source_application_id', 'nationality',
            'passport_number', 'visa_information', 'international_address', 'country', 'created_at', 'updated_at',
            'test_scores',
        ]

    def get_matric_percentage(self, obj):
        return round(obj.matric_percentage, 2)

    def get_fsc_percentage(self, obj):
        return round(obj.fsc_percentage, 2)
