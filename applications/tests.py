import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from adm.models import Profile
from companies.models import Company
from jobs.models import Job
from resumes.models import Resume
from .models import Application


class ApplyJobViewTest(TestCase):

	@classmethod
	def setUpClass(cls):
		cls.temp_media = tempfile.mkdtemp()
		cls._media_override = override_settings(MEDIA_ROOT=cls.temp_media)
		cls._media_override.enable()
		super().setUpClass()

	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		cls._media_override.disable()
		shutil.rmtree(cls.temp_media, ignore_errors=True)

	def setUp(self):
		self.user = User.objects.create_user(
			username="applicant",
			password="test-password",
		)
		Profile.objects.create(user=self.user, account_type="job_seeker")
		self.company = Company.objects.create(
			name="Northstar Labs",
			industry="Technology",
			location="Chennai",
			verification_status="verified",
		)
		self.job = Job.objects.create(
			title="Python Developer",
			company=self.company,
			location="Chennai",
			skills="Python, Django",
			description="Build web applications.",
		)
		self.resume = Resume.objects.create(
			user=self.user,
			resume_file=SimpleUploadedFile(
				"resume.pdf",
				b"Test resume",
				content_type="application/pdf",
			),
		)
		self.client.force_login(self.user)

	def test_successful_application_confirms_and_changes_button_to_applied(self):
		detail_url = reverse("jobs:job_detail", kwargs={"pk": self.job.pk})
		response = self.client.post(
			reverse("apply", kwargs={"job_id": self.job.pk}),
			{"resume": self.resume.pk},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.redirect_chain[-1][0], detail_url)
		self.assertTrue(
			Application.objects.filter(applicant=self.user, job=self.job).exists()
		)
		self.assertContains(response, "Application Submitted Successfully!")
		self.assertContains(
			response,
			"Your application has been successfully submitted for this position.",
		)
		self.assertContains(response, "fa-circle-check")
		self.assertContains(response, "Applied")
		self.assertNotContains(response, "Apply Now")

		revisited_detail = self.client.get(detail_url)
		self.assertContains(revisited_detail, "Applied")
		self.assertNotContains(revisited_detail, "Apply Now")

	def test_can_upload_resume_and_apply_from_application_form(self):
		response = self.client.post(
			reverse("apply", kwargs={"job_id": self.job.pk}),
			{
				"resume_file": SimpleUploadedFile(
					"new-resume.docx",
					b"Test DOCX content",
					content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
				),
				"cover_letter": "I am interested in this role.",
			},
			follow=True,
		)

		application = Application.objects.get(applicant=self.user, job=self.job)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(application.resume.file_extension(), "docx")
		self.assertEqual(application.cover_letter, "I am interested in this role.")
		self.assertContains(response, "Application Submitted Successfully!")
		self.assertContains(response, "Applied")

	def test_application_form_rejects_unsupported_resume_file(self):
		response = self.client.post(
			reverse("apply", kwargs={"job_id": self.job.pk}),
			{
				"resume_file": SimpleUploadedFile(
					"resume.txt",
					b"Not a supported resume",
					content_type="text/plain",
				),
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Only PDF, DOC, or DOCX files are allowed.")
		self.assertFalse(Application.objects.filter(applicant=self.user, job=self.job).exists())

	def test_apply_page_renders_remove_resume_button(self):
		response = self.client.get(reverse("apply", kwargs={"job_id": self.job.pk}))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'id="applyRemoveFileBtn"')
		self.assertContains(response, "fa-trash-can")
		self.assertContains(response, 'id="applyResumeFilename"')

	def test_application_rejected_when_deadline_passed(self):
		from datetime import timedelta
		from django.utils import timezone
		self.job.application_deadline = timezone.now().date() - timedelta(days=1)
		self.job.save()

		detail_url = reverse("jobs:job_detail", kwargs={"pk": self.job.pk})
		response = self.client.post(
			reverse("apply", kwargs={"job_id": self.job.pk}),
			{"resume": self.resume.pk},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.redirect_chain[-1][0], detail_url)
		self.assertFalse(
			Application.objects.filter(applicant=self.user, job=self.job).exists()
		)
		self.assertContains(response, "The application deadline for this job")
		self.assertContains(response, "has passed")

	def test_cannot_open_apply_page_when_deadline_passed(self):
		from datetime import timedelta
		from django.utils import timezone
		self.job.application_deadline = timezone.now().date() - timedelta(days=2)
		self.job.save()

		detail_url = reverse("jobs:job_detail", kwargs={"pk": self.job.pk})
		response = self.client.get(
			reverse("apply", kwargs={"job_id": self.job.pk}),
			follow=True,
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.redirect_chain[-1][0], detail_url)
		self.assertContains(response, "The application deadline for this job")

	def test_cannot_apply_to_inactive_job(self):
		self.job.is_active = False
		self.job.save()

		detail_url = reverse("jobs:job_detail", kwargs={"pk": self.job.pk})
		response = self.client.post(
			reverse("apply", kwargs={"job_id": self.job.pk}),
			{"resume": self.resume.pk},
			follow=True,
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.redirect_chain[-1][0], detail_url)
		self.assertFalse(Application.objects.filter(applicant=self.user, job=self.job).exists())
		self.assertContains(response, "This job is inactive and is no longer accepting applications.")

	def test_application_history_displays_submitted_application(self):
		self.client.post(
			reverse("apply", kwargs={"job_id": self.job.pk}),
			{"resume": self.resume.pk},
			follow=True,
		)
		self.assertTrue(Application.objects.filter(applicant=self.user, job=self.job).exists())

		history_response = self.client.get(reverse("my_applications"))
		self.assertEqual(history_response.status_code, 200)
		self.assertContains(history_response, self.job.title)
		self.assertContains(history_response, self.company.name)
		self.assertContains(history_response, "Applied")

	def test_cannot_apply_to_job_with_unverified_company(self):
		self.client.force_login(self.user)
		self.company.verification_status = "unverified"
		self.company.save()

		get_response = self.client.get(reverse("apply", kwargs={"job_id": self.job.pk}))
		self.assertRedirects(get_response, reverse("jobs:job_detail", kwargs={"pk": self.job.pk}))

		post_response = self.client.post(
			reverse("apply", kwargs={"job_id": self.job.pk}),
			{"resume": self.resume.pk},
		)
		self.assertRedirects(post_response, reverse("jobs:job_detail", kwargs={"pk": self.job.pk}))
		self.assertFalse(Application.objects.filter(job=self.job).exists())

	def test_cannot_apply_to_job_with_suspended_or_rejected_company(self):
		self.client.force_login(self.user)
		for status in ("suspended", "rejected"):
			self.company.verification_status = status
			self.company.save()

			response = self.client.get(reverse("apply", kwargs={"job_id": self.job.pk}))
			self.assertRedirects(response, reverse("jobs:job_detail", kwargs={"pk": self.job.pk}))



class ApplicationAuthorizationAndManagementTest(TestCase):


	@classmethod
	def setUpClass(cls):
		cls.temp_media = tempfile.mkdtemp()
		cls._media_override = override_settings(MEDIA_ROOT=cls.temp_media)
		cls._media_override.enable()
		super().setUpClass()

	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		cls._media_override.disable()
		shutil.rmtree(cls.temp_media, ignore_errors=True)

	def setUp(self):
		self.recruiter1 = User.objects.create_user(username="recruiter1", password="password")
		Profile.objects.create(user=self.recruiter1, account_type="recruiter")

		self.recruiter2 = User.objects.create_user(username="recruiter2", password="password")
		Profile.objects.create(user=self.recruiter2, account_type="recruiter")

		self.seeker1 = User.objects.create_user(username="seeker1", password="password")
		Profile.objects.create(user=self.seeker1, account_type="job_seeker")

		self.seeker2 = User.objects.create_user(username="seeker2", password="password")
		Profile.objects.create(user=self.seeker2, account_type="job_seeker")

		self.company = Company.objects.create(name="TechCorp", industry="Tech", location="Remote", verification_status="verified")

		self.job1 = Job.objects.create(
			title="Backend Dev",
			company=self.company,
			recruiter=self.recruiter1,
			location="Remote",
			skills="Python",
			description="Desc",
		)
		self.job2 = Job.objects.create(
			title="Frontend Dev",
			company=self.company,
			recruiter=self.recruiter2,
			location="Remote",
			skills="JS",
			description="Desc",
		)

		self.resume1 = Resume.objects.create(
			user=self.seeker1,
			resume_file=SimpleUploadedFile("s1.pdf", b"pdf", content_type="application/pdf"),
		)
		self.resume2 = Resume.objects.create(
			user=self.seeker2,
			resume_file=SimpleUploadedFile("s2.pdf", b"pdf", content_type="application/pdf"),
		)

		self.app1 = Application.objects.create(applicant=self.seeker1, job=self.job1, resume=self.resume1)
		self.app2 = Application.objects.create(applicant=self.seeker2, job=self.job2, resume=self.resume2)

	def test_seeker_can_view_own_application(self):
		self.client.force_login(self.seeker1)
		response = self.client.get(reverse("application_details", kwargs={"pk": self.app1.pk}))
		self.assertEqual(response.status_code, 200)

	def test_seeker_cannot_view_other_application(self):
		self.client.force_login(self.seeker2)
		response = self.client.get(reverse("application_details", kwargs={"pk": self.app1.pk}))
		self.assertEqual(response.status_code, 403)

	def test_recruiter_can_view_application_for_own_job(self):
		self.client.force_login(self.recruiter1)
		response = self.client.get(reverse("application_details", kwargs={"pk": self.app1.pk}))
		self.assertEqual(response.status_code, 200)

	def test_recruiter_cannot_view_application_for_other_recruiter_job(self):
		self.client.force_login(self.recruiter2)
		response = self.client.get(reverse("application_details", kwargs={"pk": self.app1.pk}))
		self.assertEqual(response.status_code, 403)

	def test_manage_applicants_redirects_to_recruiter_dashboard_pipeline(self):
		self.client.force_login(self.recruiter1)
		response = self.client.get(reverse("manage_applicants"))
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse("recruiter_dashboard"), response.url)

	def test_recruiter_dashboard_manages_complete_pipeline_and_shows_only_own_jobs(self):
		self.client.force_login(self.recruiter1)
		response = self.client.get(reverse("recruiter_dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertIn(self.app1, response.context["pipeline_applications"])
		self.assertNotIn(self.app2, response.context["pipeline_applications"])
		self.assertIn(self.app1, response.context["pending_applications_list"])
		self.assertNotIn(self.app2, response.context["pending_applications_list"])
		self.assertContains(response, "Pending Applications")
		self.assertContains(response, "Candidate Pipeline &amp; Review Candidates")
		self.assertContains(response, "Resume")

	def test_recruiter_cannot_access_my_applications_and_redirects_to_dashboard(self):
		self.client.force_login(self.recruiter1)
		response = self.client.get(reverse("my_applications"))
		self.assertRedirects(response, reverse("recruiter_dashboard"))

	def test_seeker_can_access_my_applications_normally(self):
		self.client.force_login(self.seeker1)
		response = self.client.get(reverse("my_applications"))
		self.assertEqual(response.status_code, 200)

	def test_update_application_status_requires_post(self):
		self.client.force_login(self.recruiter1)
		response = self.client.get(reverse("update_application_status", kwargs={"pk": self.app1.pk}))
		self.assertEqual(response.status_code, 405)

	def test_recruiter_can_update_status_for_own_job(self):
		self.client.force_login(self.recruiter1)
		response = self.client.post(
			reverse("update_application_status", kwargs={"pk": self.app1.pk}),
			{"status": "under_review"},
		)
		self.assertEqual(response.status_code, 302)
		self.app1.refresh_from_db()
		self.assertEqual(self.app1.status, "under_review")

	def test_recruiter_cannot_update_status_for_other_recruiter_job(self):
		self.client.force_login(self.recruiter2)
		response = self.client.post(
			reverse("update_application_status", kwargs={"pk": self.app1.pk}),
			{"status": "under_review"},
		)
		self.assertEqual(response.status_code, 403)

	def test_recruiter_dashboard_requires_login(self):
		response = self.client.get(reverse("recruiter_dashboard"))
		self.assertEqual(response.status_code, 302)

	def test_recruiter_dashboard_context_and_stats(self):
		self.client.force_login(self.recruiter1)
		response = self.client.get(reverse("recruiter_dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context["total_jobs"], 1)
		self.assertEqual(response.context["total_applications"], 1)
		self.assertEqual(response.context["pending_applications"], 1)
		self.assertIn(self.app1, response.context["recent_applications"])
		self.assertNotIn(self.app2, response.context["recent_applications"])
		self.assertContains(response, "Total Jobs")
		self.assertContains(response, "Active Jobs")
		self.assertContains(response, "Total Applications")
		self.assertContains(response, "Pending Applications")
		self.assertContains(response, "Recruiter Navigation")

	def test_recruiter_dashboard_redirects_job_seeker(self):
		self.client.force_login(self.seeker1)
		response = self.client.get(reverse("recruiter_dashboard"))
		self.assertRedirects(response, reverse("dashboard:dashboard_home"))

	def test_manage_jobs_view_shows_only_recruiter_jobs(self):
		self.client.force_login(self.recruiter1)
		response = self.client.get(reverse("manage_jobs"))
		self.assertEqual(response.status_code, 200)
		self.assertIn(self.job1, response.context["jobs"])
		self.assertNotIn(self.job2, response.context["jobs"])

	def test_manage_jobs_view_blocks_job_seeker(self):
		self.client.force_login(self.seeker1)
		response = self.client.get(reverse("manage_jobs"))
		self.assertRedirects(response, reverse("jobs:job_list"))

	def test_post_job_redirects_recruiter(self):
		self.client.force_login(self.recruiter1)
		response = self.client.get(reverse("post_job"))
		self.assertRedirects(response, reverse("jobs:add_job"))

	def test_post_job_blocks_job_seeker(self):
		self.client.force_login(self.seeker1)
		response = self.client.get(reverse("post_job"))
		self.assertRedirects(response, reverse("jobs:job_list"))

	def test_application_details_includes_recruiter_status_update_form(self):
		self.client.force_login(self.recruiter1)
		response = self.client.get(reverse("application_details", kwargs={"pk": self.app1.pk}))
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context["is_job_recruiter"])
		self.assertContains(response, "Update Status")
		self.assertContains(response, "Update Candidate Status")

	def test_update_application_status_redirects_to_next(self):
		self.client.force_login(self.recruiter1)
		next_target = reverse("application_details", kwargs={"pk": self.app1.pk})
		response = self.client.post(
			reverse("update_application_status", kwargs={"pk": self.app1.pk}),
			{"status": "shortlisted", "next": next_target},
		)
		self.assertRedirects(response, next_target)
		self.app1.refresh_from_db()
		self.assertEqual(self.app1.status, "shortlisted")

	def test_application_initial_status_is_pending_and_shows_resume_on_my_applications(self):
		self.client.force_login(self.seeker1)
		app = Application.objects.get(pk=self.app1.pk)
		self.assertEqual(app.status, Application.STATUS_PENDING)

		history_response = self.client.get(reverse("my_applications"))
		self.assertEqual(history_response.status_code, 200)
		self.assertContains(history_response, self.job1.title)
		self.assertContains(history_response, self.company.name)
		self.assertContains(history_response, "Pending")
		self.assertContains(history_response, "Resume:")
		self.assertContains(history_response, self.resume1.resume_file.url)

	def test_recruiter_status_update_displays_checkmark_and_updates_seeker_view(self):
		self.client.force_login(self.recruiter1)
		response = self.client.post(
			reverse("update_application_status", kwargs={"pk": self.app1.pk}),
			{"status": Application.STATUS_SELECTED},
			follow=True,
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Application status updated to Selected.")
		self.assertContains(response, "✓")

		self.app1.refresh_from_db()
		self.assertEqual(self.app1.status, Application.STATUS_SELECTED)

		# Seeker views my_applications and sees updated status
		self.client.force_login(self.seeker1)
		seeker_response = self.client.get(reverse("my_applications"))
		self.assertEqual(seeker_response.status_code, 200)
		self.assertContains(seeker_response, "Selected")

