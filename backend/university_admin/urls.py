from django.urls import path

from . import views

app_name = 'university_admin'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('applications/', views.applications, name='applications'),
    path('applications/<uuid:application_uuid>/', views.application_detail, name='application_detail'),
    path('documents/<uuid:document_id>/review/', views.document_review_action, name='document_review_action'),
    path('exports/<str:format>/', views.export_applications, name='export_applications'),
]
