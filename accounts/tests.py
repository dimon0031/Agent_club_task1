from django.test import Client, TestCase
from django.urls import reverse
from .models import User


class AccountTests(TestCase):
    def test_two_accounts(self):
        for email in ("one@example.com", "two@example.com"):
            client = Client()
            password = "Summer-hills-38491"
            page = client.post(reverse("register"), {
                "email": email, "password1": password, "password2": password,
            }, follow=True)
            self.assertContains(page, email)
            client.post(reverse("logout"))
            self.assertNotIn("_auth_user_id", client.session)
            page = client.post(reverse("login"), {
                "username": email.upper(), "password": password,
            }, follow=True)
            self.assertContains(page, email)
        self.assertEqual(User.objects.count(), 2)

    def test_duplicate_email(self):
        User.objects.create_user("one@example.com", "Original-82540")
        page = self.client.post(reverse("register"), {
            "email": "ONE@example.com", "password1": "Summer-hills-38491",
            "password2": "Summer-hills-38491",
        })
        self.assertIn("email", page.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)
