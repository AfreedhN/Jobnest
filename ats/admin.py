from django.contrib import admin

from .models import ATSReport


@admin.register(ATSReport)
class ATSReportAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "get_target_job",
        "resume_name",
        "overall_score",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "job__title",
        "job_title_input",
        "job__company__name",
        "resume_name",
    )

    readonly_fields = (
        "created_at",
    )

    @admin.display(description="Target Job")
    def get_target_job(self, obj):
        return obj.job.title if obj.job else (obj.job_title_input or "General Analysis")
