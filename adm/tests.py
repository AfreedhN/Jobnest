import io
import shutil
import tempfile

from PIL import Image
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Profile


class AuthenticationViewTest(TestCase):

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

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_password_reset_email_can_reset_account_password(self):
		user = User.objects.create_user(
			username="reset-user",
			email="reset@example.com",
			password="Cobalt7!Drift-Lantern"
		)

		response = self.client.post(
			reverse("password_reset"),
			{"email": user.email}
		)

		self.assertRedirects(response, reverse("password_reset_done"))
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn("Reset your JobNest password", mail.outbox[0].subject)

		reset_url = mail.outbox[0].body.splitlines()[3]
		reset_path = "/" + reset_url.split("/", 3)[3]
		response = self.client.get(reset_path, follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Choose a new password")

		response = self.client.post(
			response.wsgi_request.path,
			{
				"new_password1": "New-Cobalt8!Drift-Lantern",
				"new_password2": "New-Cobalt8!Drift-Lantern",
			},
			follow=True,
		)
		self.assertContains(response, "Password updated")
		user.refresh_from_db()
		self.assertTrue(user.check_password("New-Cobalt8!Drift-Lantern"))

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_password_reset_rejects_unregistered_email(self):
		response = self.client.post(
			reverse("password_reset"),
			{"email": "unregistered@example.com"}
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(
			response,
			"No account is registered with this email address. Please check and try again."
		)
		self.assertEqual(len(mail.outbox), 0)

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_password_reset_sends_to_exact_email_address(self):
		user = User.objects.create_user(
			username="exact-user",
			email="exact@example.com",
			password="Cobalt7!Drift-Lantern"
		)

		response = self.client.post(
			reverse("password_reset"),
			{"email": "exact@example.com"}
		)

		self.assertRedirects(response, reverse("password_reset_done"))
		self.assertEqual(len(mail.outbox), 1)
		self.assertEqual(mail.outbox[0].to, ["exact@example.com"])

	def test_password_reset_confirm_shows_expired_for_invalid_link(self):
		response = self.client.get(
			reverse(
				"password_reset_confirm",
				kwargs={"uidb64": "MQ", "token": "invalid-token-123"}
			)
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Password Reset Link Expired")
		self.assertContains(response, "Request a new link")


	def test_profile_displays_signed_in_user_information(self):
		user = User.objects.create_user(
			username="profile-user",
			first_name="Jordan",
			last_name="Lee",
			email="jordan@example.com",
			password="Cobalt7!Drift-Lantern"
		)
		Profile.objects.create(
			user=user,
			account_type="job_seeker",
			professional_headline="Product designer",
			skills="Research, Prototyping"
		)
		self.client.force_login(user)

		response = self.client.get(reverse("profile"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Jordan Lee")
		self.assertContains(response, "Product designer")
		self.assertContains(response, "Research")

	def test_profile_requires_login(self):
		response = self.client.get(reverse("profile"))

		self.assertRedirects(
			response,
			f"{reverse('login')}?next={reverse('profile')}"
		)

	def test_profile_loads_when_skills_are_empty(self):
		user = User.objects.create_user(
			username="empty-skills-user",
			first_name="Ava",
			last_name="Stone",
			email="ava@example.com",
			password="Cobalt7!Drift-Lantern"
		)
		Profile.objects.create(user=user, account_type="job_seeker", skills="")
		self.client.force_login(user)

		response = self.client.get(reverse("profile"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Ava Stone")
		self.assertContains(response, "Add your strongest skills")

	def test_edit_profile_updates_user_and_profile_fields(self):
		user = User.objects.create_user(
			username="edit-profile-user",
			first_name="Old",
			last_name="Name",
			email="old@example.com",
			password="Cobalt7!Drift-Lantern"
		)
		Profile.objects.create(user=user, account_type="job_seeker")
		self.client.force_login(user)

		response = self.client.post(
			reverse("edit_profile"),
			{
				"first_name": "New",
				"last_name": "Surname",
				"email": "new@example.com",
				"phone": "+91 98765 43210",
				"location": "Bengaluru",
				"professional_headline": "Senior Python Developer",
				"about": "Experienced in Django and APIs.",
				"skills": "Python, Django, FastAPI",
				"education": "B.Tech in CS",
				"experience": "5 years building Python apps",
				"linkedin": "https://linkedin.com/in/example",
				"github": "https://github.com/example",
				"portfolio": "https://example.com",
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		user.refresh_from_db()
		self.assertEqual(user.first_name, "New")
		self.assertEqual(user.last_name, "Surname")
		self.assertEqual(user.email, "new@example.com")
		self.assertEqual(user.profile.phone, "+91 98765 43210")
		self.assertEqual(user.profile.location, "Bengaluru")
		self.assertEqual(user.profile.professional_headline, "Senior Python Developer")
		self.assertContains(response, "Senior Python Developer")
		self.assertContains(response, "Your profile has been updated successfully.")
		self.assertContains(response, "account-success-icon")
		self.assertContains(response, "✓")

	def test_edit_profile_allows_valid_image_upload(self):
		user = User.objects.create_user(
			username="photo-user",
			email="photo@example.com",
			password="Cobalt7!Drift-Lantern"
		)
		Profile.objects.create(user=user, account_type="job_seeker")
		self.client.force_login(user)

		file = io.BytesIO()
		img = Image.new("RGB", size=(100, 100), color=(73, 109, 137))
		img.save(file, "jpeg")
		file.seek(0)
		photo = SimpleUploadedFile("avatar.jpg", file.read(), content_type="image/jpeg")

		response = self.client.post(
			reverse("edit_profile"),
			{
				"first_name": "Photo",
				"last_name": "User",
				"email": "photo@example.com",
				"profile_photo": photo,
			},
			follow=True,
		)
		self.assertEqual(response.status_code, 200)
		user.refresh_from_db()
		self.assertTrue(bool(user.profile.profile_photo))
		self.assertIn("avatar", user.profile.profile_photo.name)

	def test_edit_profile_rejects_document_upload(self):
		user = User.objects.create_user(
			username="doc-user",
			email="doc@example.com",
			password="Cobalt7!Drift-Lantern"
		)
		Profile.objects.create(user=user, account_type="job_seeker")
		self.client.force_login(user)

		doc_file = SimpleUploadedFile("document.pdf", b"%PDF-1.4 sample pdf", content_type="application/pdf")

		response = self.client.post(
			reverse("edit_profile"),
			{
				"first_name": "Doc",
				"last_name": "User",
				"email": "doc@example.com",
				"profile_photo": doc_file,
			},
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Only image files")
		user.refresh_from_db()
		self.assertFalse(bool(user.profile.profile_photo))

	def test_edit_profile_rejects_non_profile_photo_files(self):
		user = User.objects.create_user(
			username="other-file-user",
			email="other@example.com",
			password="Cobalt7!Drift-Lantern"
		)
		Profile.objects.create(user=user, account_type="job_seeker")
		self.client.force_login(user)

		doc_file = SimpleUploadedFile("resume.docx", b"docx data", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

		response = self.client.post(
			reverse("edit_profile"),
			{
				"first_name": "Other",
				"last_name": "User",
				"email": "other@example.com",
				"resume_doc": doc_file,
			},
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Only a profile photo can be uploaded")
		user.refresh_from_db()
		self.assertFalse(bool(user.profile.profile_photo))

	def test_login_authenticates_and_honors_safe_next_url(self):
		user = User.objects.create_user(
			username="recruiter",
			email="recruiter@example.com",
			password="Cobalt7!Drift-Lantern"
		)
		Profile.objects.create(user=user, account_type="recruiter")

		response = self.client.post(
			reverse("login"),
			{
				"username": "recruiter@example.com",
				"password": "Cobalt7!Drift-Lantern",
				"next": "/jobs/add/",
			}
		)

		self.assertRedirects(response, "/jobs/add/", fetch_redirect_response=False)
		self.assertTrue(response.wsgi_request.user.is_authenticated)

	def test_login_page_carries_ats_destination_into_registration(self):
		response = self.client.get(
			reverse("login"),
			{"next": reverse("ats_analyzer")},
		)

		self.assertContains(response, 'name="next" value="/ats-analyzer/"')
		self.assertContains(response, 'href="/register/?next=/ats-analyzer/"')

	def test_registration_returns_to_safe_ats_destination(self):
		response = self.client.post(
			reverse("register"),
			{
				"first_name": "Avery",
				"last_name": "Candidate",
				"email": "avery@example.com",
				"username": "avery-candidate",
				"password": "Cobalt7!Drift-Lantern",
				"confirm_password": "Cobalt7!Drift-Lantern",
				"account_type": "job_seeker",
				"terms": "on",
				"next": reverse("ats_analyzer"),
			},
		)

		self.assertRedirects(response, reverse("ats_analyzer"), fetch_redirect_response=False)
		self.assertTrue(response.wsgi_request.user.is_authenticated)

	def test_successful_login_shows_checkmark_and_login_successful_message(self):
		user = User.objects.create_user(
			username="login-user",
			email="login@example.com",
			password="Cobalt7!Drift-Lantern"
		)
		Profile.objects.create(user=user, account_type="job_seeker")

		response = self.client.post(
			reverse("login"),
			{"username": "login-user", "password": "Cobalt7!Drift-Lantern"},
			follow=True,
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Login successful.")
		self.assertContains(response, "account-success-icon")
		self.assertContains(response, "✓")

	def test_create_account_shows_checkmark_and_account_created_message(self):
		response = self.client.post(
			reverse("register"),
			{
				"first_name": "New",
				"last_name": "Account",
				"email": "newaccount@example.com",
				"username": "newaccount",
				"password": "Cobalt7!Drift-Lantern",
				"confirm_password": "Cobalt7!Drift-Lantern",
				"account_type": "job_seeker",
				"terms": "on",
			},
			follow=True,
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Your account has been created successfully.")
		self.assertContains(response, "account-success-icon")
		self.assertContains(response, "✓")

	def test_login_rejects_invalid_credentials(self):
		response = self.client.post(
			reverse("login"),
			{"username": "unknown", "password": "wrong-password"}
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Invalid username/email or password.")

	def test_registration_creates_recruiter_profile_and_logs_in(self):
		response = self.client.post(
			reverse("register"),
			{
				"first_name": "Riley",
				"last_name": "Recruiter",
				"email": "riley@example.com",
				"username": "riley-recruiter",
				"password": "Cobalt7!Drift-Lantern",
				"confirm_password": "Cobalt7!Drift-Lantern",
				"account_type": "recruiter",
				"terms": "on",
			}
		)

		user = User.objects.get(username="riley-recruiter")
		self.assertRedirects(response, reverse("home"))
		self.assertEqual(user.profile.account_type, "recruiter")
		self.assertTrue(response.wsgi_request.user.is_authenticated)

	def test_registration_shows_missing_password_error_below_password_field(self):
		response = self.client.post(
			reverse("register"),
			{
				"first_name": "Riley",
				"last_name": "Recruiter",
				"email": "riley@example.com",
				"username": "riley-recruiter",
				"password": "",
				"confirm_password": "Cobalt7!Drift-Lantern",
				"account_type": "recruiter",
				"terms": "on",
			}
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(
			response,
			'id="passwordError" data-for="password" aria-live="polite">Password is required.'
		)

	def test_registration_shows_password_validation_errors_below_password_field(self):
		response = self.client.post(
			reverse("register"),
			{
				"first_name": "Riley",
				"last_name": "Recruiter",
				"email": "riley@example.com",
				"username": "riley-recruiter",
				"password": "short",
				"confirm_password": "short",
				"account_type": "recruiter",
				"terms": "on",
			}
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(
			response,
			'id="passwordError" data-for="password" aria-live="polite">This password is too short.'
		)

	def test_register_page_renders_centered_create_account_button(self):
		response = self.client.get(reverse("register"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Create Account")
		self.assertContains(response, 'class="auth-submit-center"')
		self.assertContains(response, "btn-primary full-width")

	def test_first_time_visitor_sees_home_page_normally(self):
		self.client.logout()
		root_response = self.client.get("/")
		self.assertEqual(root_response.status_code, 200)
		self.assertContains(root_response, "JobNest")
		self.assertContains(root_response, "Find a job where")

		home_response = self.client.get(reverse("home"))
		self.assertEqual(home_response.status_code, 200)
		self.assertContains(home_response, "JobNest")

	def test_authenticated_session_maintained_across_pages(self):
		user = User.objects.create_user(
			username="session_user",
			email="session@example.com",
			password="SecurePassword123!"
		)
		Profile.objects.create(user=user, account_type="job_seeker")

		# Login
		login_response = self.client.post(
			reverse("login"),
			{"username": "session_user", "password": "SecurePassword123!"},
			follow=True,
		)
		self.assertEqual(login_response.status_code, 200)
		self.assertTrue(login_response.wsgi_request.user.is_authenticated)

		# Navigate to Home
		home_resp = self.client.get(reverse("home"))
		self.assertEqual(home_resp.status_code, 200)
		self.assertTrue(home_resp.wsgi_request.user.is_authenticated)

		# Navigate to Profile
		profile_resp = self.client.get(reverse("profile"))
		self.assertEqual(profile_resp.status_code, 200)
		self.assertTrue(profile_resp.wsgi_request.user.is_authenticated)

		# Already logged in user navigating to login/register is redirected to home
		relogin_resp = self.client.get(reverse("login"))
		self.assertRedirects(relogin_resp, reverse("home"))

		reregister_resp = self.client.get(reverse("register"))
		self.assertRedirects(reregister_resp, reverse("home"))

	def test_logout_redirects_to_home_and_clears_session(self):
		user = User.objects.create_user(
			username="logout_user",
			email="logout@example.com",
			password="SecurePassword123!"
		)
		Profile.objects.create(user=user, account_type="job_seeker")

		self.client.force_login(user)

		# Logout redirects to home
		logout_response = self.client.get(reverse("logout"))
		self.assertRedirects(logout_response, reverse("home"))

		# Now user is unauthenticated
		# Home page still works normally
		home_resp = self.client.get(reverse("home"))
		self.assertEqual(home_resp.status_code, 200)
		self.assertFalse(home_resp.wsgi_request.user.is_authenticated)

		# Protected features require login
		profile_resp = self.client.get(reverse("profile"))
		self.assertRedirects(profile_resp, f"{reverse('login')}?next={reverse('profile')}")


