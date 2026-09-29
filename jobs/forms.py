from decimal import Decimal
from django import forms

from companies.models import Company
from .models import Job


class JobForm(forms.ModelForm):
    salary_min = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01"})
    )
    salary_max = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01"})
    )
    vacancies = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={"min": "1", "step": "1"})
    )

    class Meta:
        model = Job
        fields = [
            "title",
            "company",
            "category",
            "location",
            "work_mode",
            "job_type",
            "experience_level",
            "salary_min",
            "salary_max",
            "vacancies",
            "application_deadline",
            "skills",
            "description",
            "requirements",
            "responsibilities",
        ]
        widgets = {
            "application_deadline": forms.DateInput(attrs={"type": "date"}),
            "skills": forms.Textarea(attrs={"rows": 3}),
            "description": forms.Textarea(attrs={"rows": 5}),
            "requirements": forms.Textarea(attrs={"rows": 4}),
            "responsibilities": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["company"].queryset = Company.objects.filter(verification_status="verified")
        self.fields["company"].empty_label = "Select a verified company"

    def clean_company(self):
        company = self.cleaned_data.get("company")
        if not company or company.verification_status != "verified":
            raise forms.ValidationError("Only companies with a verified status can post jobs.")
        return company

    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get("salary_min")
        salary_max = cleaned_data.get("salary_max")

        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            self.add_error("salary_max", "Maximum salary must be at least the minimum salary.")

        return cleaned_data