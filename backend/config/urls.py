from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from admissions import views as admissions_views

urlpatterns = [
    path('', include('admissions.urls')),
    path('api/v1/', include('admissions.urls_api')),
    path('university-admin/', include('university_admin.urls')),
    path('student/', include('students.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = admissions_views.page_not_found
handler403 = admissions_views.permission_denied
handler500 = admissions_views.server_error
