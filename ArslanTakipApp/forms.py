from django import forms
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.contrib.auth.models import User
from django.template import loader
from .email_utils import send_email

class PasswordChangingForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Eski Parola'}))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Yeni Parola'}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Yeni Parola Tekrar'}))
    
    class Meta:
        model = User
        fields = ['old_password', 'new_password1', 'new_password2']

class PasswordResettingForm(PasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = loader.render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())  # Clean up the subject

        body = loader.render_to_string(email_template_name, context)

        html_body = None
        if html_email_template_name:
            html_body = loader.render_to_string(html_email_template_name, context)

        # Call the custom send_email function
        try:
            send_email([to_email], subject, body)
            if html_body:
                send_email([to_email], subject, html_body)  # Optionally send HTML version too
        except Exception as e:
            print(f"Failed to send email to {to_email}: {e}")