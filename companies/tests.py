from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from adm.models import Profile
from .models import Company


class CompanyModelTest(TestCase):

    def setUp(self):
        self.company = Company.objects.create(
            name="TechNova Solutions",
            industry="Information Technology",
            location="Chennai",
            company_size="51-200",
            founded_year=2015
        )

    def test_company_created(self):
        self.assertEqual(
            self.company.name,
            "TechNova Solutions"
        )

    def test_company_string(self):
        self.assertEqual(
            str(self.company),
            "TechNova Solutions"
        )


class CompanyViewTest(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="compviewuser", password="password123")
        self.client.force_login(self.user)
        self.company = Company.objects.create(
            name="TechNova Solutions",
            industry="Information Technology",
            location="Chennai"
        )

    def test_unauthenticated_user_redirected_to_login_from_company_list(self):
        self.client.logout()
        response = self.client.get(reverse("companies:company_list"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('companies:company_list')}")

    def test_unauthenticated_user_redirected_to_login_from_company_detail(self):
        self.client.logout()
        response = self.client.get(reverse("companies:company_detail", kwargs={"pk": self.company.pk}))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('companies:company_detail', kwargs={'pk': self.company.pk})}")

    def test_company_list(self):
        response = self.client.get(
            reverse("companies:company_list")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertContains(
            response,
            "TechNova Solutions"
        )

    def test_company_detail(self):
        response = self.client.get(
            reverse(
                "companies:company_detail",
                kwargs={"pk": self.company.pk}
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertContains(
            response,
            "TechNova Solutions"
        )
        self.assertContains(response, "Information Technology")
        self.assertContains(response, "Company details")

    def test_company_card_links_to_its_detail_page(self):
        response = self.client.get(reverse("companies:company_list"))

        self.assertContains(
            response,
            reverse(
                "companies:company_detail",
                kwargs={"pk": self.company.pk}
            )
        )

    def test_root_companies_page_loads_real_companies(self):
        response = self.client.get("/companies/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TechNova Solutions")


class CompanyAddViewTest(TestCase):

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="company-owner",
            password="test-password"
        )
        Profile.objects.create(user=self.user, account_type="recruiter")
        self.client.force_login(self.user)

    def test_recruiter_add_company_form_is_inline_on_companies_page(self):
        response = self.client.get(reverse("companies:company_list"))

        self.assertContains(response, 'id="addCompanyDialog"')
        self.assertContains(response, 'name="form_action" value="add_company"')
        self.assertContains(response, 'data-open-dialog="addCompanyDialog"')
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_recruiter_can_add_company_from_companies_page(self):
        response = self.client.post(
            reverse("companies:company_list"),
            {
                "form_action": "add_company",
                "name": "Inline Northstar",
                "industry": "Technology",
                "location": "Chennai",
            },
        )

        self.assertRedirects(response, reverse("companies:company_list"))
        self.assertTrue(Company.objects.filter(name="Inline Northstar").exists())

    def test_invalid_inline_company_form_reopens_on_companies_page(self):
        Company.objects.create(
            name="Existing Company",
            industry="Technology",
            location="Chennai",
        )

        response = self.client.post(
            reverse("companies:company_list"),
            {
                "form_action": "add_company",
                "name": "existing company",
                "industry": "Technology",
                "location": "Chennai",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["show_company_form"])
        self.assertContains(response, "A company with this name already exists.")

    def test_add_company_redirects_to_directory(self):
        response = self.client.post(
            reverse("companies:add_company"),
            {
                "name": "Northstar Labs",
                "industry": "Technology",
                "location": "Chennai",
            }
        )

        self.assertRedirects(
            response,
            reverse("companies:company_list")
        )
        self.assertTrue(
            Company.objects.filter(name="Northstar Labs").exists()
        )

    def test_job_seekers_cannot_add_company(self):
        job_seeker = get_user_model().objects.create_user(
            username="job-seeker",
            password="test-password"
        )
        Profile.objects.create(user=job_seeker, account_type="job_seeker")
        self.client.force_login(job_seeker)

        response = self.client.post(
            reverse("companies:add_company"),
            {
                "name": "Hidden Company",
                "industry": "Technology",
                "location": "Chennai",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Company.objects.filter(name="Hidden Company").exists())
        self.assertNotContains(response, "Add company")

    def test_add_company_rejects_case_insensitive_duplicate(self):
        Company.objects.create(
            name="Northstar Labs",
            industry="Technology",
            location="Chennai"
        )

        response = self.client.post(
            reverse("companies:add_company"),
            {
                "name": "northstar labs",
                "industry": "Technology",
                "location": "Chennai",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.context["form"].errors)

    def test_newly_added_company_defaults_to_unverified(self):
        response = self.client.post(
            reverse("companies:add_company"),
            {
                "name": "Brand New Corp",
                "industry": "Finance",
                "location": "Mumbai",
            },
        )
        self.assertRedirects(response, reverse("companies:company_list"))
        comp = Company.objects.get(name="Brand New Corp")
        self.assertEqual(comp.verification_status, Company.STATUS_UNVERIFIED)
        self.assertFalse(comp.is_verified)
        self.assertFalse(comp.can_post_jobs)


class CompanyAdminVerificationTest(TestCase):

    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_superuser(
            username="admin-user",
            password="admin-password",
            email="admin@example.com",
        )
        self.company = Company.objects.create(
            name="Startup X",
            industry="Healthcare",
            location="Hyderabad",
            verification_status="unverified",
        )
        self.client.force_login(self.staff_user)

    def test_admin_dashboard_displays_unverified_company(self):
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Startup X")
        self.assertContains(response, "Unverified")

    def test_admin_can_verify_company_via_dashboard_action(self):
        response = self.client.post(
            reverse("update_company_status", kwargs={"pk": self.company.pk}),
            {"status": "verified"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.verification_status, "verified")
        self.assertTrue(self.company.is_verified)
        self.assertTrue(self.company.can_post_jobs)

    def test_admin_can_suspend_and_reject_company(self):
        for status in ("suspended", "rejected"):
            response = self.client.post(
                reverse("update_company_status", kwargs={"pk": self.company.pk}),
                {"status": status},
                follow=True,
            )
            self.assertEqual(response.status_code, 200)
            self.company.refresh_from_db()
            self.assertEqual(self.company.verification_status, status)
            self.assertFalse(self.company.can_post_jobs)


class CompanySearchAndFilterTest(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="compfilteruser", password="password123")
        self.client.force_login(self.user)
        self.c1 = Company.objects.create(
            name="Alpha Technologies",
            industry="Software Engineering",
            location="Bengaluru, Karnataka",
            description="Leading AI and cloud engineering company.",
            verification_status="verified",
        )
        self.c2 = Company.objects.create(
            name="Beta Financial",
            industry="Banking & Finance",
            location="Mumbai, Maharashtra",
            description="Global banking and fintech provider.",
            verification_status="verified",
        )
        self.c3 = Company.objects.create(
            name="Gamma Healthcare",
            industry="Healthcare & Biotech",
            location="Chennai, Tamil Nadu",
            description="Innovative biotech solutions and research.",
            verification_status="verified",
        )

    def test_search_by_name_or_keyword(self):
        response = self.client.get(reverse("companies:company_list"), {"search": "Alpha"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha Technologies")
        self.assertNotContains(response, "Beta Financial")
        self.assertNotContains(response, "Gamma Healthcare")

        # Keyword in description
        response = self.client.get(reverse("companies:company_list"), {"keyword": "fintech"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Beta Financial")
        self.assertNotContains(response, "Alpha Technologies")

    def test_filter_by_industry(self):
        response = self.client.get(reverse("companies:company_list"), {"industry": "Software Engineering"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha Technologies")
        self.assertNotContains(response, "Beta Financial")
        self.assertNotContains(response, "Gamma Healthcare")

        # All industries option
        response_all = self.client.get(reverse("companies:company_list"), {"industry": "All industries"})
        self.assertEqual(response_all.status_code, 200)
        self.assertContains(response_all, "Alpha Technologies")
        self.assertContains(response_all, "Beta Financial")
        self.assertContains(response_all, "Gamma Healthcare")

    def test_filter_by_location(self):
        response = self.client.get(reverse("companies:company_list"), {"location": "Chennai, Tamil Nadu"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gamma Healthcare")
        self.assertNotContains(response, "Alpha Technologies")
        self.assertNotContains(response, "Beta Financial")

        # All locations option
        response_all = self.client.get(reverse("companies:company_list"), {"location": "All locations"})
        self.assertEqual(response_all.status_code, 200)
        self.assertContains(response_all, "Alpha Technologies")
        self.assertContains(response_all, "Beta Financial")
        self.assertContains(response_all, "Gamma Healthcare")

    def test_dynamic_industries_and_locations_lists(self):
        response = self.client.get(reverse("companies:company_list"))
        self.assertEqual(response.status_code, 200)
        industries = list(response.context["industries"])
        locations = list(response.context["locations"])

        self.assertIn("Software Engineering", industries)
        self.assertIn("Banking & Finance", industries)
        self.assertIn("Healthcare & Biotech", industries)
        self.assertNotIn("Nonexistent Industry", industries)

        self.assertIn("Bengaluru, Karnataka", locations)
        self.assertIn("Mumbai, Maharashtra", locations)
        self.assertIn("Chennai, Tamil Nadu", locations)
        self.assertNotIn("Nonexistent Location", locations)

    def test_no_results_found_when_no_match(self):
        response = self.client.get(reverse("companies:company_list"), {"search": "NonexistentCompany12345"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No results found")
        self.assertContains(response, "No companies found matching your search or filter criteria")
        self.assertNotContains(response, "Alpha Technologies")
        self.assertNotContains(response, "Beta Financial")
        self.assertNotContains(response, "Gamma Healthcare")

    def test_edit_company_forbidden_for_job_seeker(self):
        User = get_user_model()
        seeker = User.objects.create_user(username="seeker_edit", password="password")
        Profile.objects.create(user=seeker, account_type="job_seeker")
        self.client.force_login(seeker)

        response = self.client.get(reverse("companies:edit_company", kwargs={"pk": self.c1.pk}))
        self.assertEqual(response.status_code, 403)

    def test_edit_company_allowed_for_recruiter(self):
        User = get_user_model()
        recruiter = User.objects.create_user(username="recruiter_edit", password="password")
        Profile.objects.create(user=recruiter, account_type="recruiter")
        self.client.force_login(recruiter)

        response = self.client.get(reverse("companies:edit_company", kwargs={"pk": self.c1.pk}))
        self.assertEqual(response.status_code, 200)

    def test_delete_company_forbidden_for_job_seeker(self):
        User = get_user_model()
        seeker = User.objects.create_user(username="seeker_delete", password="password")
        Profile.objects.create(user=seeker, account_type="job_seeker")
        self.client.force_login(seeker)

        response = self.client.get(reverse("companies:delete_company", kwargs={"pk": self.c1.pk}))
        self.assertEqual(response.status_code, 403)

    def test_delete_company_renders_confirm_and_deletes_for_recruiter(self):
        User = get_user_model()
        recruiter = User.objects.create_user(username="recruiter_delete", password="password")
        Profile.objects.create(user=recruiter, account_type="recruiter")
        self.client.force_login(recruiter)

        # GET confirmation page
        response = self.client.get(reverse("companies:delete_company", kwargs={"pk": self.c1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete Company Profile?")
        self.assertContains(response, self.c1.name)

        # POST delete
        post_response = self.client.post(reverse("companies:delete_company", kwargs={"pk": self.c1.pk}))
        self.assertRedirects(post_response, reverse("companies:company_list"))
        self.assertFalse(Company.objects.filter(pk=self.c1.pk).exists())

