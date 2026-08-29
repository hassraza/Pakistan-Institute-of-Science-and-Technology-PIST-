from django.urls import path

from . import views

app_name = 'admissions'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('campuses/', views.campuses, name='campuses'),
    path('campuses/<str:campus_code>/', views.campus_detail, name='campus_detail'),
    path('departments/', views.departments, name='departments'),
    path('departments/<slug:department_slug>/', views.department_detail, name='department_detail'),
    path('programs/', views.programs, name='programs'),
    path('programs/<slug:program_slug>/', views.program_detail, name='program_detail'),
    path('admissions/', views.admission_procedure, name='admission_procedure'),
    path('admissions/how-it-works/', views.admission_procedure, name='how_it_works'),
    path('admissions/track/', views.track_application, name='track_application'),
    path('admissions/roll-slip/<uuid:application_uuid>/', views.roll_slip, name='roll_slip'),
    path('admissions/roll-slip/<uuid:application_uuid>/qr.png', views.roll_slip_qr, name='roll_slip_qr'),
    path('verify/<str:application_uuid>/', views.verify_application, name='verify_application'),
    path('verify/roll-slip/<uuid:qr_token>/', views.verify_roll_slip, name='verify_roll_slip'),
    path('research/', views.research, name='research'),
    path('student-life/', views.student_life, name='student_life'),
    path('contact/', views.contact, name='contact'),
]
