import shutil
import tempfile
from io import BytesIO

from docx import Document
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from adm.models import Profile
from companies.models import Company
from jobs.models import Job
from resumes.models import Resume
from .models import ATSReport
from .services import analyze_resume_text


def make_docx(text):
	document = Document()
	for line in text.splitlines():
		document.add_paragraph(line)
	output = BytesIO()
	document.save(output)
	return output.getvalue()


class ATSAnalyzerViewTest(TestCase):

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
			username="ats-applicant",
			password="test-password",
		)
		Profile.objects.create(user=self.user, account_type="job_seeker")
		self.client.force_login(self.user)

		self.company = Company.objects.create(
			name="Northstar Labs",
			industry="Technology",
			location="Remote",
			verification_status="verified",
		)
		self.job = Job.objects.create(
			company=self.company,
			title="Python Developer",
			location="Remote",
			experience_level="mid",
			skills="Python, Django, SQL",
			description="Build Python APIs with Django and SQL.",
			requirements="Bachelor's degree and 2 years experience. Kubernetes preferred.",
			responsibilities="Develop web services.",
		)
		resume_file = SimpleUploadedFile(
			"backend-resume.docx",
			make_docx(
				"Professional Summary\n"
				"Python and Django developer building APIs.\n"
				"Experience\n"
				"3 years experience developing web services.\n"
				"Education\n"
				"Bachelor's degree in Computer Science.\n"
				"Skills\n"
				"Python, Django"
			),
			content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		)
		self.resume = Resume.objects.create(
			user=self.user,
			resume_file=resume_file,
			skills="Unrelated legacy metadata: Java, Rust",
		)

	def test_form_lists_owned_resumes_and_active_jobs(self):
		response = self.client.get(reverse("ats_analyzer"))

		self.assertEqual(response.status_code, 200)
		resume_filename = self.resume.resume_file.name.rsplit("/", 1)[-1]
		self.assertContains(response, resume_filename)
		self.assertContains(response, 'enctype="multipart/form-data"')
		self.assertContains(response, 'name="resume_file"')
		self.assertContains(response, 'id="atsResumeFilename"')
		self.assertContains(response, 'id="atsRemoveFileBtn"')
		self.assertContains(response, "fa-trash-can")
		self.assertContains(response, "Python Developer - Northstar Labs")

	def test_analysis_uses_selected_file_and_job_content(self):
		response = self.client.post(
			reverse("ats_analyzer"),
			{"resume": self.resume.pk, "job": self.job.pk},
		)

		report = ATSReport.objects.get(user=self.user)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(report.resume, self.resume)
		self.assertEqual(report.job, self.job)
		self.assertEqual(report.matched_skills, ["Python", "Django"])
		self.assertEqual(report.missing_skills, ["SQL"])
		self.assertIn("python", report.matched_keywords)
		self.assertIn("kubernetes", report.missing_keywords)
		self.assertEqual(report.experience_score, 25)
		self.assertEqual(report.education_score, 10)
		self.assertGreater(report.overall_score, 0)
		self.assertLessEqual(report.overall_score, 100)
		self.assertContains(response, "ATS Compatibility Report")
		self.assertContains(response, "Matched Keywords")
		self.assertContains(response, "Missing Keywords")

	def test_uploaded_resume_is_saved_and_used_for_selected_job_analysis(self):
		upload = SimpleUploadedFile(
			"fresh-python-resume.docx",
			make_docx(
				"Professional Summary\n"
				"Python and Django developer.\n"
				"Experience\n"
				"3 years building APIs.\n"
				"Education\n"
				"Bachelor's degree in Computer Science.\n"
				"Skills\n"
				"Python, Django"
			),
			content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		)

		response = self.client.post(
			reverse("ats_analyzer"),
			{"job": self.job.pk, "resume_file": upload},
		)

		uploaded_resume = Resume.objects.get(user=self.user, title="fresh-python-resume.docx")
		report = ATSReport.objects.get(user=self.user)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(report.resume, uploaded_resume)
		self.assertEqual(report.job, self.job)
		self.assertEqual(report.matched_skills, ["Python", "Django"])
		self.assertContains(response, "fresh-python-resume.docx")
		self.assertContains(response, "ATS Compatibility Report")

	def test_upload_form_rejects_unsupported_file_without_saving_it(self):
		response = self.client.post(
			reverse("ats_analyzer"),
			{
				"job": self.job.pk,
				"resume_file": SimpleUploadedFile(
					"resume.txt",
					b"Unsupported resume file",
					content_type="text/plain",
				),
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Legacy DOC files are not supported")
		self.assertEqual(Resume.objects.filter(user=self.user).count(), 1)
		self.assertFalse(ATSReport.objects.exists())

	def test_invalid_selection_keeps_values_and_shows_error(self):
		response = self.client.post(
			reverse("ats_analyzer"),
			{"resume": self.resume.pk, "job": "999999"},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Please choose a valid job.")
		self.assertEqual(response.context["selected_resume_id"], str(self.resume.pk))
		self.assertEqual(response.context["selected_job_id"], "999999")
		self.assertFalse(ATSReport.objects.exists())

	def test_legacy_doc_resume_shows_supported_format_error(self):
		legacy_resume = Resume.objects.create(
			user=self.user,
			resume_file=SimpleUploadedFile("legacy.doc", b"legacy document"),
		)

		response = self.client.post(
			reverse("ats_analyzer"),
			{"resume": legacy_resume.pk, "job": self.job.pk},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Legacy DOC files are not supported")
		self.assertFalse(ATSReport.objects.exists())

	def test_section_scores_use_standalone_heading_aliases(self):
		analysis = analyze_resume_text(
			"Professional Experience\n"
			"3 years building Python and Django services.\n"
			"Academic Qualifications\n"
			"Bachelor's degree in Computer Science.\n"
			"Technical Skills\n"
			"Python, Django, SQL.",
			self.job,
		)

		self.assertEqual(analysis["experience_score"], 25)
		self.assertEqual(analysis["education_score"], 10)
		self.assertEqual(analysis["structure_score"], 5)

	def test_keywords_in_prose_do_not_count_as_resume_sections(self):
		analysis = analyze_resume_text(
			"My experience includes Python and Django. I completed a bachelor's degree.",
			self.job,
		)

		self.assertEqual(analysis["structure_score"], 0)
		self.assertEqual(analysis["experience_score"], 0)
