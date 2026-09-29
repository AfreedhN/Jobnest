from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from adm.models import Profile
from .forms import CompanyForm
from .models import Company


@login_required
def company_list(request):
    is_recruiter = (
        request.user.is_authenticated
        and Profile.objects.filter(user=request.user, account_type="recruiter").exists()
    )
    company_form = CompanyForm()
    show_company_form = False

    if request.method == "POST" and request.POST.get("form_action") == "add_company":
        if not is_recruiter:
            messages.error(request, "Only recruiters can add companies.")
            return redirect("companies:company_list")

        company_form = CompanyForm(request.POST, request.FILES)
        show_company_form = True
        if company_form.is_valid():
            company = company_form.save()
            messages.success(request, f"{company.name} added successfully.")
            return redirect("companies:company_list")

    companies = Company.objects.all()

    search = request.GET.get("search", "").strip()
    keyword = request.GET.get("keyword", "").strip()
    name = request.GET.get("name", "").strip()
    industry = request.GET.get("industry", "").strip()
    location = request.GET.get("location", "").strip()

    query = search or keyword
    if query:
        companies = companies.filter(
            Q(name__icontains=query)
            | Q(industry__icontains=query)
            | Q(location__icontains=query)
            | Q(description__icontains=query)
            | Q(about_company__icontains=query)
        )

    if name:
        companies = companies.filter(name__icontains=name)

    if industry and industry.lower() not in ("all", "all industries"):
        companies = companies.filter(
            industry__iexact=industry
        )

    if location and location.lower() not in ("all", "all locations"):
        companies = companies.filter(
            location__iexact=location
        )

    industries = (
        Company.objects
        .exclude(industry__isnull=True)
        .exclude(industry__exact="")
        .values_list("industry", flat=True)
        .distinct()
        .order_by("industry")
    )

    locations = (
        Company.objects
        .exclude(location__isnull=True)
        .exclude(location__exact="")
        .values_list("location", flat=True)
        .distinct()
        .order_by("location")
    )

    context = {
        "companies": companies,
        "industries": industries,
        "locations": locations,
        "search": search or keyword,
        "keyword": keyword,
        "name": name,
        "selected_industry": industry,
        "selected_location": location,
        "is_recruiter": is_recruiter,
        "company_form": company_form,
        "show_company_form": show_company_form,
    }

    return render(
        request,
        "companies/company_list.html",
        context
    )


@login_required
def company_detail(request, pk):
    company = get_object_or_404(
        Company,
        pk=pk
    )
    if company.is_verified:
        jobs = company.jobs.active().select_related("category")
    else:
        jobs = company.jobs.none()

    return render(
        request,
        "companies/company_detail.html",
        {
            "company": company,
            "jobs": jobs,
        }
    )


@login_required
def add_company(request):
    is_recruiter = (
        Profile.objects.filter(user=request.user, account_type="recruiter").exists()
        or request.user.is_staff
        or request.user.is_superuser
    )
    if not is_recruiter:
        messages.error(request, "Only recruiters can add companies.")
        return redirect("companies:company_list")

    form = CompanyForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        company = form.save()
        messages.success(request, f"{company.name} added successfully.")
        return redirect("companies:company_list")

    return render(
        request,
        "companies/company_form.html",
        {"form": form}
    )


@login_required
def edit_company(request, pk):
    is_recruiter = (
        Profile.objects.filter(user=request.user, account_type="recruiter").exists()
        or request.user.is_staff
        or request.user.is_superuser
    )
    if not is_recruiter:
        raise PermissionDenied("Only recruiters or administrators can edit company profiles.")

    company = get_object_or_404(
        Company,
        pk=pk
    )

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        industry = request.POST.get("industry", "").strip()
        location = request.POST.get("location", "").strip()

        if not name or not industry or not location:
            messages.error(
                request,
                "Company name, industry and location are required."
            )

            return render(
                request,
                "companies/company_form.html",
                {"company": company}
            )

        existing_company = Company.objects.filter(
            name__iexact=name
        ).exclude(
            pk=company.pk
        ).first()

        if existing_company:
            messages.error(
                request,
                "Another company with this name already exists."
            )

            return render(
                request,
                "companies/company_form.html",
                {"company": company}
            )

        company.name = name
        company.industry = industry
        company.location = location
        company.website = request.POST.get("website", "").strip() or None
        company.email = request.POST.get("email", "").strip() or None
        company.phone = request.POST.get("phone", "").strip() or None
        company.description = request.POST.get(
            "description", ""
        ).strip() or None

        company.company_size = request.POST.get(
            "company_size", ""
        ).strip() or None

        founded_year = request.POST.get(
            "founded_year", ""
        ).strip()

        company.founded_year = founded_year or None

        company.about_company = request.POST.get(
            "about_company", ""
        ).strip() or None

        if request.FILES.get("logo"):
            company.logo = request.FILES.get("logo")

        company.save()

        messages.success(
            request,
            f"{company.name} updated successfully."
        )

        return redirect(
            "companies:company_detail",
            pk=company.pk
        )

    return render(
        request,
        "companies/company_form.html",
        {
            "company": company
        }
    )


@login_required
def delete_company(request, pk):
    is_recruiter = (
        Profile.objects.filter(user=request.user, account_type="recruiter").exists()
        or request.user.is_staff
        or request.user.is_superuser
    )
    if not is_recruiter:
        raise PermissionDenied("Only recruiters or administrators can delete company profiles.")

    company = get_object_or_404(
        Company,
        pk=pk
    )

    if request.method == "POST":

        company_name = company.name

        company.delete()

        messages.success(
            request,
            f"{company_name} deleted successfully."
        )

        return redirect(
            "companies:company_list"
        )

    return render(
        request,
        "companies/company_confirm_delete.html",
        {
            "company": company
        }
    )
