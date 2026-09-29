import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from .constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from .models import Resume

def calculate_ats_score(skills):
    """
    Basic ATS score based on number of skills.
    This is a simple starting point.
    Later we can connect it with Job matching.
    """

    if not skills:
        return 0

    skill_list = [
        skill.strip()
        for skill in skills.split(",")
        if skill.strip()
    ]

    score = min(len(skill_list) * 10, 100)

    return score


@login_required
def resume_list(request):

    resumes = Resume.objects.filter(
        user=request.user
    )

    return render(
        request,
        "resume.html",
        {
            "resumes": resumes
        }
    )


@login_required
def upload_resume(request):

    if request.method == "POST":

        title = request.POST.get(
            "title",
            "My Resume"
        ).strip()

        skills = request.POST.get(
            "skills",
            ""
        ).strip()

        resume_file = request.FILES.get(
            "resume_file"
        )

        is_primary = request.POST.get(
            "is_primary"
        ) == "on"

        # --------------------------------
        # Check file
        # --------------------------------

        if not resume_file:

            messages.error(
                request,
                "Please select a resume file."
            )

            return render(
                request,
                "resume_upload.html"
            )

        # --------------------------------
        # Check extension
        # --------------------------------

        extension = os.path.splitext(
            resume_file.name
        )[1].lower()

        if extension not in ALLOWED_EXTENSIONS:

            messages.error(
                request,
                "Only PDF, DOC and DOCX files are allowed."
            )

            return render(
                request,
                "resume_upload.html"
            )

        # --------------------------------
        # Check file size
        # --------------------------------

        if resume_file.size > MAX_FILE_SIZE:

            messages.error(
                request,
                "Resume file size must be below 5 MB."
            )

            return render(
                request,
                "resume_upload.html"
            )

        # --------------------------------
        # ATS Score
        # --------------------------------

        ats_score = calculate_ats_score(
            skills
        )

        # --------------------------------
        # Primary Resume
        # --------------------------------

        if is_primary:

            Resume.objects.filter(
                user=request.user,
                is_primary=True
            ).update(
                is_primary=False
            )

        # If this is user's first resume
        # make it primary automatically.

        if not Resume.objects.filter(
            user=request.user
        ).exists():

            is_primary = True

        # --------------------------------
        # Create Resume
        # --------------------------------

        resume = Resume.objects.create(
            user=request.user,
            title=title or "My Resume",
            resume_file=resume_file,
            skills=skills,
            ats_score=ats_score,
            is_primary=is_primary,
        )

        messages.success(
            request,
            "Resume uploaded successfully."
        )

        return redirect(
            "resumes:resume_list"
        )

    return render(
        request,
        "resume_upload.html"
    )


@login_required
def resume_detail(request, pk):

    resume = get_object_or_404(
        Resume,
        pk=pk,
        user=request.user
    )

    return render(
        request,
        "resume.html",
        {
            "resume": resume,
            "resumes": [resume],
        }
    )


@login_required
def download_resume(request, pk):

    resume = get_object_or_404(
        Resume,
        pk=pk,
        user=request.user
    )

    if not resume.resume_file:
        raise Http404("Resume file not found.")

    try:

        response = FileResponse(
            resume.resume_file.open("rb"),
            as_attachment=True,
            filename=resume.file_name()
        )

        return response

    except FileNotFoundError:

        raise Http404(
            "Resume file not found."
        )


@login_required
def delete_resume(request, pk):

    resume = get_object_or_404(
        Resume,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":

        resume.resume_file.delete(
            save=False
        )

        resume.delete()

        messages.success(
            request,
            "Resume deleted successfully."
        )

        return redirect(
            "resumes:resume_list"
        )

    return render(
        request,
        "resume.html",
        {
            "resume": resume,
            "resumes": [resume],
        }
    )


@login_required
def set_primary_resume(request, pk):

    resume = get_object_or_404(
        Resume,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":

        Resume.objects.filter(
            user=request.user,
            is_primary=True
        ).update(
            is_primary=False
        )

        resume.is_primary = True
        resume.save()

        messages.success(
            request,
            "Primary resume updated."
        )

    return redirect(
        "resumes:resume_list"
    )
