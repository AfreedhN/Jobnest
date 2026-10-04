import os
import mimetypes

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils._os import safe_join
from django.utils.http import url_has_allowed_host_and_scheme

from adm.models import Profile
from applications.models import Application
from ats.models import ATSReport
from ats.services import (
    ResumeTextError,
    analyze_resume_text,
    extract_resume_text,
    extract_resume_upload_text,
)
from companies.models import Company
from jobs.models import Job
from resumes.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from resumes.models import Resume


def home(request):
    q = request.GET.get("q", "").strip()
    search = request.GET.get("search", "").strip()
    job_title = request.GET.get("job_title", "").strip()
    title = request.GET.get("title", "").strip()
    skill = request.GET.get("skill", "").strip()
    skills = request.GET.get("skills", "").strip()
    keyword = request.GET.get("keyword", "").strip()
    keywords = request.GET.get("keywords", "").strip()
    location = request.GET.get("location", "").strip()
    city = request.GET.get("city", "").strip()

    title_query = job_title or title
    skill_query = skill or skills
    unified_query = q or search or keyword or keywords
    loc_query = location or city

    is_searching = bool(unified_query or title_query or skill_query or loc_query)

    jobs = Job.objects.active().select_related("company")

    if title_query:
        jobs = jobs.filter(title__icontains=title_query)

    if skill_query:
        jobs = jobs.filter(skills__icontains=skill_query)

    if unified_query:
        base_q = Q(title__icontains=unified_query) | Q(skills__icontains=unified_query)
        words = [w for w in unified_query.replace(",", " ").split() if w]
        if len(words) > 1:
            word_q = Q()
            for w in words:
                word_q &= (Q(title__icontains=w) | Q(skills__icontains=w))
            jobs = jobs.filter(base_q | word_q)
        else:
            jobs = jobs.filter(base_q)

    if loc_query:
        jobs = jobs.filter(location__icontains=loc_query)

    if is_searching:
        latest_jobs = jobs.order_by("-created_at")
    else:
        latest_jobs = jobs.order_by("-created_at")[:6]

    companies = Company.objects.order_by("name")[:6]
    total_jobs = Job.objects.active().count()
    total_companies = Company.objects.count()
    total_users = User.objects.filter(is_active=True).count()

    display_query = unified_query or title_query or skill_query

    return render(
        request,
        "home.html",
        {
            "latest_jobs": latest_jobs,
            "companies": companies,
            "total_jobs": total_jobs,
            "total_companies": total_companies,
            "total_users": total_users,
            "is_searching": is_searching,
            "search_query": display_query,
            "location_query": loc_query,
        }
    )


@login_required
def jobs(request):
    from jobs.views import job_list
    return job_list(request)


@login_required
def companies(request):
    from companies.views import company_list
    return company_list(request)


@login_required
def resume(request):
    resumes = Resume.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'resume.html', {'resumes': resumes})


@login_required
def my_applications(request):
    is_recruiter = (
        Profile.objects.filter(user=request.user, account_type="recruiter").exists()
        and not request.user.is_superuser
    )
    if is_recruiter:
        messages.info(request, "Recruiters manage candidate applications directly from the Recruiter Dashboard.")
        return redirect("recruiter_dashboard")

    applications = (
        Application.objects.filter(applicant=request.user)
        .select_related("job__company", "resume")
        .order_by("-applied_at")
    )
    return render(request, 'my_applications.html', {'applications': applications})


