from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from activities import views as activity_views
from jobs_app import views as job_views
from career_app import views as career_views
from career_app import manual_resume_views
from career_app import create_resume_views
from riya_bot.skillup_views import skillup_hub
import subject_views

from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from core.media_views import serve_protected_media
from core.nav_views import nav_go

urlpatterns = [
    # SR-04 fix: résumés and selfies must be authenticated + ownership-checked;
    # placed ahead of the catch-all static() media route below so these two
    # categories win. Every other media path (logos, etc.) still falls through
    # to the plain static() route further down, unauthenticated as before.
    path('media/resumes/<str:filename>', serve_protected_media, {'category': 'resumes'}, name='serve_protected_resume'),
    path('media/selfies/<str:filename>', serve_protected_media, {'category': 'selfies'}, name='serve_protected_selfie'),
    # Served from OUTSIDE /media/ deliberately. Deployments carry a
    # `location /media/ { alias ...; }` block that nginx matches BEFORE the
    # request reaches Django; with the recordings in MinIO there is no file on
    # disk at that path, so nginx answered 404. Nothing fronts this prefix, so
    # the access-checked view always runs.
    path('interview-recording/<str:filename>', serve_protected_media, {'category': 'interview_videos'}, name='serve_protected_interview_video'),
    path('media/interview_videos/<str:filename>', serve_protected_media, {'category': 'interview_videos'}, name='serve_protected_interview_video_legacy'),
    path('admin/', admin.site.urls),

    # Landing-page navigation gateway. Every Skill Up / Resources link
    # goes through here so the login check and the post-login redirect
    # are identical for all of them (core/navigation.py holds the map).
    path('go/<slug:key>/', nav_go, name='nav_go'),
    path('', activity_views.home, name='home'),
    path('careers/<slug:track>/', activity_views.career_path, name='career_path'),
    path('dashboard/', activity_views.dashboard, name='student_dashboard'),
    path('applications/<int:pk>/', job_views.my_application_detail, name='my_application_detail'),
    path('activities/', include('activities.urls')),
    path('skill-up/', skillup_hub, name='skill_up'),
    path('skill-up/assessment/', include('skillup_assessment.urls')),
    path('static/001 Career Buddy/', RedirectView.as_view(url='/skill-up/', permanent=False)),
    path('static/001%20Career%20Buddy/', RedirectView.as_view(url='/skill-up/', permanent=False)),
    path('users/', include('users.urls')),

    # ── Workshop Modules ──────────────────────────────────────────────────────
    path('gd/', include('GD_app.urls')),
    path('jam/', include('jam_app.urls')),
    path('roleplay/', include('activities.roleplay_urls')),

    # ── Grammar Module ────────────────────────────────────────────────────────
    path('subject/', subject_views.subject_home, name='subject'),
    path('subject/slides/<slug:slug>/<path:file_name>', subject_views.subject_slide_image, name='subject_slide_image'),
    path('subject/video/<slug:slug>.mp4', subject_views.subject_video, name='subject_video'),
    path('subject/illustrations/<slug:slug>/<int:index>.svg', subject_views.subject_illustration, name='subject_illustration'),
    path('subject/<slug:slug>.html', subject_views.subject_topic, name='subject_topic'),

    # ── Employer Portal ───────────────────────────────────────────────────────
    path('employer/', include('employer_portal.urls')),
    # Global alias so redirect('job_home') works from any view
    path('employer-home/', job_views.home, name='job_home'),

    # ── Pro Subscription & Access ─────────────────────────────────────────────
    path('pro/', career_views.pro_page, name='pro_page'),
    path('pro/toggle/', career_views.toggle_pro_status, name='toggle_pro_status'),
    path('pro/create-order/', career_views.create_razorpay_order, name='create_razorpay_order'),
    path('pro/verify-payment/', career_views.verify_razorpay_payment, name='verify_razorpay_payment'),
    # BUG-03 fix: server-side webhook — activates plan even if browser closes early
    path('pro/webhook/razorpay/', career_views.razorpay_webhook, name='razorpay_webhook'),
    # GST tax invoice for a paid subscription (owner/staff only)
    path('pro/invoice/<int:pk>/', career_views.payment_invoice, name='payment_invoice'),

    # ── Resume Builder & Career ───────────────────────────────────────────────
    path('resume-builder/', include([
        path('', career_views.resume_builder_home, name='resume_builder'),
        path('match/', career_views.resume_job_match, name='resume_job_match'),
        path('start-interview/', career_views.resume_start_interview, name='resume_start_interview'),
        path('interview/chat/', career_views.resume_interview_chat, name='resume_interview_chat'),
        path('camera-verified/', career_views.resume_camera_verified, name='resume_camera_verified'),
        path('upload-interview-video/', career_views.resume_upload_interview_video, name='resume_upload_interview_video'),
        path('record-violation/', career_views.resume_record_violation, name='resume_record_violation'),
        path('violation-state/', career_views.resume_violation_state, name='resume_violation_state'),
        path('get-question/', career_views.resume_get_next_question, name='resume_get_next_question'),
        path('submit-answer/', career_views.resume_submit_answer, name='resume_submit_answer'),
        path('transcribe-answer/', career_views.resume_transcribe_answer, name='resume_transcribe_answer'),
        path('analytics/', career_views.resume_analytics, name='resume_analytics'),
        path('history/', career_views.resume_history, name='resume_history'),
        path('reanalyze/<int:resume_id>/', career_views.resume_reanalyze, name='resume_reanalyze'),
        # Manual (rule-based, no-AI) builder used by the landing-page role cards.
        path('manual/roles/', manual_resume_views.roles_api, name='manual_resume_roles'),
        path('manual/preview/', manual_resume_views.preview_api, name='manual_resume_preview'),
        path('manual/pdf/', manual_resume_views.pdf_download, name='manual_resume_pdf'),
        path('manual/pages/', manual_resume_views.preview_pages_api, name='manual_resume_pages'),
        # Create Resume builder (landing page): fully manual, no AI.
        path('create/preview/', create_resume_views.preview_api, name='create_resume_preview'),
        path('create/pdf/', create_resume_views.pdf_download, name='create_resume_pdf'),
        path('create/pages/', create_resume_views.pages_api, name='create_resume_pages'),
        path('create/drafts/', create_resume_views.drafts_list, name='create_resume_drafts'),
        path('create/drafts/save/', create_resume_views.draft_save, name='create_resume_draft_save'),
        path('create/drafts/<int:pk>/', create_resume_views.draft_detail, name='create_resume_draft'),
        path('create/drafts/<int:pk>/delete/', create_resume_views.draft_delete, name='create_resume_draft_delete'),
    ])),

    # ── AI Chatbot (Riya) ─────────────────────────────────────────────────────
    path('', include('riya_bot.urls')),

    # Plain STATIC_URL, not staticfiles_storage.url(): the latter resolves the
    # manifest hash at import time and raises if the file is missing, which took
    # the whole urlconf (and site) down under DEBUG=False. This never raises.
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'img/favicon.ico')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
