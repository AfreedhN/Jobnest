from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from adm.models import Profile
from companies.models import Company
from .forms import JobForm
from .models import Job, JobCategory


@login_required
def job_list(request):
    is_recruiter = (
        request.user.is_authenticated
        and Profile.objects.filter(user=request.user, account_type="recruiter").exists()
    )
    job_form = JobForm()
    show_job_form = False

    if request.method == "POST" and request.POST.get("form_action") == "add_job":
        if not is_recruiter:
            messages.error(request, "Only recruiter accounts can post jobs.")
            return redirect("jobs:job_list")

        job_form = JobForm(request.POST)
        show_job_form = True
        if job_form.is_valid():
            job = job_form.save(commit=False)
            job.recruiter = request.user
            job.save()
            messages.success(request, "Job posted successfully.")
            return redirect("jobs:job_list")

    jobs = Job.objects.active().select_related(
        "company",
        "category"
    )

    available_categories = JobCategory.objects.with_active_jobs()

    q = request.GET.get("q", "").strip()
    search = request.GET.get("search", "").strip() or q
    role = request.GET.get("role", "").strip() or request.GET.get("job_title", "").strip()
    company = request.GET.get("company", "").strip()
    skill = request.GET.get("skill", "").strip() or request.GET.get("skills", "").strip()
    city = request.GET.get("city", "").strip()
    location = request.GET.get("location", "").strip() or city
    category = request.GET.get("category", "").strip()
    work_mode = request.GET.get("work_mode", "").strip()
    job_type = request.GET.get("job_type", "").strip()

    if category.lower() in ("all", "all categories", "none"):
        category = ""

    if search:
        base_q = (
            Q(title__icontains=search)
            | Q(company__name__icontains=search)
            | Q(skills__icontains=search)
            | Q(description__icontains=search)
        )
        words = [w for w in search.replace(",", " ").split() if w]
        if len(words) > 1:
            word_q = Q()
            for w in words:
                word_q &= (
                    Q(title__icontains=w)
                    | Q(company__name__icontains=w)
                    | Q(skills__icontains=w)
                    | Q(description__icontains=w)
                )
            jobs = jobs.filter(base_q | word_q)
        else:
            jobs = jobs.filter(base_q)

    if role:
        jobs = jobs.filter(title__icontains=role)

    if company:
        jobs = jobs.filter(company__name__icontains=company)

    if skill:
        jobs = jobs.filter(skills__icontains=skill)

    if city:
        jobs = jobs.filter(location__icontains=city)

    if location:
        jobs = jobs.filter(location__icontains=location)

    if category:
        if category.isdigit():
            jobs = jobs.filter(category_id=category)
        else:
            jobs = jobs.filter(category__name__iexact=category)

    if work_mode:
        jobs = jobs.filter(work_mode=work_mode)

    if job_type:
        jobs = jobs.filter(job_type=job_type)

    context = {
        "jobs": jobs,
        "categories": available_categories,
        "search": search,
        "role": role,
        "company": company,
        "skill": skill,
        "city": city,
        "location": location,
        "selected_category": category,
        "selected_work_mode": work_mode,
        "selected_job_type": job_type,
        "is_recruiter": is_recruiter,
        "job_form": job_form,
        "show_job_form": show_job_form,
        "has_verified_companies": Company.objects.filter(verification_status="verified").exists(),
    }

    return render(request, "jobs/job_list.html", context)


@login_required
def job_detail(request, pk):
    job = get_object_or_404(
        Job.objects.select_related("company", "category"),
        pk=pk,
    )
    if job.is_past_deadline and job.is_active:
        job.is_active = False
        job.save(update_fields=["is_active"])

    skills = [skill.strip() for skill in job.skills.split(",") if skill.strip()]
    has_applied = (
        request.user.is_authenticated
        and job.applications.filter(applicant=request.user).exists()
    )
    return render(
        request,
        "jobs/job_detail.html",
        {"job": job, "skills": skills, "has_applied": has_applied},
    )



@login_required
def add_job(request):
    if not Profile.objects.filter(
        user=request.user,
        account_type="recruiter"
    ).exists():
        messages.error(request, "Only recruiter accounts can post jobs.")
        return redirect("jobs:job_list")

    verified_companies = Company.objects.filter(verification_status="verified")
    if not verified_companies.exists():
        messages.warning(
            request,
            "No verified companies are available. Only companies with a verified status can post jobs."
        )

    form = JobForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        job = form.save(commit=False)
        job.recruiter = request.user
        job.save()
        messages.success(request, "Job posted successfully.")
        return redirect("jobs:job_list")

    return render(
        request,
        "jobs/job_form.html",
        {
            "form": form,
            "has_verified_companies": verified_companies.exists(),
        },
    )


@login_required
def edit_job(request, pk):
    job = get_object_or_404(Job, pk=pk)

    if job.recruiter != request.user and not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("You can only edit your own job postings.")

    verified_companies = Company.objects.filter(verification_status="verified")
    form = JobForm(request.POST or None, instance=job)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Job updated successfully.")
        return redirect("jobs:job_detail", pk=job.pk)

    return render(
        request,
        "jobs/job_form.html",
        {
            "form": form,
            "job": job,
            "is_edit": True,
            "has_verified_companies": verified_companies.exists(),
        },
    )


@login_required
def delete_job(request, pk):
    job = get_object_or_404(Job, pk=pk)

    if job.recruiter != request.user and not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("You can only delete your own job postings.")

    if request.method == "POST":
        job_title = job.title
        job.delete()
        messages.success(request, f"'{job_title}' deleted successfully.")
        return redirect("manage_jobs")

    return render(
        request,
        "jobs/job_confirm_delete.html",
        {"job": job},
    )
