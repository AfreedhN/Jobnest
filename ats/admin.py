from django.contrib import admin

from .models import ATSReport


@admin.register(ATSReport)
class ATSReportAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "job",
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
        "job__company__name",
    )

    readonly_fields = (
        "created_at",
    )
