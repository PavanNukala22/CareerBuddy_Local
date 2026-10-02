from django.contrib import admin
from .models import EmployerProfile, JobPosting, JobApplication

@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'industry', 'location', 'company_size', 'created_at']
    search_fields = ['company_name', 'industry']

@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ['title', 'employer', 'job_type', 'experience', 'location', 'status', 'created_at']
    list_filter = ['status', 'job_type', 'experience']
    search_fields = ['title', 'skills_required']

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant_name', 'applicant_email', 'job', 'status', 'applied_at']
    list_filter = ['status']
    search_fields = ['applicant_name', 'applicant_email']
    list_editable = ['status']
