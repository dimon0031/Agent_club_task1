from django.contrib.auth.forms import BaseUserCreationForm

from .models import User


class RegistrationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email",)

    def clean_email(self):
        return User.objects.normalize_email(self.cleaned_data["email"])
