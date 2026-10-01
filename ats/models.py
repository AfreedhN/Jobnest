from django.contrib.auth.models import User
from django.db import models

from jobs.models import Job
from resumes.models import Resume


class ATSReport(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ats_reports"
    )

    resume = models.ForeignKey(
        Resume,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ats_reports"
    )

    resume_name = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ats_reports"
    )

    job_title_input = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    job_company_name = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    job_description_input = models.TextField(
        blank=True,
        default=""
    )

    overall_score = models.PositiveIntegerField(default=0)

    skills_score = models.PositiveIntegerField(default=0)

    experience_score = models.PositiveIntegerField(default=0)

    keywords_score = models.PositiveIntegerField(default=0)

    education_score = models.PositiveIntegerField(default=0)

    structure_score = models.PositiveIntegerField(default=0)

    formatting_score = models.PositiveIntegerField(default=0)

    projects_score = models.PositiveIntegerField(default=0)

    matched_skills = models.JSONField(
        default=list,
        blank=True
    )

    missing_skills = models.JSONField(
        default=list,
        blank=True
    )

    matched_keywords = models.JSONField(
        default=list,
        blank=True
    )

    missing_keywords = models.JSONField(
        default=list,
        blank=True
    )

    suggestions = models.JSONField(
        default=list,
        blank=True
    )

    line_improvements = models.JSONField(
        default=list,
        blank=True
    )

    section_analysis = models.JSONField(
        default=dict,
        blank=True
    )

    formatting_issues = models.JSONField(
        default=list,
        blank=True
    )

    skills_categorized = models.JSONField(
        default=dict,
        blank=True
    )

    critical_issues = models.JSONField(
        default=list,
        blank=True
    )

    score_breakdown = models.JSONField(
        default=dict,
        blank=True
    )

    improvement_checklist = models.JSONField(
        default=list,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        target = self.job.title if self.job else (self.job_title_input or "General Analysis")
        return (
            f"{self.user.username} - "
            f"{target} - "
            f"{self.overall_score}"
        )
