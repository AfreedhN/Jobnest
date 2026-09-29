from django.contrib import admin
from .models import Job, JobCategory


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "name",
    )


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "company",
        "category",
        "location",
        "work_mode",
        "job_type",
        "experience_level",
        "vacancies",
        "is_active",
        "created_at",
    )

    list_filter = (
        "work_mode",
        "job_type",
        "experience_level",
        "is_active",
        "category",
        "company",
    )

    search_fields = (
        "title",
        "company__name",
        "location",
        "skills",
        "description",
    )

    list_editable = (
        "is_active",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
