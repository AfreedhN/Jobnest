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
        on_delete=models.CASCADE,
        related_name="ats_reports"
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="ats_reports"
    )

    overall_score = models.PositiveIntegerField(default=0)

    skills_score = models.PositiveIntegerField(default=0)

    experience_score = models.PositiveIntegerField(default=0)

    keywords_score = models.PositiveIntegerField(default=0)

    education_score = models.PositiveIntegerField(default=0)

    structure_score = models.PositiveIntegerField(default=0)

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

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.job.title} - "
            f"{self.overall_score}"
        )
