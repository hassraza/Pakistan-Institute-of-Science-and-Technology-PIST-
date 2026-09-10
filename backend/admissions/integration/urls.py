from __future__ import annotations

from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from .views import (
    ApplicationCreateAPIView,
    ApplicationStatusAPIView,
    DocumentUploadAPIView,
    RollSlipAPIView,
    StudentCreateAPIView,
    StudentNotificationsAPIView,
)

app_name = 'integration'

urlpatterns = [
    # 1. Student Account Creation
    path('students/create/', StudentCreateAPIView.as_view(), name='student_create'),

    # 2. Application Submission
    path('applications/create/', ApplicationCreateAPIView.as_view(), name='application_create'),

    # 3. Document Upload
    path('documents/upload/', DocumentUploadAPIView.as_view(), name='document_upload'),

    # 4. Application Status (Dual routes: primary specification & PakUniPortal default)
    path('application-status/<str:application_id>/', ApplicationStatusAPIView.as_view(), name='application_status'),
    path('applications/<str:application_id>/', ApplicationStatusAPIView.as_view(), name='application_status_alt'),

    # 5. Student Notifications (Dual routes: primary specification & PakUniPortal default)
    path('notifications/<str:student_id>/', StudentNotificationsAPIView.as_view(), name='student_notifications'),
    path('students/<str:student_id>/notifications/', StudentNotificationsAPIView.as_view(), name='student_notifications_alt'),

    # 6. Roll Slip (Dual routes: primary specification & PakUniPortal default)
    path('roll-slip/<str:application_id>/', RollSlipAPIView.as_view(), name='roll_slip'),
    path('applications/<str:application_id>/roll-slip/', RollSlipAPIView.as_view(), name='roll_slip_alt'),

    # OpenAPI 3.0 Schema & Interactive Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='integration:schema'), name='swagger_ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='integration:schema'), name='redoc'),
]
