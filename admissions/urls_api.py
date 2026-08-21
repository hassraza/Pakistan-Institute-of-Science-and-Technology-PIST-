from django.urls import path

from .views import ExternalApplicationAPIView, PublicApplicationLookupAPIView, PublicSiteAPIView

urlpatterns = [
    path('public/site/', PublicSiteAPIView.as_view(), name='public_site'),
    path('public/track/', PublicApplicationLookupAPIView.as_view(), name='public_track'),
    path('admissions/external-apply/', ExternalApplicationAPIView.as_view(), name='external_apply'),
]
