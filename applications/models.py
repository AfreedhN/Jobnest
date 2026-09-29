from django.contrib.auth.models import User
from django.db import models

from jobs.models import Job
from resumes.models import Resume


class Application(models.Model):

    STATUS_APPLIED = "applied"
    STATUS_REVIEW = "under_review"
    STATUS_SHORTLISTED = "shortlisted"
    STATUS_INTERVIEW = "interview"
    STATUS_SELECTED = "selected"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_APPLIED, "Applied"),
        (STATUS_REVIEW, "Under Review"),
        (STATUS_SHORTLISTED, "Shortlisted"),
        (STATUS_INTERVIEW, "Interview"),
        (STATUS_SELECTED, "Selected"),
        (STATUS_REJECTED, "Rejected"),
    ]

    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    resume = models.ForeignKey(
        Resume,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications"
    )

    cover_letter = models.TextField(blank=True)

    additional_information = models.TextField(blank=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_APPLIED,
        db_index=True
    )

    applied_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["applicant", "job"],
                name="unique_application_per_user_job"
            )
        ]

        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["applicant", "status"]),
        ]

    def __str__(self):
        return f"{self.applicant.username} - {self.job.title}"
