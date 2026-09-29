from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
	ACCOUNT_TYPES = [
		("job_seeker", "Job Seeker"),
		("recruiter", "Recruiter"),
	]

	user = models.OneToOneField(
		User,
		on_delete=models.CASCADE,
		related_name="profile"
	)

	account_type = models.CharField(
		max_length=20,
		choices=ACCOUNT_TYPES,
		default="job_seeker"
	)

	profile_photo = models.ImageField(
		upload_to="profile_photos/",
		blank=True,
		null=True
	)

	phone = models.CharField(max_length=20, blank=True)
	location = models.CharField(max_length=150, blank=True)
	professional_headline = models.CharField(max_length=180, blank=True)
	about = models.TextField(blank=True)
	skills = models.TextField(blank=True)
	education = models.TextField(blank=True)
	experience = models.TextField(blank=True)
	linkedin = models.URLField(blank=True)
	github = models.URLField(blank=True)
	portfolio = models.URLField(blank=True)

	def __str__(self):
		return f"{self.user.username} profile"
