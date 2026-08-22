from django.urls import path

from . import views

app_name = 'students'

urlpatterns = [
    path('terms/', views.policy, {'policy_name': 'terms'}, name='terms'),
    path('privacy/', views.policy, {'policy_name': 'privacy'}, name='privacy'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('roll-slip/', views.roll_slip, name='roll_slip'),
    path('documents/', views.documents, name='documents'),
    path('documents/upload/', views.document_upload, name='document_upload'),
    path('documents/<uuid:doc_id>/view/', views.document_view, name='document_view'),
    path('documents/<uuid:doc_id>/replace/', views.document_replace, name='document_replace'),
    path('documents/<uuid:doc_id>/delete/', views.document_delete, name='document_delete'),
    path('academic-record/', views.academic_record, name='academic_record'),
    path('academic-record/matric/edit/', views.matric_edit, name='matric_edit'),
    path('academic-record/intermediate/edit/', views.intermediate_edit, name='intermediate_edit'),
    path('academic-record/test-scores/add/', views.test_score_add, name='test_score_add'),
    path('academic-record/test-scores/<uuid:score_id>/edit/', views.test_score_edit, name='test_score_edit'),
    path('academic-record/test-scores/<uuid:score_id>/delete/', views.test_score_delete, name='test_score_delete'),
    path('academic-record/test-scores/<uuid:score_id>/certificate/', views.test_certificate_view, name='test_certificate_view'),
    path('programs/<slug:program_slug>/apply/', views.apply_program, name='apply_program'),
    path('programs/<slug:program_slug>/submit/', views.submit_program_application, name='submit_program_application'),
    path('registered-programs/', views.registered_programs, name='registered_programs'),
    path('applications/<uuid:application_uuid>/', views.application_detail, name='application_detail'),
    path('applications/<uuid:application_uuid>/roll-slip/', views.application_roll_slip, name='application_roll_slip'),
    path('password/change/', views.password_change, name='password_change'),
    path('password/reset/', views.StudentPasswordResetView.as_view(), name='password_reset'),
    path('password/reset/done/', views.StudentPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/', views.StudentPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/reset/complete/', views.StudentPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
