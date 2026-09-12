from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.test import TestCase

from admissions.models import Campus, Department, Program
from admissions.pakuniportal_sync import (
    serialize_program_for_sync,
    sync_program_to_pakuniportal,
    bulk_sync_all_programs,
)



class PakUniPortalSyncTests(TestCase):
    def setUp(self):
        self.campus = Campus.objects.create(
            name='Pakistan Institute of Science and Technology — Islamabad Main Campus',
            city='Islamabad',
            code='ISB',
            is_main_campus=True,
        )
        self.dept = Department.objects.create(
            campus=self.campus,
            name='Department of Computer Science',
            code='CS',
        )

    @patch('admissions.pakuniportal_sync.requests.post')
    def test_serialize_program_for_sync(self, mock_post):
        program = Program.objects.create(
            department=self.dept,
            campus=self.campus,
            name='BS Artificial Intelligence',
            code='BSAI-ISB',
            duration='4 Years',
            degree_level='Undergraduate',
            eligibility_percentage=Decimal('60.00'),
            required_test_type='USAT',
            admissions_open=True,
            description='Premier AI program.',
        )
        data = serialize_program_for_sync(program, action='upsert')
        self.assertEqual(data['code'], 'BSAI-ISB')
        self.assertEqual(data['name'], 'BS Artificial Intelligence')
        self.assertEqual(data['department_name'], 'Department of Computer Science')
        self.assertEqual(data['degree_level'], 'Undergraduate')
        self.assertEqual(data['eligibility_percentage'], 60.0)
        self.assertEqual(data['required_test_type'], 'USAT')
        self.assertTrue(data['admissions_open'])
        self.assertEqual(data['action'], 'upsert')

    @patch('admissions.pakuniportal_sync.requests.post')
    def test_sync_program_to_pakuniportal_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success'}
        mock_post.return_value = mock_response

        program = Program.objects.create(
            department=self.dept,
            campus=self.campus,
            name='BS Data Science',
            code='BSDS-ISB',
            eligibility_percentage=Decimal('65.00'),
        )
        # Signal called it once; reset mock for direct test
        mock_post.reset_mock()

        success, result = sync_program_to_pakuniportal(program, action='upsert')
        self.assertTrue(success)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn('api/v1/pist/programs/sync/', args[0])
        self.assertEqual(kwargs['headers']['X-API-KEY'], 'pist-integration-secret-key-2026')
        self.assertEqual(kwargs['json']['code'], 'BSDS-ISB')


    @patch('admissions.pakuniportal_sync.requests.post')
    def test_signal_triggers_on_create_and_delete(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success'}
        mock_post.return_value = mock_response

        # Creating program triggers post_save signal
        prog = Program.objects.create(
            department=self.dept,
            campus=self.campus,
            name='BS Cyber Security',
            code='BSCYS-ISB',
        )
        self.assertTrue(mock_post.called)
        last_action = mock_post.call_args[1]['json']['action']
        self.assertEqual(last_action, 'upsert')

        mock_post.reset_mock()
        # Deleting program triggers post_delete signal
        prog.delete()
        self.assertTrue(mock_post.called)
        delete_action = mock_post.call_args[1]['json']['action']
        self.assertEqual(delete_action, 'delete')
