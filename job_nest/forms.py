from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError

UserModel = get_user_model()


class JobNestPasswordResetForm(PasswordResetForm):
    """
    Password reset form that validates the email exists in the database
    and sends the reset link to the exact email address entered by the user.
    """

    email = forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "id": "id_email",
                "placeholder": "Enter your registered email",
                "required": "required",
                "autofocus": "autofocus",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            raise ValidationError(
                "Please enter your email address.",
                code="required",
            )

        active_users = UserModel._default_manager.filter(
            email__iexact=email,
            is_active=True,
        )

        if not active_users.exists():
            raise ValidationError(
                "No account is registered with this email address. Please check and try again.",
                code="email_not_found",
            )

        if not any(user.has_usable_password() for user in active_users):
            raise ValidationError(
                "This account does not have a usable password set.",
                code="unusable_password",
            )

        return email

    def get_users(self, email):
        """
        Return active users matching the cleaned email who have usable passwords.
        """
        email_field_name = UserModel.get_email_field_name()
        active_users = UserModel._default_manager.filter(**{
            f"{email_field_name}__iexact": email,
            "is_active": True,
        })
        return [user for user in active_users if user.has_usable_password()]

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        # Guarantee that the link is delivered to the exact email address entered
        recipient = self.cleaned_data.get("email", "").strip() or to_email
        super().send_mail(
            subject_template_name,
            email_template_name,
            context,
            from_email,
            recipient,
            html_email_template_name=html_email_template_name,
        )
