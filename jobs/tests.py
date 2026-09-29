from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from adm.models import Profile
from companies.models import Company
from .models import Job, JobCategory


class JobModelTest(TestCase):

    def setUp(self):

        self.company = Company.objects.create(
            name="TechNova Solutions",
            industry="Information Technology",
            location="Chennai",
            verification_status="verified",
        )

        self.category = JobCategory.objects.create(
            name="Software Development"
        )

        self.job = Job.objects.create(
            title="Python Developer",
            company=self.company,
            category=self.category,
            location="Chennai",
            work_mode="hybrid",
            job_type="full-time",
            experience_level="entry",
            skills="Python, Django, PostgreSQL",
            description="Develop web applications using Django.",
            vacancies=2
        )

    def test_job_created(self):

        self.assertEqual(
            self.job.title,
            "Python Developer"
        )

    def test_job_string(self):

        self.assertEqual(
            str(self.job),
            "Python Developer - TechNova Solutions"
        )

    def test_job_salary_range_without_salary(self):

        self.assertEqual(
            self.job.salary_range,
            "Salary not disclosed"
        )

    def test_job_deadline_properties(self):
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.now().date()

        self.assertFalse(self.job.is_past_deadline)
        self.assertTrue(self.job.is_open_for_applications)

        self.job.application_deadline = today - timedelta(days=1)
        self.assertTrue(self.job.is_past_deadline)
        self.assertFalse(self.job.is_open_for_applications)

        self.job.application_deadline = today + timedelta(days=5)
        self.assertFalse(self.job.is_past_deadline)
        self.assertTrue(self.job.is_open_for_applications)



