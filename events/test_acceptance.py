from datetime import timedelta
from urllib.parse import urlencode

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone


class PrivateEventJourneyTests(TestCase):
    def post_form(self, browser, url, **fields):
        fields["csrfmiddlewaretoken"] = browser.cookies["csrftoken"].value
        return browser.post(url, fields, follow=True)

    def register(self, browser, url, email, destination):
        page = browser.get(url)
        self.assertContains(page, "Створити акаунт")
        return self.post_form(
            browser, url, email=email, password1="Night-beat-7241",
            password2="Night-beat-7241", next=destination,
        )

    def test_guest_registers_from_invitation_and_frees_the_last_seat(self):
        host = Client(enforce_csrf_checks=True)
        guest = Client(enforce_csrf_checks=True)
        create_url = reverse("event-create")
        self.register(host, reverse("register"), "host@example.org", create_url)
        detail = self.post_form(
            host, create_url, title="Ніч джазу", description="Живий концерт",
            starts_at=(timezone.localtime() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            capacity=2, visibility="private",
        )
        event = detail.context["event"]
        invite = event.get_absolute_url()
        self.assertContains(detail, "Вільних місць: 1 із 2")
        self.assertNotContains(guest.get(reverse("home")), event.title)

        landing = guest.get(invite)
        login_url = reverse("login") + "?next=" + invite
        self.assertContains(landing, login_url)
        register_url = reverse("register") + "?" + urlencode({"next": invite})
        self.assertContains(guest.get(login_url), register_url)
        returned = self.register(guest, register_url, "guest@example.org", invite)
        self.assertEqual(returned.request["PATH_INFO"], invite)

        attendance = reverse("invite-attend", args=[event.token])
        full = self.post_form(guest, attendance, action="join")
        self.assertContains(full, "Вільних місць: 0 із 2")
        self.assertContains(guest.get(reverse("profile")), invite)
        self.post_form(guest, invite, body="Побачимось на концерті!")
        roster = host.get(invite)
        self.assertContains(roster, "guest@example.org")
        self.assertContains(roster, "Побачимось на концерті!")

        cancelled = self.post_form(guest, attendance, action="cancel")
        self.assertContains(cancelled, "Вільних місць: 1 із 2")
        self.assertNotContains(guest.get(reverse("profile")), invite)
        delete_url = reverse("event-delete", args=[event.pk])
        self.assertContains(host.get(delete_url), "Скасувати")
        self.assertContains(self.post_form(host, delete_url), "Подію видалено.")
        self.assertContains(guest.get(invite), "Перейти до афіші", status_code=404)
