from django.db import models


class CompanyQuerySet(models.QuerySet):
    def verified(self):
        return self.filter(verification_status="verified")

    def unverified(self):
        return self.filter(verification_status="unverified")

    def suspended(self):
        return self.filter(verification_status="suspended")

    def rejected(self):
        return self.filter(verification_status="rejected")


class Company(models.Model):
    STATUS_UNVERIFIED = "unverified"
    STATUS_VERIFIED = "verified"
    STATUS_REJECTED = "rejected"
    STATUS_SUSPENDED = "suspended"

    VERIFICATION_STATUS_CHOICES = [
        (STATUS_UNVERIFIED, "Unverified"),
        (STATUS_VERIFIED, "Verified"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_SUSPENDED, "Suspended"),
    ]

    objects = CompanyQuerySet.as_manager()

    COMPANY_SIZES = [
        ("1-10", "1-10 Employees"),
        ("11-50", "11-50 Employees"),
        ("51-200", "51-200 Employees"),
        ("201-500", "201-500 Employees"),
        ("501-1000", "501-1000 Employees"),
        ("1000+", "1000+ Employees"),
    ]

    name = models.CharField(max_length=150, unique=True)
    logo = models.ImageField(
        upload_to="company_logos/",
        blank=True,
        null=True
    )
    industry = models.CharField(max_length=100)
    location = models.CharField(max_length=150)

    website = models.URLField(
        blank=True,
        null=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    company_size = models.CharField(
        max_length=20,
        choices=COMPANY_SIZES,
        blank=True,
        null=True
    )

    founded_year = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    about_company = models.TextField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default=STATUS_UNVERIFIED,
        db_index=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_verified(self):
        return self.verification_status == self.STATUS_VERIFIED

    @property
    def is_unverified(self):
        return self.verification_status == self.STATUS_UNVERIFIED

    @property
    def is_suspended(self):
        return self.verification_status == self.STATUS_SUSPENDED

    @property
    def is_rejected(self):
        return self.verification_status == self.STATUS_REJECTED

    @property
    def can_post_jobs(self):
        return self.is_verified and self.is_active