class JobViewTest(TestCase):

    def setUp(self):

        self.company = Company.objects.create(
            name="TechNova Solutions",
            industry="Information Technology",
            location="Chennai",
            verification_status="verified",
        )

        self.category = JobCategory.objects.create(name="Software Development")
        self.empty_category = JobCategory.objects.create(name="Data Science")

        self.job = Job.objects.create(
            title="Python Developer",
            company=self.company,
            category=self.category,
            location="Chennai",
            work_mode="remote",
            job_type="full-time",
            experience_level="entry",
            skills="Python, Django",
            description="Python development job.",
            vacancies=1
        )

        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123"
        )
        Profile.objects.create(user=self.user, account_type="recruiter")
        self.job_seeker = User.objects.create_user(
            username="jobseeker",
            password="testpassword123"
        )
        Profile.objects.create(user=self.job_seeker, account_type="job_seeker")
        self.client.force_login(self.job_seeker)

    def test_unauthenticated_user_redirected_to_login_from_job_list(self):
        self.client.logout()
        response = self.client.get(reverse("jobs:job_list"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('jobs:job_list')}")

    def test_unauthenticated_user_redirected_to_login_from_job_detail(self):
        self.client.logout()
        response = self.client.get(reverse("jobs:job_detail", kwargs={"pk": self.job.pk}))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('jobs:job_detail', kwargs={'pk': self.job.pk})}")

    def test_job_list(self):

        response = self.client.get(
            reverse("jobs:job_list")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertContains(
            response,
            "Python Developer"
        )

    def test_root_jobs_page_loads_real_jobs(self):

        response = self.client.get(
            "/jobs/"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertContains(
            response,
            "Python Developer"
        )

    def test_job_detail(self):

        response = self.client.get(
            reverse(
                "jobs:job_detail",
                kwargs={
                    "pk": self.job.pk
                }
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertContains(
            response,
            "Python Developer"
        )

    def test_apply_option_is_only_shown_to_job_seekers(self):
        detail_url = reverse(
            "jobs:job_detail",
            kwargs={"pk": self.job.pk}
        )

        self.client.force_login(self.job_seeker)
        seeker_response = self.client.get(detail_url)
        self.assertContains(seeker_response, "Apply Now")
        self.assertNotContains(seeker_response, "Add Company")
        self.assertNotContains(seeker_response, "Add Jobs")

        self.client.force_login(self.user)
        recruiter_response = self.client.get(detail_url)
        self.assertNotContains(recruiter_response, "Apply Now")

    def test_job_detail_shows_closed_when_deadline_passed(self):
        from datetime import timedelta
        from django.utils import timezone
        self.job.application_deadline = timezone.now().date() - timedelta(days=1)
        self.job.save()

        detail_url = reverse("jobs:job_detail", kwargs={"pk": self.job.pk})
        self.client.force_login(self.job_seeker)
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Applications Closed")
        self.assertContains(response, "(Expired)")
        self.assertNotContains(response, "Apply Now")

    def test_job_detail_shows_closed_when_inactive(self):
        self.job.is_active = False
        self.job.save()

        detail_url = reverse("jobs:job_detail", kwargs={"pk": self.job.pk})
        self.client.force_login(self.job_seeker)
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Applications Closed")
        self.assertNotContains(response, "Apply Now")

    def test_job_list_and_detail_display_vacancies(self):
        self.job.vacancies = 3
        self.job.save()

        list_response = self.client.get(reverse("jobs:job_list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "3 vacancies")

        detail_response = self.client.get(reverse("jobs:job_detail", kwargs={"pk": self.job.pk}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Vacancies")
        self.assertContains(detail_response, "3 open positions")

    def test_job_list_only_displays_active_non_expired_jobs(self):
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.now().date()

        active_job = Job.objects.create(
            title="Active Future Role",
            company=self.company,
            location="Remote",
            description="Active role.",
            vacancies=1,
            is_active=True,
            application_deadline=today + timedelta(days=10),
        )

        expired_job = Job.objects.create(
            title="Expired Role",
            company=self.company,
            location="Remote",
            description="Expired role.",
            vacancies=1,
            is_active=True,
            application_deadline=today - timedelta(days=2),
        )

        inactive_job = Job.objects.create(
            title="Inactive Role",
            company=self.company,
            location="Remote",
            description="Inactive role.",
            vacancies=1,
            is_active=False,
        )

        response = self.client.get(reverse("jobs:job_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Future Role")
        self.assertNotContains(response, "Expired Role")
        self.assertNotContains(response, "Inactive Role")

    def test_search_and_filter_active_vacancies(self):
        response = self.client.get(reverse("jobs:job_list"), {"search": "Python"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Developer")

        response = self.client.get(reverse("jobs:job_list"), {"location": "NonexistentCity"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No open roles found")

    def test_category_list_only_contains_categories_with_active_jobs(self):
        response = self.client.get(reverse("jobs:job_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.category.name)
        self.assertNotContains(response, self.empty_category.name)
        self.assertIn(self.category, response.context["categories"])
        self.assertNotIn(self.empty_category, response.context["categories"])

    def test_selecting_all_categories_displays_all_posted_jobs(self):
        response = self.client.get(reverse("jobs:job_list"), {"category": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.job.title)
        self.assertNotContains(response, self.empty_category.name)

        response_all = self.client.get(reverse("jobs:job_list"), {"category": "all"})
        self.assertEqual(response_all.status_code, 200)
        self.assertContains(response_all, self.job.title)

    def test_category_with_inactive_or_expired_jobs_is_not_displayed(self):
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.now().date()

        inactive_cat = JobCategory.objects.create(name="Archived Category")
        Job.objects.create(
            title="Old Job",
            company=self.company,
            category=inactive_cat,
            location="Remote",
            skills="Legacy",
            description="Inactive job.",
            vacancies=1,
            is_active=False,
        )
        expired_cat = JobCategory.objects.create(name="Expired Category")
        Job.objects.create(
            title="Expired Job",
            company=self.company,
            category=expired_cat,
            location="Remote",
            skills="Legacy",
            description="Expired job.",
            vacancies=1,
            is_active=True,
            application_deadline=today - timedelta(days=5),
        )

        response = self.client.get(reverse("jobs:job_list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(inactive_cat, response.context["categories"])
        self.assertNotIn(expired_cat, response.context["categories"])
        self.assertNotContains(response, "Archived Category")
        self.assertNotContains(response, "Expired Category")

    def test_filtering_by_category_displays_only_matching_active_jobs(self):
        other_cat = JobCategory.objects.create(name="Cloud Computing")
        other_job = Job.objects.create(
            title="Cloud Engineer",
            company=self.company,
            category=other_cat,
            location="Remote",
            skills="AWS",
            description="Cloud role.",
            vacancies=1,
            is_active=True,
        )

        # Filter by self.category
        response = self.client.get(reverse("jobs:job_list"), {"category": str(self.category.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.job.title)
        self.assertNotContains(response, other_job.title)

        # Filter by other_cat
        response_other = self.client.get(reverse("jobs:job_list"), {"category": str(other_cat.pk)})
        self.assertEqual(response_other.status_code, 200)
        self.assertContains(response_other, other_job.title)
        self.assertNotContains(response_other, self.job.title)

        # Select "All categories" -> displays both posted jobs
        response_all = self.client.get(reverse("jobs:job_list"), {"category": ""})
        self.assertEqual(response_all.status_code, 200)
        self.assertContains(response_all, self.job.title)
        self.assertContains(response_all, other_job.title)



    def test_recruiter_add_actions_are_hidden_from_job_seekers(self):
        self.client.force_login(self.job_seeker)

        jobs_response = self.client.get(reverse("jobs:job_list"))
        companies_response = self.client.get(reverse("companies:company_list"))

        self.assertNotContains(jobs_response, "Add job")
        self.assertNotContains(jobs_response, "Add Jobs")
        self.assertNotContains(companies_response, "Add company")

    def test_recruiters_see_add_job_action_on_jobs_page(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("jobs:job_list"))

        self.assertContains(response, "Add Job")
        self.assertContains(response, 'data-open-dialog="addJobDialog"')
        self.assertNotContains(response, "Add Company")

    def test_recruiter_add_job_form_is_inline_on_jobs_page(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("jobs:job_list"))

        self.assertContains(response, 'id="addJobDialog"')
        self.assertContains(response, 'name="form_action" value="add_job"')
        self.assertContains(response, 'data-open-dialog="addJobDialog"')

    def test_recruiter_can_add_job_from_jobs_page(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("jobs:job_list"),
            {
                "form_action": "add_job",
                "title": "Inline Product Engineer",
                "company": self.company.pk,
                "location": "Remote",
                "work_mode": "remote",
                "job_type": "full-time",
                "experience_level": "mid",
                "skills": "Python, Django",
                "description": "Build product features.",
                "vacancies": 1,
            },
        )

        self.assertRedirects(response, reverse("jobs:job_list"))
        self.assertTrue(Job.objects.filter(title="Inline Product Engineer").exists())

    def test_invalid_inline_job_form_reopens_on_jobs_page(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("jobs:job_list"),
            {
                "form_action": "add_job",
                "title": "Invalid Salary Role",
                "company": self.company.pk,
                "location": "Remote",
                "work_mode": "remote",
                "job_type": "full-time",
                "experience_level": "mid",
                "salary_min": "100000",
                "salary_max": "50000",
                "skills": "Python",
                "description": "A role with an invalid salary range.",
                "vacancies": 1,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["show_job_form"])
        self.assertContains(response, "Maximum salary must be at least the minimum salary.")
        self.assertFalse(Job.objects.filter(title="Invalid Salary Role").exists())

    def test_recruiters_cannot_apply_to_jobs(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("apply", kwargs={"job_id": self.job.pk})
        )

        self.assertRedirects(
            response,
            reverse("jobs:job_detail", kwargs={"pk": self.job.pk})
        )

    def test_job_seekers_cannot_open_legacy_job_management_pages(self):
        self.client.force_login(self.job_seeker)

        for route_name in ("manage_jobs", "post_job"):
            response = self.client.get(reverse(route_name), follow=True)

            self.assertRedirects(response, reverse("jobs:job_list"))

    def test_add_job_requires_login(self):
        self.client.logout()
        response = self.client.get(
            reverse("jobs:add_job")
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_add_job_form_loads_for_signed_in_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("jobs:add_job"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Publish job")

    def test_add_job_posts_and_redirects_to_job_board(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("jobs:add_job"),
            {
                "title": "Frontend Developer",
                "company": self.company.pk,
                "location": "Chennai",
                "work_mode": "remote",
                "job_type": "full-time",
                "experience_level": "mid",
                "skills": "JavaScript, CSS",
                "description": "Build accessible web experiences.",
                "vacancies": 1,
            }
        )

        self.assertRedirects(response, reverse("jobs:job_list"))
        self.assertTrue(
            Job.objects.filter(title="Frontend Developer").exists()
        )

    def test_add_job_rejects_invalid_salary_range(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("jobs:add_job"),
            {
                "title": "Frontend Developer",
                "company": self.company.pk,
                "location": "Chennai",
                "work_mode": "remote",
                "job_type": "full-time",
                "experience_level": "mid",
                "salary_min": "100000",
                "salary_max": "50000",
                "skills": "JavaScript, CSS",
                "description": "Build accessible web experiences.",
                "vacancies": 1,
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("salary_max", response.context["form"].errors)

    def test_add_job_rejects_negative_salary(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("jobs:add_job"),
            {
                "title": "Frontend Developer",
                "company": self.company.pk,
                "location": "Chennai",
                "work_mode": "remote",
                "job_type": "full-time",
                "experience_level": "mid",
                "salary_min": "-1",
                "skills": "JavaScript, CSS",
                "description": "Build accessible web experiences.",
                "vacancies": 1,
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("salary_min", response.context["form"].errors)

    def test_job_seekers_cannot_post_jobs(self):
        self.client.force_login(self.user)
        Profile.objects.filter(user=self.user).update(account_type="job_seeker")

        response = self.client.get(reverse("jobs:add_job"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Job.objects.filter(title="Frontend Developer").exists())

    def test_edit_job_requires_login(self):
        self.client.logout()
        response = self.client.get(
            reverse(
                "jobs:edit_job",
                kwargs={
                    "pk": self.job.pk
                }
            )
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_delete_job_requires_login(self):
        self.client.logout()
        response = self.client.get(
            reverse(
                "jobs:delete_job",
                kwargs={
                    "pk": self.job.pk
                }
            )
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_unverified_company_cannot_post_jobs(self):
        self.client.force_login(self.user)
        unverified_company = Company.objects.create(
            name="Unverified Corp",
            industry="IT",
            location="Remote",
            verification_status="unverified",
        )

        response = self.client.post(
            reverse("jobs:add_job"),
            {
                "title": "Unverified Role",
                "company": unverified_company.pk,
                "location": "Remote",
                "work_mode": "remote",
                "job_type": "full-time",
                "experience_level": "entry",
                "skills": "Python",
                "description": "Role description.",
                "vacancies": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("company", response.context["form"].errors)
        self.assertFalse(Job.objects.filter(title="Unverified Role").exists())

    def test_suspended_and_rejected_companies_cannot_post_jobs(self):
        self.client.force_login(self.user)
        for status in ("suspended", "rejected"):
            comp = Company.objects.create(
                name=f"{status.capitalize()} Corp",
                industry="IT",
                location="Remote",
                verification_status=status,
            )
            response = self.client.post(
                reverse("jobs:add_job"),
                {
                    "title": f"{status.capitalize()} Role",
                    "company": comp.pk,
                    "location": "Remote",
                    "work_mode": "remote",
                    "job_type": "full-time",
                    "experience_level": "entry",
                    "skills": "Python",
                    "description": "Role description.",
                    "vacancies": 1,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("company", response.context["form"].errors)
            self.assertFalse(Job.objects.filter(title=f"{status.capitalize()} Role").exists())

    def test_job_form_only_includes_verified_companies_in_dropdown(self):
        self.client.force_login(self.user)
        unverified = Company.objects.create(name="Pending LLC", industry="Tech", location="NYC", verification_status="unverified")
        response = self.client.get(reverse("jobs:add_job"))
        self.assertEqual(response.status_code, 200)
        form_companies = list(response.context["form"].fields["company"].queryset)
        self.assertIn(self.company, form_companies)
        self.assertNotIn(unverified, form_companies)

    def test_job_list_only_shows_jobs_from_verified_companies(self):
        unverified_comp = Company.objects.create(
            name="Ghost Corp",
            industry="IT",
            location="Remote",
            verification_status="unverified",
        )
        unverified_job = Job.objects.create(
            title="Ghost Developer",
            company=unverified_comp,
            location="Remote",
            skills="Python",
            description="Hidden job.",
            vacancies=1,
            is_active=True,
        )
        response = self.client.get(reverse("jobs:job_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.job.title)
        self.assertNotContains(response, "Ghost Developer")

    def test_admin_verifying_company_allows_job_posting_immediately(self):
        self.client.force_login(self.user)
        new_comp = Company.objects.create(
            name="New Startup",
            industry="AI",
            location="Bengaluru",
            verification_status="unverified",
        )

        # Before verification: cannot post job
        fail_response = self.client.post(
            reverse("jobs:add_job"),
            {
                "title": "AI Researcher",
                "company": new_comp.pk,
                "location": "Bengaluru",
                "work_mode": "remote",
                "job_type": "full-time",
                "experience_level": "senior",
                "skills": "PyTorch",
                "description": "AI research role.",
                "vacancies": 1,
            },
        )
        self.assertEqual(fail_response.status_code, 200)
        self.assertFalse(Job.objects.filter(title="AI Researcher").exists())

        # Admin verifies the company
        new_comp.verification_status = "verified"
        new_comp.save()

        # Immediately after verification: job posting succeeds
        success_response = self.client.post(
            reverse("jobs:add_job"),
            {
                "title": "AI Researcher",
                "company": new_comp.pk,
                "location": "Bengaluru",
                "work_mode": "remote",
                "job_type": "full-time",
                "experience_level": "senior",
                "skills": "PyTorch",
                "description": "AI research role.",
                "vacancies": 1,
            },
            follow=True,
        )
        self.assertEqual(success_response.status_code, 200)
        self.assertTrue(Job.objects.filter(title="AI Researcher", company=new_comp).exists())


class JobSearchAndFilterDatabaseTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="searchfilteruser", password="password123")
        self.client.force_login(self.user)
        self.comp_a = Company.objects.create(
            name="Stripe India",
            industry="Fintech",
            location="Bengaluru, Karnataka",
            verification_status="verified",
        )
        self.comp_b = Company.objects.create(
            name="Razorpay",
            industry="Fintech",
            location="Mumbai, Maharashtra",
            verification_status="verified",
        )
        self.unverified_comp = Company.objects.create(
            name="Unverified Tech",
            industry="Software",
            location="Delhi",
            verification_status="unverified",
        )

        self.cat_eng = JobCategory.objects.create(name="Engineering")
        self.cat_data = JobCategory.objects.create(name="Data Science")
        self.cat_empty = JobCategory.objects.create(name="Human Resources")

        today = timezone.now().date()
        self.job1 = Job.objects.create(
            title="Senior Python Backend Engineer",
            company=self.comp_a,
            category=self.cat_eng,
            location="Bengaluru, Karnataka",
            work_mode="remote",
            job_type="full-time",
            experience_level="senior",
            skills="Python, Django, PostgreSQL, Docker",
            description="Build scalable payment infrastructure.",
            vacancies=3,
            is_active=True,
            application_deadline=today + timedelta(days=15),
        )

        self.job2 = Job.objects.create(
            title="Data Scientist",
            company=self.comp_b,
            category=self.cat_data,
            location="Mumbai, Maharashtra",
            work_mode="hybrid",
            job_type="full-time",
            experience_level="mid",
            skills="Python, Machine Learning, PyTorch, Pandas",
            description="Develop fraud detection ML pipelines.",
            vacancies=2,
            is_active=True,
            application_deadline=today + timedelta(days=20),
        )

        # Unverified company job - should NEVER appear
        self.unverified_job = Job.objects.create(
            title="Frontend React Developer",
            company=self.unverified_comp,
            category=self.cat_eng,
            location="Delhi",
            skills="React, JavaScript",
            description="Build web applications.",
            vacancies=1,
            is_active=True,
            application_deadline=today + timedelta(days=10),
        )

    def test_search_by_role(self):
        response = self.client.get(reverse("jobs:job_list"), {"role": "Backend"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Python Backend Engineer")
        self.assertNotContains(response, "Data Scientist")
        self.assertNotContains(response, "Frontend React Developer")

    def test_search_by_company(self):
        response = self.client.get(reverse("jobs:job_list"), {"company": "Stripe"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Python Backend Engineer")
        self.assertNotContains(response, "Razorpay")

    def test_search_by_skill(self):
        response = self.client.get(reverse("jobs:job_list"), {"skill": "PostgreSQL"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Python Backend Engineer")
        self.assertNotContains(response, "Data Scientist")

    def test_search_by_city_or_region(self):
        response = self.client.get(reverse("jobs:job_list"), {"city": "Bengaluru"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Python Backend Engineer")
        self.assertNotContains(response, "Data Scientist")

        # via location param
        response_loc = self.client.get(reverse("jobs:job_list"), {"location": "Mumbai"})
        self.assertEqual(response_loc.status_code, 200)
        self.assertContains(response_loc, "Data Scientist")
        self.assertNotContains(response_loc, "Senior Python Backend Engineer")

    def test_search_unified_role_company_skill(self):
        response = self.client.get(reverse("jobs:job_list"), {"search": "Docker"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Python Backend Engineer")
        self.assertNotContains(response, "Data Scientist")

    def test_filter_by_all_categories_and_specific_category(self):
        # By ID
        response_eng = self.client.get(reverse("jobs:job_list"), {"category": self.cat_eng.pk})
        self.assertEqual(response_eng.status_code, 200)
        self.assertContains(response_eng, "Senior Python Backend Engineer")
        self.assertNotContains(response_eng, "Data Scientist")

        # By Name
        response_data = self.client.get(reverse("jobs:job_list"), {"category": "Data Science"})
        self.assertEqual(response_data.status_code, 200)
        self.assertContains(response_data, "Data Scientist")
        self.assertNotContains(response_data, "Senior Python Backend Engineer")

        # All categories
        response_all = self.client.get(reverse("jobs:job_list"), {"category": "all"})
        self.assertEqual(response_all.status_code, 200)
        self.assertContains(response_all, "Senior Python Backend Engineer")
        self.assertContains(response_all, "Data Scientist")
        # Empty category is not in dropdown
        self.assertNotContains(response_all, "Human Resources")

    def test_no_results_found_message(self):
        response = self.client.get(reverse("jobs:job_list"), {"search": "NonexistentSkillxyz"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No results found")
        self.assertContains(response, "No open roles found matching your search or filter criteria")
        self.assertNotContains(response, "Senior Python Backend Engineer")
        self.assertNotContains(response, "Data Scientist")

    def test_only_active_jobs_from_verified_companies_are_returned(self):
        response = self.client.get(reverse("jobs:job_list"), {"search": "React"})
        self.assertEqual(response.status_code, 200)
        # unverified_job had React, but its company is unverified, so 0 results found
        self.assertContains(response, "No results found")
        self.assertNotContains(response, "Frontend React Developer")


class HomePageJobSearchTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="homeuser", password="password123")
        self.client.force_login(self.user)
        self.company = Company.objects.create(
            name="Apex Innovations",
            industry="Software & AI",
            location="Bengaluru, Karnataka",
            verification_status="verified",
        )
        self.unverified_company = Company.objects.create(
            name="Shadow Corp",
            industry="Tech",
            location="Chennai",
            verification_status="unverified",
        )

        today = timezone.now().date()
        self.job_python = Job.objects.create(
            title="Senior Python Developer",
            company=self.company,
            location="Bengaluru, Karnataka",
            work_mode="remote",
            job_type="full-time",
            experience_level="senior",
            skills="Python, Django, PostgreSQL, Celery",
            description="Build scalable backend services.",
            vacancies=2,
            is_active=True,
            application_deadline=today + timedelta(days=20),
        )

        self.job_react = Job.objects.create(
            title="Frontend React Developer",
            company=self.company,
            location="Chennai, Tamil Nadu",
            work_mode="hybrid",
            job_type="full-time",
            experience_level="mid",
            skills="React, TypeScript, Next.js, Redux",
            description="Design intuitive user interfaces.",
            vacancies=1,
            is_active=True,
            application_deadline=today + timedelta(days=25),
        )

        self.job_devops = Job.objects.create(
            title="DevOps Engineer",
            company=self.company,
            location="Hyderabad, Telangana",
            work_mode="onsite",
            job_type="full-time",
            experience_level="mid",
            skills="AWS, Kubernetes, Docker, Terraform",
            description="Manage cloud infrastructure and CI/CD pipelines.",
            vacancies=1,
            is_active=True,
            application_deadline=today + timedelta(days=30),
        )

        # Unverified company job with matching title/skill - must NOT appear
        self.job_unverified = Job.objects.create(
            title="Python Intern",
            company=self.unverified_company,
            location="Bengaluru, Karnataka",
            skills="Python, Django",
            description="Internship role.",
            vacancies=1,
            is_active=True,
            application_deadline=today + timedelta(days=15),
        )

    def test_home_page_default_displays_active_jobs(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Python Developer")
        self.assertContains(response, "Frontend React Developer")
        self.assertContains(response, "DevOps Engineer")
        self.assertNotContains(response, "Python Intern")

    def test_home_search_by_job_title_shows_only_matching_jobs(self):
        response = self.client.get(reverse("home"), {"q": "Python Developer"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Python Developer")
        # Unrelated jobs must NOT be displayed
        self.assertNotContains(response, "Frontend React Developer")
        self.assertNotContains(response, "DevOps Engineer")
        self.assertNotContains(response, "Python Intern")

    def test_home_search_by_skill_keyword_shows_only_matching_jobs(self):
        # Skill: Django
        response_django = self.client.get(reverse("home"), {"q": "Django"})
        self.assertEqual(response_django.status_code, 200)
        self.assertContains(response_django, "Senior Python Developer")
        self.assertNotContains(response_django, "Frontend React Developer")
        self.assertNotContains(response_django, "DevOps Engineer")

        # Skill: React
        response_react = self.client.get(reverse("home"), {"q": "React"})
        self.assertEqual(response_react.status_code, 200)
        self.assertContains(response_react, "Frontend React Developer")
        self.assertNotContains(response_react, "Senior Python Developer")
        self.assertNotContains(response_react, "DevOps Engineer")

        # Skill: Kubernetes
        response_k8s = self.client.get(reverse("home"), {"q": "Kubernetes"})
        self.assertEqual(response_k8s.status_code, 200)
        self.assertContains(response_k8s, "DevOps Engineer")
        self.assertNotContains(response_k8s, "Senior Python Developer")
        self.assertNotContains(response_k8s, "Frontend React Developer")

    def test_home_search_unrelated_jobs_not_displayed(self):
        # Searching for an unavailable job/skill like "Data Scientist" or "Rust"
        response = self.client.get(reverse("home"), {"q": "Rust Embedded Engineer"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No results found")
        self.assertContains(response, "No jobs found matching your search criteria")
        self.assertNotContains(response, "Senior Python Developer")
        self.assertNotContains(response, "Frontend React Developer")
        self.assertNotContains(response, "DevOps Engineer")

    def test_home_search_by_location(self):
        response = self.client.get(reverse("home"), {"q": "Python", "location": "Bengaluru"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Python Developer")
        self.assertNotContains(response, "Frontend React Developer")

        # Location mismatch
        response_mismatch = self.client.get(reverse("home"), {"q": "Python", "location": "Chennai"})
        self.assertEqual(response_mismatch.status_code, 200)
        self.assertContains(response_mismatch, "No results found")
        self.assertNotContains(response_mismatch, "Senior Python Developer")

    def test_unauthenticated_user_can_view_home_normally(self):
        self.client.logout()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find a job where")
        self.assertContains(response, "Senior Python Developer")

    def test_first_time_visitor_to_root_url_sees_home_page(self):
        self.client.logout()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "JobNest")
        self.assertContains(response, "Find a job where")

    def test_edit_job_by_owner_updates_successfully(self):
        Profile.objects.get_or_create(user=self.user, defaults={"account_type": "recruiter"})
        self.client.force_login(self.user)
        job = Job.objects.create(
            title="Original Title",
            recruiter=self.user,
            company=self.company,
            location="Bengaluru",
            work_mode="remote",
            job_type="full-time",
            experience_level="mid",
            skills="Python",
            description="Original description",
            vacancies=1,
            is_active=True,
        )

        response = self.client.post(
            reverse("jobs:edit_job", kwargs={"pk": job.pk}),
            {
                "title": "Updated Title",
                "company": self.company.pk,
                "location": "Bengaluru",
                "work_mode": "remote",
                "job_type": "full-time",
                "experience_level": "senior",
                "skills": "Python, Django",
                "description": "Updated description",
                "vacancies": 2,
            },
        )
        self.assertRedirects(response, reverse("jobs:job_detail", kwargs={"pk": job.pk}))
        job.refresh_from_db()
        self.assertEqual(job.title, "Updated Title")
        self.assertEqual(job.experience_level, "senior")

    def test_edit_job_by_different_user_returns_forbidden(self):
        other_user = User.objects.create_user(username="other_recruiter", password="password")
        Profile.objects.create(user=other_user, account_type="recruiter")
        job = Job.objects.create(
            title="Protected Job",
            recruiter=self.user,
            company=self.company,
            location="Bengaluru",
            skills="Python",
            description="Role details",
            vacancies=1,
        )

        self.client.force_login(other_user)
        response = self.client.get(reverse("jobs:edit_job", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 403)

    def test_delete_job_by_owner_renders_confirmation_and_deletes(self):
        Profile.objects.get_or_create(user=self.user, defaults={"account_type": "recruiter"})
        self.client.force_login(self.user)
        job = Job.objects.create(
            title="Job To Delete",
            recruiter=self.user,
            company=self.company,
            location="Bengaluru",
            skills="Python",
            description="Role details",
            vacancies=1,
        )

        # GET confirmation
        get_response = self.client.get(reverse("jobs:delete_job", kwargs={"pk": job.pk}))
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, "Delete Job Posting?")
        self.assertContains(get_response, "Job To Delete")

        # POST delete
        post_response = self.client.post(reverse("jobs:delete_job", kwargs={"pk": job.pk}))
        self.assertRedirects(post_response, reverse("manage_jobs"))
        self.assertFalse(Job.objects.filter(pk=job.pk).exists())

    def test_delete_job_by_different_user_returns_forbidden(self):
        other_user = User.objects.create_user(username="unauthorized_deleter", password="password")
        Profile.objects.create(user=other_user, account_type="recruiter")
        job = Job.objects.create(
            title="Not Your Job",
            recruiter=self.user,
            company=self.company,
            location="Bengaluru",
            skills="Python",
            description="Role details",
            vacancies=1,
        )

        self.client.force_login(other_user)
        response = self.client.post(reverse("jobs:delete_job", kwargs={"pk": job.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Job.objects.filter(pk=job.pk).exists())


