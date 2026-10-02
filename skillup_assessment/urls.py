from django.urls import path

from . import views

urlpatterns = [
    path("", views.certifications_hub, name="skillup_certifications_hub"),

    # JSON API — consumed by the in-page Certifications section on the
    # static Skill Up page.
    path("api/status/", views.api_certifications_status, name="skillup_api_status"),
    path(
        "api/<str:module>/certificate/generate/",
        views.api_certificate_generate,
        name="skillup_api_certificate_generate",
    ),
    path(
        "api/<str:module>/certificate/regenerate/",
        views.api_certificate_regenerate,
        name="skillup_api_certificate_regenerate",
    ),

    # HTML pages — still work as direct/bookmarkable URLs.
    path("<str:module>/", views.module_detail, name="skillup_module_detail"),
    path(
        "<str:module>/certificate/name/",
        views.certificate_name_submit,
        name="skillup_certificate_name",
    ),
    path(
        "<str:module>/certificate/edit/",
        views.certificate_edit_name,
        name="skillup_certificate_edit",
    ),
    path(
        "<str:module>/certificate/download/",
        views.certificate_download,
        name="skillup_certificate_download",
    ),
]
