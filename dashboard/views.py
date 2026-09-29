from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from companies.models import Company
from jobs.models import Job
from applications.models import Application


@login_required
def dashboard_home(request):

    user = request.user

    # -----------------------------
    # General Statistics
    # -----------------------------

    total_companies = Company.objects.count()
    total_jobs = Job.objects.active().count()
    total_applications = Application.objects.count()

    # -----------------------------
    # User Applications
    # -----------------------------

    my_applications = Application.objects.filter(
        applicant=user
    ).select_related(
        "job", "job__company"
    ).order_by(
        "-applied_at"
    )

    my_application_count = my_applications.count()

    # -----------------------------
    # Application Status
    # -----------------------------

    pending_count = my_applications.filter(
        status="applied"
    ).count()

    shortlisted_count = my_applications.filter(
        status="shortlisted"
    ).count()

    rejected_count = my_applications.filter(
        status="rejected"
    ).count()

    hired_count = my_applications.filter(
        status="selected"
    ).count()

    # -----------------------------
    # Latest Jobs
    # -----------------------------

    latest_jobs = Job.objects.active().select_related(
        "company",
        "category"
    ).order_by(
        "-id"
    )[:6]

    # -----------------------------
    # Context
    # -----------------------------

    context = {
        "user": user,

        "total_companies": total_companies,
        "total_jobs": total_jobs,
        "total_applications": total_applications,

        "my_applications": my_applications,
        "my_application_count": my_application_count,

        "pending_count": pending_count,
        "shortlisted_count": shortlisted_count,
        "rejected_count": rejected_count,
        "hired_count": hired_count,

        "latest_jobs": latest_jobs,
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )
