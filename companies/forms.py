from django import forms

from .models import Company


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            "name",
            "logo",
            "industry",
            "location",
            "website",
            "email",
            "phone",
            "company_size",
            "founded_year",
            "description",
            "about_company",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "about_company": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        companies = Company.objects.filter(name__iexact=name)
        if self.instance.pk:
            companies = companies.exclude(pk=self.instance.pk)
        if companies.exists():
            raise forms.ValidationError("A company with this name already exists.")
        return name