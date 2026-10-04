from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, re_path, include
from django.urls import reverse_lazy
from django.conf import settings

from companies.views import company_detail as company_detail_view
from jobs.views import job_detail as job_detail_view
from resumes.views import (
    delete_resume as delete_resume_view,
    set_primary_resume as set_primary_resume_view,
    view_resume as view_resume_view,
    download_resume as download_resume_view,
)
from .forms import JobNestPasswordResetForm
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("home/", views.home, name="home_alias"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            form_class=JobNestPasswordResetForm,
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    path("admin-panel/", include("adm.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("companies/", include("companies.urls")),
    path("jobs/", include("jobs.urls")),
    path("applications/", include("applications.urls")),
    path("resumes/", include("resumes.urls")),


    path("company-details/<int:pk>/", company_detail_view, name="company_details"),
    path("job-details/<int:pk>/", job_detail_view, name="job_details"),
    path("apply/<int:job_id>/", views.apply_view, name="apply"),
    path("ats-analyzer/", views.ats_analyzer, name="ats_analyzer"),
    path("resume/", views.resume, name="resume"),
    path("resume-upload/", views.resume_upload, name="resume_upload"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("manage-jobs/", views.manage_jobs, name="manage_jobs"),
    path("post-job/", views.post_job, name="post_job"),
    path("manage-applicants/", views.manage_applicants, name="manage_applicants"),
    path("applications/<int:pk>/", views.application_details, name="application_details"),
    path("applications/<int:pk>/update-status/", views.update_application_status, name="update_application_status"),
    path("resumes/<int:pk>/view/", view_resume_view, name="view_resume"),
    path("resumes/<int:pk>/download/", download_resume_view, name="download_resume"),
    path("resumes/<int:pk>/delete/", delete_resume_view, name="delete_resume"),
    path("resumes/<int:pk>/primary/", set_primary_resume_view, name="set_primary_resume"),
    path("my-applications/", views.my_applications, name="my_applications"),
    path("recruiter-dashboard/", views.recruiter_dashboard, name="recruiter_dashboard"),

    # Safely serve uploaded media files in development and production (Render)
    re_path(r"^media/(?P<path>.*)$", views.serve_media, name="serve_media"),
]