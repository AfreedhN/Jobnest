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

	def test_line_by_line_feedback_and_grounded_rewrites(self):
		sample_resume = (
			"Professional Summary\n"
			"I am a hardworking software engineer skilled in python and django.\n"
			"Experience\n"
			"Responsible for building REST APIs.\n"
			"Education\n"
			"Bachelor's degree in Computer Science.\n"
			"Skills\n"
			"Python, Django, SQL"
		)
		analysis = analyze_resume_text(sample_resume, self.job)

		self.assertIn("line_improvements", analysis)
		improvements = analysis["line_improvements"]
		self.assertGreater(len(improvements), 0)

		# Check line improvement schema
		for item in improvements:
			self.assertIn("section", item)
			self.assertIn("current_line", item)
			self.assertIn("problem", item)
			self.assertIn("change_to", item)
			self.assertIn("why_change_it", item)
			self.assertIn("missing_keywords", item)

		# Check that first person or buzzword is caught
		problems = [item["problem"] for item in improvements]
		self.assertTrue(any("first-person" in p or "buzzwords" in p or "passive" in p for p in problems))

	def test_twelve_sections_and_clean_section_message(self):
		sample_resume = (
			"Contact Information\n"
			"candidate@example.com | +1-555-0199 | linkedin.com/in/test | github.com/test\n"
			"Professional Summary\n"
			"Software engineer building reliable backend systems.\n"
			"Technical Skills\n"
			"Python, Django, PostgreSQL, Docker\n"
			"Work Experience\n"
			"Engineered microservices using Python and Django.\n"
			"Education\n"
			"Bachelor's degree in Computer Science.\n"
			"Projects\n"
			"Built JobNest portal using Django.\n"
		)
		analysis = analyze_resume_text(sample_resume, self.job)

		self.assertIn("section_analysis", analysis)
		sec_analysis = analysis["section_analysis"]

		# Contact info should be clean
		self.assertEqual(sec_analysis["contact_info"]["status"], "ok")
		self.assertIn("No major issue detected", sec_analysis["contact_info"]["feedback"])

		# Certifications (optional and not provided) should display no major issue detected
		self.assertIn("No major issue detected", sec_analysis["certifications"]["feedback"])

	def test_skills_categorized_into_buckets(self):
		sample_resume = (
			"Technical Skills\n"
			"Python, JavaScript, Django, React, PostgreSQL, Docker, Git"
		)
		analysis = analyze_resume_text(sample_resume, self.job)

		self.assertIn("skills_categorized", analysis)
		cat = analysis["skills_categorized"]
		self.assertIn("Programming Languages", cat)
		self.assertIn("Python", cat["Programming Languages"])
		self.assertIn("Frameworks & Libraries", cat)
		self.assertIn("Django", cat["Frameworks & Libraries"])
		self.assertIn("Databases", cat)
		self.assertIn("PostgreSQL", cat["Databases"])

	def test_deleting_resume_preserves_past_ats_reports(self):
		report = ATSReport.objects.create(
			user=self.user,
			resume=self.resume,
			resume_name=self.resume.title,
			job=self.job,
			overall_score=85,
			skills_score=35,
			experience_score=20,
			keywords_score=15,
			education_score=10,
			structure_score=5,
		)

		self.assertEqual(report.resume, self.resume)
		self.assertEqual(report.resume_name, self.resume.title)

		# Delete resume
		self.resume.delete()

		# Refresh report from DB
		report.refresh_from_db()
		self.assertIsNone(report.resume)
		self.assertEqual(report.resume_name, "My Resume")
		# Verifying __str__ does not crash
		self.assertIn(self.user.username, str(report))

	def test_analysis_with_custom_job_description(self):
		upload = SimpleUploadedFile(
			"cloud-resume.docx",
			make_docx(
				"Contact\n"
				"dev@test.com | 555-123-4567 | linkedin.com/in/dev | github.com/dev\n"
				"Professional Summary\n"
				"Cloud and DevOps engineer.\n"
				"Skills\n"
				"Docker, Kubernetes, AWS, Python\n"
				"Experience\n"
				"Maintained Kubernetes clusters and Docker containers.\n"
				"Education\n"
				"Bachelor's degree in Engineering."
			),
			content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		)

		response = self.client.post(
			reverse("ats_analyzer"),
			{
				"resume_file": upload,
				"analysis_mode": "custom",
				"custom_job_title": "Site Reliability Engineer",
				"custom_job_description": "We need an SRE experienced in Kubernetes, Docker, and AWS.",
			},
		)

		self.assertEqual(response.status_code, 200)
		report = ATSReport.objects.filter(user=self.user).first()
		self.assertIsNotNone(report)
		self.assertIsNone(report.job)
		self.assertEqual(report.job_title_input, "Site Reliability Engineer")
		self.assertIn("Kubernetes", report.matched_skills)
		self.assertContains(response, "Site Reliability Engineer")

