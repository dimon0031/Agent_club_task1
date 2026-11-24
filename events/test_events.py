import uuid
from datetime import timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.models import User
from .models import Event


class EventTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user("author@example.com")
        cls.reader = User.objects.create_user("reader@example.com")

    def setUp(self):
        self.client.force_login(self.author)
        self.payload = {
            "title": "Книжковий клуб", "description": "Обговорення книжки",
            "starts_at": (timezone.localtime() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            "capacity": 8, "visibility": "public",
        }

    def test_public_creation_and_search(self):
        response = self.client.post(reverse("event-create"), self.payload)
        event = Event.objects.get()
        self.assertRedirects(response, event.get_absolute_url())
        self.assertEqual(event.author, self.author)
        self.assertTrue(event.attendances.filter(user=self.author).exists())
        self.assertContains(self.client.get(event.get_absolute_url()), "Вільних місць: 7 із 8")
        self.client.force_login(self.reader)
        self.assertContains(self.client.get(reverse("home"), {"q": "КЛУБ"}), event.title)
        self.assertNotContains(self.client.get(reverse("home"), {"q": "спорт"}), event.title)
        self.assertContains(self.client.get(event.get_absolute_url()), event.description)

    def test_private_invitation_and_cover(self):
        picture = BytesIO()
        Image.new("RGB", (3, 2)).save(picture, format="PNG")
        self.payload.update(visibility="private", image=SimpleUploadedFile("book.png", picture.getvalue()))
        page = self.client.post(reverse("event-create"), self.payload, follow=True)
        event = Event.objects.get()
        invite = event.get_absolute_url()
        self.assertContains(page, "Посилання-запрошення")
        self.assertContains(page, invite)
        self.client.force_login(self.reader)
        self.assertNotContains(self.client.get(reverse("home")), event.title)
        search = self.client.get(reverse("home"), {"q": event.title})
        self.assertEqual(list(search.context["events"]), [])
        self.assertNotContains(search, invite)
        self.assertContains(self.client.get(invite), event.title)
        for route in ("event", "event-cover"):
            self.assertEqual(self.client.get(reverse(route, args=[event.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("invite", args=[uuid.uuid4()])).status_code, 404)
        cover = self.client.get(reverse("invite-cover", args=[event.token]))
        self.assertEqual(Image.open(BytesIO(cover.content)).format, "JPEG")

    def test_catalog_order_and_past_events(self):
        now = timezone.now()
        for days in (2, -1, 1):
            Event.objects.create(author=self.author, title=str(days), description="Клуб",
                                 starts_at=now + timedelta(days=days), capacity=2)
        events = self.client.get(reverse("home")).context["events"]
        self.assertEqual([event.title for event in events], ["1", "2"])

    def test_invalid_fields(self):
        for field, value in [
            ("capacity", 0), ("starts_at", "2000-01-01T10:00"),
            ("image", SimpleUploadedFile("bad.png", b"invalid")),
            ("image", SimpleUploadedFile("large.png", b"x" * (5 * 1024 * 1024 + 1))),
        ]:
            with self.subTest(field=field):
                page = self.client.post(reverse("event-create"), {**self.payload, field: value})
                self.assertIn(field, page.context["form"].errors)
                self.assertFalse(Event.objects.exists())

    def test_author_edits_and_keeps_participants_and_cover(self):
        self.client.post(reverse("event-create"), self.payload)
        event = Event.objects.get()
        event.attendances.create(user=self.reader)
        Event.objects.filter(pk=event.pk).update(cover=b"original")
        url = reverse("event-edit", args=[event.pk])
        self.assertContains(self.client.get(event.get_absolute_url()), url)
        changed = dict(self.payload, capacity=1, title="Нова назва", visibility="private")
        page = self.client.post(url, changed)
        self.assertIn("capacity", page.context["form"].errors)
        event.refresh_from_db()
        self.assertEqual(event.title, self.payload["title"])
        changed["capacity"] = 2
        response = self.client.post(url, changed)
        event.refresh_from_db()
        self.assertRedirects(response, reverse("invite", args=[event.token]))
        self.assertEqual(event.cover, b"original")
        self.assertEqual(event.title, changed["title"])
        self.assertEqual(event.attendances.count(), 2)
        self.assertEqual(self.client.get(reverse("event", args=[event.pk])).status_code, 404)

    def test_only_author_can_edit(self):
        self.client.post(reverse("event-create"), self.payload)
        event = Event.objects.get()
        url = reverse("event-edit", args=[event.pk])
        self.client.force_login(self.reader)
        self.assertNotContains(self.client.get(event.get_absolute_url()), url)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, dict(self.payload, title="Інша")).status_code, 404)
        event.refresh_from_db()
        self.assertEqual(event.title, self.payload["title"])

    def test_anonymous_creation_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("event-create"), self.payload)
        self.assertRedirects(response, reverse("login") + "?next=" + reverse("event-create"))
        self.assertFalse(Event.objects.exists())

    def test_catalog_seats_after_creation_join_cancel_and_edit(self):
        self.client.post(reverse("event-create"), dict(self.payload, capacity=2))
        event = Event.objects.get()
        home = reverse("home")
        attend = reverse("event-attend", args=[event.pk])
        self.assertContains(self.client.get(home), "Вільних місць: 1 із 2")
        self.client.force_login(self.reader)
        self.client.post(attend, {"action": "join"})
        self.assertContains(self.client.get(home, {"q": "клуб"}), "Вільних місць: 0 із 2")
        self.client.post(attend, {"action": "cancel"})
        self.assertContains(self.client.get(home), "Вільних місць: 1 із 2")
        self.client.force_login(self.author)
        self.client.post(reverse("event-edit", args=[event.pk]), self.payload)
        self.assertContains(self.client.get(home), "Вільних місць: 7 із 8")

    def test_profile_roster_and_private_event_deletion(self):
        self.client.post(reverse("event-create"), dict(self.payload, visibility="private"))
        event = Event.objects.get()
        url = event.get_absolute_url()
        delete = reverse("event-delete", args=[event.pk])
        profile = reverse("profile")
        self.assertContains(self.client.get(profile), url)
        self.client.force_login(self.reader)
        self.assertNotContains(self.client.get(profile), url)
        self.client.post(reverse("invite-attend", args=[event.token]), {"action": "join"})
        self.assertContains(self.client.get(profile), url)
        self.assertNotContains(self.client.get(url), self.author.email)
        self.assertEqual(self.client.post(delete).status_code, 404)
        self.client.force_login(self.author)
        self.assertContains(self.client.get(url), self.reader.email)
        self.assertContains(self.client.get(delete), event.title)
        self.assertTrue(Event.objects.filter(pk=event.pk).exists())
        self.assertRedirects(self.client.post(delete), profile)
        self.client.force_login(self.reader)
        self.assertNotContains(self.client.get(profile), url)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_comments_require_login_and_valid_content(self):
        self.client.post(reverse("event-create"), dict(self.payload, visibility="private"))
        event = Event.objects.get()
        url = event.get_absolute_url()
        self.client.logout()
        self.assertEqual(self.client.post(url, {"body": "Привіт"}).status_code, 302)
        self.assertFalse(event.comments.exists())
        self.client.force_login(self.reader)
        for body in ("   ", "x" * 1001):
            page = self.client.post(url, {"body": body})
            self.assertIn("body", page.context["comment_form"].errors)
        self.assertEqual(self.client.post(reverse("event", args=[event.pk]),
                                          {"body": "Привіт"}).status_code, 404)
        page = self.client.post(url, {"body": "До зустрічі!"}, follow=True)
        self.assertContains(page, "До зустрічі!")
        self.assertEqual(event.comments.get().author, self.reader)
