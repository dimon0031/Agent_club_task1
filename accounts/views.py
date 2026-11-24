from django.contrib.auth import login
from django.contrib.auth.forms import BaseUserCreationForm
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import User


class RegistrationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email",)

    def clean_email(self):
        return User.objects.normalize_email(self.cleaned_data["email"])


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            if not User.objects.filter(email=form.cleaned_data["email"]).exists():
                raise
            form.add_error("email", "Адреса вже зареєстрована.")
        else:
            login(request, user)
            return redirect("home")
    return render(request, "register.html", {"form": form})
