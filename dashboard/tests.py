from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse


class DashboardTest(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123"
        )

    def test_dashboard_requires_login(self):

        response = self.client.get(
            reverse("dashboard:dashboard_home")
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_dashboard_logged_in(self):

        self.client.login(
            username="testuser",
            password="testpassword123"
        )

        response = self.client.get(
            reverse("dashboard:dashboard_home")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertTemplateUsed(
            response,
            "dashboard/dashboard.html"
        )
        self.assertContains(response, "Welcome back, testuser")
        self.assertContains(response, "JOB SEEKER")
        self.assertContains(response, "Total Applications")

    def test_dashboard_shows_only_active_jobs_in_latest(self):
        from companies.models import Company
        from jobs.models import Job

        comp = Company.objects.create(name="Verified Corp", verification_status="verified")
        unverified_comp = Company.objects.create(name="Unverified Corp", verification_status="unverified")

        active_job = Job.objects.create(
            title="Active Backend Engineer",
            company=comp,
            location="Remote",
            skills="Python",
            description="Role details",
            is_active=True,
        )
        inactive_job = Job.objects.create(
            title="Inactive Role",
            company=comp,
            location="Remote",
            skills="Python",
            description="Role details",
            is_active=False,
        )
        unverified_job = Job.objects.create(
            title="Ghost Job",
            company=unverified_comp,
            location="Remote",
            skills="Python",
            description="Role details",
            is_active=True,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:dashboard_home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(active_job, response.context["latest_jobs"])
        self.assertNotIn(inactive_job, response.context["latest_jobs"])
        self.assertNotIn(unverified_job, response.context["latest_jobs"])
