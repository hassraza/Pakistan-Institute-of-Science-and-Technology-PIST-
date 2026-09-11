from django.urls import path

from . import views

app_name = 'university_admin'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    
    # Applications
    path('applications/', views.applications, name='applications'),
    path('applications/<uuid:application_uuid>/', views.application_detail, name='application_detail'),
    path('applications/<uuid:application_uuid>/accept/', views.application_accept_action, name='application_accept_action'),
    path('applications/<uuid:application_uuid>/reject/', views.application_reject_action, name='application_reject_action'),
    path('applications/<uuid:application_uuid>/schedule/', views.application_schedule_action, name='application_schedule_action'),
    
    # Students Directory
    path('students/', views.students_list, name='students_list'),
    path('students/<uuid:student_id>/', views.student_detail, name='student_detail'),
    
    # Document Verification Queue
    path('documents/', views.documents_queue, name='documents_queue'),
    path('documents/<uuid:document_id>/review/', views.document_review_action, name='document_review_action'),
    
    # Programs & Admissions Control
    path('programs/', views.programs_list, name='programs'),
    path('programs/<int:program_id>/toggle/', views.program_toggle_admissions, name='program_toggle'),
    path('programs/<int:program_id>/edit/', views.program_edit, name='program_edit'),
    
    # Test Sessions Management
    path('test-sessions/', views.test_sessions_list, name='test_sessions'),
    path('test-sessions/<int:session_id>/toggle/', views.test_session_toggle, name='test_session_toggle'),
    
    # Notifications Broadcaster
    path('notifications/', views.notifications_list, name='notifications'),
    
    # Institutional Reports & Analytics (Figma Frame 1:4279)
    path('reports/', views.reports_view, name='reports'),
    
    # Exports
    path('exports/<str:format>/', views.export_applications, name='export_applications'),
]

