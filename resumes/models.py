from django.db import models
from django.contrib.auth.models import User


class Resume(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="resumes"
    )

    title = models.CharField(
        max_length=150,
        default="My Resume"
    )

    resume_file = models.FileField(
        upload_to="resumes/"
    )

    skills = models.TextField(
        blank=True,
        null=True,
        help_text="Enter skills separated by commas"
    )

    ats_score = models.PositiveIntegerField(
        default=0
    )

    is_primary = models.BooleanField(
        default=False
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def file_extension(self):
        if not self.resume_file:
            return ""

        return self.resume_file.name.split(".")[-1].lower()

    def file_name(self):
        if not self.resume_file:
            return ""

        return self.resume_file.name.split("/")[-1]
