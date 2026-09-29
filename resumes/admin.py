from django.contrib import admin
from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "user",
        "ats_score",
        "is_primary",
        "uploaded_at",
    )

    list_filter = (
        "is_primary",
        "ats_score",
        "uploaded_at",
    )

    search_fields = (
        "title",
        "user__username",
        "user__email",
        "skills",
    )

    ordering = (
        "-uploaded_at",
    )

    readonly_fields = (
        "uploaded_at",
        "updated_at",
    )