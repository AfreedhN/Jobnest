from django.contrib import admin
from django.utils.html import format_html
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "verification_badge",
        "verification_status",
        "is_active",
        "industry",
        "location",
        "company_size",
        "created_at",
    )

    list_filter = (
        "verification_status",
        "is_active",
        "industry",
        "location",
        "company_size",
    )

    search_fields = (
        "name",
        "industry",
        "location",
        "description",
    )

    list_editable = (
        "verification_status",
        "is_active",
    )

    ordering = ("name",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    actions = [
        "mark_as_verified",
        "mark_as_unverified",
        "mark_as_suspended",
        "mark_as_rejected",
    ]

    @admin.display(description="Verification")
    def verification_badge(self, obj):
        colors = {
            "verified": "#16a34a",
            "unverified": "#ca8a04",
            "suspended": "#dc2626",
            "rejected": "#6b7280",
        }
        color = colors.get(obj.verification_status, "#6b7280")
        label = obj.get_verification_status_display()
        return format_html(
            '<span style="background-color: {}; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; text-transform: uppercase;">{}</span>',
            color,
            label,
        )

    @admin.action(description="Verify selected companies (Enables job posting)")
    def mark_as_verified(self, request, queryset):
        count = queryset.update(verification_status=Company.STATUS_VERIFIED)
        self.message_user(
            request,
            f"{count} company/companies successfully verified. They can now post jobs immediately."
        )

    @admin.action(description="Mark selected companies as unverified")
    def mark_as_unverified(self, request, queryset):
        count = queryset.update(verification_status=Company.STATUS_UNVERIFIED)
        self.message_user(
            request,
            f"{count} company/companies marked as unverified."
        )

    @admin.action(description="Suspend selected companies (Disables job posting)")
    def mark_as_suspended(self, request, queryset):
        count = queryset.update(verification_status=Company.STATUS_SUSPENDED)
        self.message_user(
            request,
            f"{count} company/companies suspended. Job posting is disabled."
        )

    @admin.action(description="Reject selected companies")
    def mark_as_rejected(self, request, queryset):
        count = queryset.update(verification_status=Company.STATUS_REJECTED)
        self.message_user(
            request,
            f"{count} company/companies rejected."
        )
