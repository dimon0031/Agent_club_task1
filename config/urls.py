from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from accounts.views import register

urlpatterns = [
    path("", include("events.urls")),
    path("accounts/register/", register, name="register"),
    path("accounts/login/", LoginView.as_view(template_name="login.html"), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
]