@login_required
def recruiter_dashboard(request):
    is_recruiter = (
        Profile.objects.filter(user=request.user, account_type="recruiter").exists()
        or request.user.is_staff
        or request.user.is_superuser
    )

    if not is_recruiter:
        messages.info(request, "Redirected to your Job Seeker Dashboard.")
        return redirect("dashboard:dashboard_home")

    recruiter_jobs = (
        Job.objects.filter(recruiter=request.user)
        .select_related("company")
        .prefetch_related("applications")
    )
    total_jobs = recruiter_jobs.count()
    active_jobs = recruiter_jobs.active().count()

    recruiter_applications = Application.objects.filter(job__recruiter=request.user)
    total_applications = recruiter_applications.count()
    pending_applications = recruiter_applications.filter(
        status__in=[Application.STATUS_PENDING, Application.STATUS_APPLIED, Application.STATUS_REVIEW]
    ).count()
    shortlisted = recruiter_applications.filter(status=Application.STATUS_SHORTLISTED).count()
    interviews = recruiter_applications.filter(status=Application.STATUS_INTERVIEW).count()
    selected_count = recruiter_applications.filter(status=Application.STATUS_SELECTED).count()
    rejected_count = recruiter_applications.filter(status=Application.STATUS_REJECTED).count()

    # 1. Recent Applications (latest 8 for overview)
    recent_applications = (
        recruiter_applications
        .select_related("applicant", "job", "resume")
        .order_by("-applied_at")[:8]
    )

    # 2. Pending Applications (dedicated pending review queue)
    pending_applications_list = (
        recruiter_applications
        .filter(status__in=[Application.STATUS_PENDING, Application.STATUS_APPLIED, Application.STATUS_REVIEW])
        .select_related("applicant", "job__company", "resume")
        .order_by("-applied_at")
    )

    # 3. Candidate Pipeline & Review Candidates (complete workflow with filtering)
    job_filter = request.GET.get("job")
    status_filter = request.GET.get("status")

    pipeline_queryset = recruiter_applications.select_related("applicant", "job__company", "resume")
    if job_filter:
        pipeline_queryset = pipeline_queryset.filter(job_id=job_filter)
    if status_filter and status_filter in dict(Application.STATUS_CHOICES):
        pipeline_queryset = pipeline_queryset.filter(status=status_filter)

    pipeline_applications = pipeline_queryset.order_by("-applied_at")

    jobs = recruiter_jobs.order_by("-created_at")[:6]
    all_recruiter_jobs = recruiter_jobs.order_by("-created_at")
    recruiter_company = recruiter_jobs.first().company if recruiter_jobs.exists() else None

    context = {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "pending_applications": pending_applications,
        "shortlisted": shortlisted,
        "interviews": interviews,
        "selected_count": selected_count,
        "rejected_count": rejected_count,
        "recent_applications": recent_applications,
        "pending_applications_list": pending_applications_list,
        "pipeline_applications": pipeline_applications,
        "status_choices": Application.STATUS_CHOICES,
        "jobs": jobs,
        "all_recruiter_jobs": all_recruiter_jobs,
        "recruiter_company": recruiter_company,
        "selected_job_filter": job_filter,
        "selected_status_filter": status_filter,
    }
    return render(request, "recruiter_dashboard.html", context)


@login_required
def profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    skills = [
        skill.strip()
        for skill in (profile.skills or "").split(",")
        if skill.strip()
    ]
    return render(
        request,
        "profile.html",
        {"profile": profile, "skills": skills}
    )


def logout_view(request):
    logout(request)
    return redirect('home')


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    error = None
    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=identifier, password=password)

        if user is None and identifier:
            matching_user = User.objects.filter(email__iexact=identifier).first()
            if matching_user:
                user = authenticate(
                    request,
                    username=matching_user.username,
                    password=password
                )

        if user is not None:
            login(request, user)
            request.session.modified = True
            messages.success(
                request,
                "Login successful.",
                extra_tags="account-success login-success",
            )

            if url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("home")

        error = "Invalid username/email or password."

    return render(request, "login.html", {"error": error, "next": next_url})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    field_errors = {}
    form_data = {}
    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == "POST":
        form_data = request.POST
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        account_type = request.POST.get("account_type", "")
        accepted_terms = request.POST.get("terms") == "on"

        if not first_name:
            field_errors["first_name"] = "First name is required."
        if not email:
            field_errors["email"] = "Email address is required."
        if not username:
            field_errors["username"] = "Username is required."
        if not password:
            field_errors["password"] = "Password is required."
        if not confirm_password:
            field_errors["confirm_password"] = "Please confirm your password."
        if not account_type:
            field_errors["account_type"] = "Choose an account type."
        if not accepted_terms:
            field_errors["terms"] = "You must agree to the terms and conditions."

        if not field_errors and account_type not in dict(Profile.ACCOUNT_TYPES):
            field_errors["account_type"] = "Choose a valid account type."
        elif not field_errors and User.objects.filter(username__iexact=username).exists():
            field_errors["username"] = "That username is already in use."
        elif not field_errors and User.objects.filter(email__iexact=email).exists():
            field_errors["email"] = "An account with that email already exists."
        elif not field_errors and password != confirm_password:
            field_errors["confirm_password"] = "The passwords do not match."
        elif not field_errors:
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            try:
                forms.EmailField().clean(email)
            except ValidationError as validation_error:
                field_errors["email"] = " ".join(validation_error.messages)

            try:
                User._meta.get_field("username").clean(username, None)
            except ValidationError as validation_error:
                field_errors["username"] = " ".join(validation_error.messages)

            if not field_errors:
                try:
                    validate_password(password, user)
                except ValidationError as validation_error:
                    field_errors["password"] = " ".join(validation_error.messages)

        if not field_errors:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                Profile.objects.create(user=user, account_type=account_type)

            login(request, user)
            request.session.modified = True
            messages.success(
                request,
                "Your account has been created successfully.",
                extra_tags="account-success register-success",
            )
            if url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("home")

    return render(
        request,
        "register.html",
        {"field_errors": field_errors, "form_data": form_data, "next": next_url},
    )


