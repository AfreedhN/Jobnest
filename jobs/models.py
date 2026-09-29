from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from companies.models import Company



class JobCategoryQuerySet(models.QuerySet):
    def with_active_jobs(self):
        active_jobs = Job.objects.active()
        return (
            self.filter(jobs__in=active_jobs)
            .annotate(
                active_jobs_count=models.Count(
                    "jobs",
                    filter=models.Q(jobs__in=active_jobs),
                    distinct=True,
                )
            )
            .filter(active_jobs_count__gt=0)
            .distinct()
            .order_by("name")
        )


class JobCategory(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True
    )

    objects = JobCategoryQuerySet.as_manager()

    class Meta:
        verbose_name = "Job Category"
        verbose_name_plural = "Job Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class JobQuerySet(models.QuerySet):
    def active(self):
        today = timezone.now().date()
        return self.filter(
            models.Q(is_active=True) &
            models.Q(company__verification_status=Company.STATUS_VERIFIED) &
            (models.Q(application_deadline__gte=today) | models.Q(application_deadline__isnull=True))
        )

    def expired(self):
        today = timezone.now().date()
        return self.filter(
            models.Q(is_active=False) |
            models.Q(application_deadline__lt=today) |
            ~models.Q(company__verification_status=Company.STATUS_VERIFIED)
        )


class Job(models.Model):

    objects = JobQuerySet.as_manager()


    WORK_MODES = [
        ("remote", "Remote"),
        ("hybrid", "Hybrid"),
        ("onsite", "On-site"),
    ]

    JOB_TYPES = [
        ("full-time", "Full Time"),
        ("part-time", "Part Time"),
        ("internship", "Internship"),
        ("contract", "Contract"),
    ]

    EXPERIENCE_LEVELS = [
        ("entry", "Entry Level"),
        ("mid", "Mid Level"),
        ("senior", "Senior Level"),
    ]

    title = models.CharField(
        max_length=180,
        db_index=True
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="jobs"
    )

    recruiter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="posted_jobs"
    )

    category = models.ForeignKey(
        JobCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs"
    )

    location = models.CharField(
        max_length=160,
        db_index=True
    )

    work_mode = models.CharField(
        max_length=20,
        choices=WORK_MODES,
        default="onsite"
    )

    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPES,
        default="full-time"
    )

    experience_level = models.CharField(
        max_length=20,
        choices=EXPERIENCE_LEVELS,
        default="entry"
    )

    salary_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    salary_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    skills = models.TextField(
        help_text="Enter skills separated by commas"
    )

    description = models.TextField()

    requirements = models.TextField(
        blank=True,
        null=True
    )

    responsibilities = models.TextField(
        blank=True,
        null=True
    )

    vacancies = models.PositiveIntegerField(
        default=1
    )

    application_deadline = models.DateField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.company.name}"

    @property
    def salary_range(self):
        if self.salary_min and self.salary_max:
            return f"₹{self.salary_min} - ₹{self.salary_max}"

        if self.salary_min:
            return f"₹{self.salary_min}+"

        if self.salary_max:
            return f"Up to ₹{self.salary_max}"

        return "Salary not disclosed"

    @property
    def is_company_verified(self):
        if self.company_id:
            return getattr(self.company, "is_verified", False)
        return False

    @property
    def is_past_deadline(self):
        if self.application_deadline:
            return self.application_deadline < timezone.now().date()
        return False

    @property
    def is_open_for_applications(self):
        return (
            self.is_active
            and not self.is_past_deadline
            and self.is_company_verified
        )

    @property
    def is_expired(self):
        return (
            not self.is_active
            or self.is_past_deadline
            or not self.is_company_verified
        )

    def clean(self):
        super().clean()
        if self.company_id and not getattr(self.company, "is_verified", False):
            raise ValidationError({"company": "Only verified companies can post jobs."})


    @property
    def posted_by(self):
        return self.recruiter

    @posted_by.setter
    def posted_by(self, value):
        self.recruiter = value