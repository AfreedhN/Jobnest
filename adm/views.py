from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from adm.models import Profile
from companies.models import Company
from jobs.models import Job
from applications.models import Application
from resumes.models import Resume


@staff_member_required(login_url="login")
def admin_dashboard(request):

    context = {
        "users_count": User.objects.count(),

        "job_seekers_count": Profile.objects.filter(
            account_type="job_seeker"
        ).count(),

        "recruiters_count": Profile.objects.filter(
            account_type="recruiter"
        ).count(),

        "companies_count": Company.objects.count(),

        "verified_companies_count": Company.objects.filter(
            verification_status=Company.STATUS_VERIFIED
        ).count(),

        "unverified_companies_count": Company.objects.exclude(
            verification_status=Company.STATUS_VERIFIED
        ).count(),

        "jobs_count": Job.objects.active().count(),

        "applications_count": Application.objects.count(),

        "resumes_count": Resume.objects.count(),

        "recent_jobs": Job.objects.select_related(
            "company"
        ).order_by("-created_at")[:5],

        "recent_applications": Application.objects.select_related(
            "applicant",
            "job",
            "job__company"
        ).order_by("-applied_at")[:5],

        "pending_companies": Company.objects.exclude(
            verification_status=Company.STATUS_VERIFIED
        ).order_by("-created_at")[:10],

        "all_companies": Company.objects.all().order_by("-created_at")[:10],
    }

    return render(
        request,
        "admin_dashboard.html",
        context
    )


@staff_member_required(login_url="login")
@require_POST
def update_company_status(request, pk):
    company = get_object_or_404(Company, pk=pk)
    new_status = request.POST.get("status")
    if new_status in dict(Company.VERIFICATION_STATUS_CHOICES):
        company.verification_status = new_status
        company.save(update_fields=["verification_status", "updated_at"])
        messages.success(
            request,
            f"{company.name} verification status updated to {new_status.capitalize()}."
        )
    else:
        messages.error(request, "Invalid verification status.")
    return redirect("admin_dashboard")