@login_required
def resume_upload(request):
    if request.method == 'POST':
        resume_file = request.FILES.get('resume_file')
        is_primary = request.POST.get('is_primary') == 'on'

        if not resume_file:
            messages.error(request, 'Please select a resume file.')
            return render(request, 'resume_upload.html', {'error': 'Please select a resume file.'})

        extension = os.path.splitext(resume_file.name)[1].lower()
        if extension not in {'.pdf', '.doc', '.docx'}:
            messages.error(request, 'Only PDF, DOC and DOCX files are allowed.')
            return render(request, 'resume_upload.html', {'error': 'Only PDF, DOC and DOCX files are allowed.'})

        if resume_file.size > 5 * 1024 * 1024:
            messages.error(request, 'Resume file size must be below 5 MB.')
            return render(request, 'resume_upload.html', {'error': 'Resume file size must be below 5 MB.'})

        if is_primary:
            Resume.objects.filter(user=request.user, is_primary=True).update(is_primary=False)

        if not Resume.objects.filter(user=request.user).exists():
            is_primary = True

        Resume.objects.create(
            user=request.user,
            title=resume_file.name,
            resume_file=resume_file,
            is_primary=is_primary,
        )

        messages.success(request, 'Resume uploaded successfully.')
        return redirect('resume')

    return render(request, 'resume_upload.html')


@login_required
def ats_analyzer(request):
    resumes = Resume.objects.filter(user=request.user).order_by('-uploaded_at')
    jobs = Job.objects.active().select_related('company')
    selected_resume_id = ''
    selected_job_id = ''
    custom_job_title = ''
    custom_job_description = ''
    analysis_mode = 'job'
    error = None

    if request.method == 'POST':
        selected_resume_id = request.POST.get('resume', '').strip()
        selected_job_id = request.POST.get('job', '').strip()
        custom_job_title = request.POST.get('custom_job_title', '').strip()
        custom_job_description = request.POST.get('custom_job_description', '').strip()
        analysis_mode = request.POST.get('analysis_mode', 'job')
        uploaded_resume = request.FILES.get('resume_file')

        resume = resumes.filter(pk=selected_resume_id).first() if selected_resume_id else None
        job = jobs.filter(pk=selected_job_id).first() if selected_job_id else None

        if selected_job_id and not job:
            error = 'Please choose a valid job.'
        elif not job and not custom_job_description and analysis_mode == 'job' and not selected_job_id:
            error = 'Please choose a valid job.'
        elif uploaded_resume:
            if uploaded_resume.size > MAX_FILE_SIZE:
                error = 'Resume file size must be below 5 MB.'
            else:
                try:
                    resume_text = extract_resume_upload_text(uploaded_resume)
                except ResumeTextError as parse_error:
                    error = str(parse_error)
                else:
                    analysis = analyze_resume_text(
                        resume_text,
                        job=job,
                        custom_job_title=custom_job_title,
                        custom_job_description=custom_job_description,
                    )
                    valid_report_fields = {f.name for f in ATSReport._meta.get_fields()}
                    report_data = {k: v for k, v in analysis.items() if k in valid_report_fields}
                    with transaction.atomic():
                        resume = Resume.objects.create(
                            user=request.user,
                            title=os.path.basename(uploaded_resume.name)[:150] or 'ATS resume',
                            resume_file=uploaded_resume,
                            is_primary=not resumes.exists(),
                        )
                        report = ATSReport.objects.create(
                            user=request.user,
                            resume=resume,
                            resume_name=resume.title,
                            job=job,
                            job_title_input=custom_job_title or (job.title if job else "General ATS Analysis"),
                            job_company_name=job.company.name if (job and getattr(job, "company", None)) else "",
                            job_description_input=custom_job_description if not job else "",
                            **report_data,
                        )
                    return render(request, 'ats_result.html', {'report': report})
        elif not resume:
            error = 'Choose a saved resume or upload a PDF or DOCX resume.'
        elif not resume.file_exists:
            error = f'The selected resume "{resume.title or resume.file_name()}" is missing from the server. Please upload your resume directly.'
        else:
            try:
                resume_text = extract_resume_text(resume)
            except ResumeTextError as parse_error:
                error = str(parse_error)
            else:
                analysis = analyze_resume_text(
                    resume_text,
                    job=job,
                    custom_job_title=custom_job_title,
                    custom_job_description=custom_job_description,
                )
                valid_report_fields = {f.name for f in ATSReport._meta.get_fields()}
                report_data = {k: v for k, v in analysis.items() if k in valid_report_fields}
                report = ATSReport.objects.create(
                    user=request.user,
                    resume=resume,
                    resume_name=resume.title,
                    job=job,
                    job_title_input=custom_job_title or (job.title if job else "General ATS Analysis"),
                    job_company_name=job.company.name if (job and getattr(job, "company", None)) else "",
                    job_description_input=custom_job_description if not job else "",
                    **report_data,
                )
                return render(request, 'ats_result.html', {'report': report})

    return render(
        request,
        'ats_analyzer.html',
        {
            'resumes': resumes,
            'jobs': jobs,
            'selected_resume_id': selected_resume_id,
            'selected_job_id': selected_job_id,
            'custom_job_title': custom_job_title,
            'custom_job_description': custom_job_description,
            'analysis_mode': analysis_mode,
            'error': error,
        },
    )


@login_required
def apply_view(request, job_id=None):
    job = get_object_or_404(Job.objects.select_related('company'), pk=job_id) if job_id else None

    if not Profile.objects.filter(
        user=request.user,
        account_type='job_seeker'
    ).exists():
        messages.error(request, 'Only job seekers can apply for jobs.')
        if job:
            return redirect('jobs:job_detail', pk=job.pk)
        return redirect('jobs:job_list')

    if job and Application.objects.filter(applicant=request.user, job=job).exists():
        messages.info(request, 'You have already applied for this job.')
        return redirect('jobs:job_detail', pk=job.pk)

    if job and not job.is_open_for_applications:
        if not job.is_company_verified:
            messages.error(request, 'This job is not accepting applications because the company is not verified.')
        elif job.is_past_deadline:
            deadline_str = job.application_deadline.strftime("%d %b %Y") if job.application_deadline else ""
            messages.error(
                request,
                f'The application deadline for this job ({deadline_str}) has passed. Applications are no longer accepted.'
            )
        else:
            messages.error(request, 'This job is inactive and is no longer accepting applications.')
        return redirect('jobs:job_detail', pk=job.pk)


    resumes = Resume.objects.filter(user=request.user).order_by('-uploaded_at')


    if request.method == 'POST':
        if not job:
            messages.error(request, 'Please choose a valid job.')
            return redirect('jobs:job_list')

        uploaded_resume = request.FILES.get('resume_file')
        resume_id = request.POST.get('resume')
        resume = None
        error = None

        if uploaded_resume:
            extension = os.path.splitext(uploaded_resume.name)[1].lower()
            if extension not in ALLOWED_EXTENSIONS:
                error = 'Only PDF, DOC, or DOCX files are allowed.'
            elif uploaded_resume.size > MAX_FILE_SIZE:
                error = 'Resume file size must be below 5 MB.'
        else:
            resume = resumes.filter(pk=resume_id).first()
            if not resume:
                error = 'Choose a saved resume or upload a PDF, DOC, or DOCX file.'
            elif not resume.file_exists:
                error = f'The selected resume "{resume.title or resume.file_name()}" is missing from the server. Please upload a new resume file below.'

        if error:
            return render(
                request,
                'apply.html',
                {
                    'job': job,
                    'job_id': job_id,
                    'resumes': resumes,
                    'error': error,
                    'form_data': request.POST,
                },
            )

        if Application.objects.filter(applicant=request.user, job=job).exists():
            messages.info(request, 'You have already applied for this job.')
            return redirect('jobs:job_detail', pk=job.pk)

        with transaction.atomic():
            if uploaded_resume:
                resume = Resume.objects.create(
                    user=request.user,
                    resume_file=uploaded_resume,
                    is_primary=not resumes.exists(),
                )

            Application.objects.create(
                applicant=request.user,
                job=job,
                resume=resume,
                cover_letter=request.POST.get('cover_letter', '').strip(),
                additional_information=request.POST.get('additional_information', '').strip(),
                status=Application.STATUS_PENDING,
            )

        messages.success(
            request,
            'Application submitted successfully.',
            extra_tags='application-submitted',
        )
        return redirect('jobs:job_detail', pk=job.pk)

    return render(
        request,
        'apply.html',
        {'job': job, 'job_id': job_id, 'resumes': resumes},
    )


@login_required
def manage_jobs(request):
    is_recruiter = (
        Profile.objects.filter(user=request.user, account_type="recruiter").exists()
        or request.user.is_staff
        or request.user.is_superuser
    )

    if not is_recruiter:
        messages.error(request, "Only recruiters can manage jobs.")
        return redirect("jobs:job_list")

    jobs = (
        Job.objects.filter(recruiter=request.user)
        .select_related("company")
        .prefetch_related("applications")
        .order_by("-created_at")
    )
    return render(request, "manage_jobs.html", {"jobs": jobs})


@login_required
def post_job(request):
    is_recruiter = (
        Profile.objects.filter(user=request.user, account_type="recruiter").exists()
        or request.user.is_staff
        or request.user.is_superuser
    )

    if not is_recruiter:
        messages.error(request, "Only recruiters can post jobs.")
        return redirect("jobs:job_list")

    return redirect("jobs:add_job")


@login_required
def manage_applicants(request):
    is_recruiter = (
        Profile.objects.filter(user=request.user, account_type="recruiter").exists()
        or request.user.is_staff
        or request.user.is_superuser
    )

    if not is_recruiter:
        messages.error(request, "Only recruiters can manage applicants.")
        return redirect("home")

    job_id = request.GET.get("job")
    status_param = request.GET.get("status")
    params = []
    if job_id:
        params.append(f"job={job_id}")
    if status_param:
        params.append(f"status={status_param}")
    query = f"?{'&'.join(params)}" if params else ""
    return redirect(f"{reverse('recruiter_dashboard')}{query}#candidate-pipeline")


@login_required
def application_details(request, pk):
    application = get_object_or_404(
        Application.objects.select_related("applicant", "job__company", "resume"),
        pk=pk,
    )
    is_applicant = (application.applicant_id == request.user.id)
    is_job_recruiter = (
        (Profile.objects.filter(user=request.user, account_type="recruiter").exists()
         and application.job.recruiter_id == request.user.id)
        or request.user.is_staff
        or request.user.is_superuser
    )

    if not (is_applicant or is_job_recruiter):
        raise PermissionDenied("You are not authorized to view this application.")

    return render(
        request,
        "application_details.html",
        {
            "application": application,
            "is_job_recruiter": is_job_recruiter,
            "status_choices": Application.STATUS_CHOICES,
        },
    )


@require_POST
@login_required
def update_application_status(request, pk):
    is_recruiter = (
        Profile.objects.filter(user=request.user, account_type="recruiter").exists()
        or request.user.is_staff
        or request.user.is_superuser
    )

    if not is_recruiter:
        messages.error(request, "Only recruiters can update application status.")
        return redirect("home")

    application = get_object_or_404(Application, pk=pk)
    if application.job.recruiter_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("You can only update applications for your own jobs.")

    status = request.POST.get("status")

    if status in dict(Application.STATUS_CHOICES):
        application.status = status
        application.save(update_fields=["status", "updated_at"])
        messages.success(
            request,
            f"Application status updated to {application.get_status_display()}.",
            extra_tags="account-success application-status-success",
        )
    else:
        messages.error(request, "Invalid application status.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect(f"{reverse('recruiter_dashboard')}#candidate-pipeline")


@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Disallow any file uploads other than 'profile_photo'
        if any(key != "profile_photo" for key in request.FILES.keys()):
            messages.error(request, "Only a profile photo can be uploaded. No other files or documents are allowed.")
            return render(request, "edit_profile.html", {"profile": profile})

        photo = request.FILES.get("profile_photo")
        if photo:
            ext = os.path.splitext(photo.name)[1].lower()
            allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
            if ext not in allowed_extensions:
                messages.error(
                    request,
                    "Only image files (JPG, JPEG, PNG, WEBP, GIF) are allowed for profile photo. Documents or other files cannot be uploaded."
                )
                return render(request, "edit_profile.html", {"profile": profile})

            try:
                from PIL import Image
                photo.seek(0)
                img = Image.open(photo)
                img.verify()
                photo.seek(0)
            except Exception:
                messages.error(request, "Invalid image file. Please upload a valid photo.")
                return render(request, "edit_profile.html", {"profile": profile})

            profile.profile_photo = photo

        request.user.first_name = request.POST.get("first_name", "").strip()
        request.user.last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()

        if email:
            request.user.email = email

        request.user.save(update_fields=["first_name", "last_name", "email"])

        profile.phone = request.POST.get("phone", "").strip()
        profile.location = request.POST.get("location", "").strip()
        profile.professional_headline = request.POST.get("professional_headline", "").strip()
        profile.about = request.POST.get("about", "").strip()
        profile.skills = request.POST.get("skills", "").strip()
        profile.education = request.POST.get("education", "").strip()
        profile.experience = request.POST.get("experience", "").strip()
        profile.linkedin = request.POST.get("linkedin", "").strip() or ""
        profile.github = request.POST.get("github", "").strip() or ""
        profile.portfolio = request.POST.get("portfolio", "").strip() or ""

        profile.save()
        messages.success(
            request,
            "Your profile has been updated successfully.",
            extra_tags="account-success profile-success",
        )
        return redirect("profile")

    return render(request, "edit_profile.html", {"profile": profile})


def serve_media(request, path):
    """
    Safely serves uploaded media files (resumes, company logos, etc.) in both
    local development and Render production environments.
    If the requested file does not exist on disk, renders a friendly
    'Resume File Not Found' page instead of throwing an unhandled Http404.
    """
    try:
        fullpath = safe_join(settings.MEDIA_ROOT, path)
    except Exception:
        raise Http404("Invalid media path.")

    if os.path.exists(fullpath) and os.path.isfile(fullpath):
        content_type, encoding = mimetypes.guess_type(fullpath)
        content_type = content_type or "application/octet-stream"
        response = FileResponse(open(fullpath, "rb"), content_type=content_type)
        if content_type in ("application/pdf", "image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"):
            response["Content-Disposition"] = f'inline; filename="{os.path.basename(fullpath)}"'
        else:
            response["Content-Disposition"] = f'attachment; filename="{os.path.basename(fullpath)}"'
        if encoding:
            response["Content-Encoding"] = encoding
        return response

    filename = os.path.basename(path)
    is_resume = "resume" in path.lower() or path.lower().endswith((".pdf", ".doc", ".docx"))
    return render(
        request,
        "media_not_found.html",
        {
            "filename": filename,
            "path": path,
            "is_resume": is_resume,
        },
        status=404,
    )

