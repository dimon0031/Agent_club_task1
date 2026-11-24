from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import Client, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .models import Event


class AttendanceTests(TransactionTestCase):
    def setUp(self):
        self.clients = []
        for name in ("one", "two"):
            user = get_user_model().objects.create_user(f"{name}@example.com")
            client = Client()
            client.force_login(user)
            self.clients.append(client)
        self.event = Event.objects.create(
            author=user, title="Зустріч", starts_at=timezone.now() + timedelta(days=1),
            capacity=1,
        )
        self.url = reverse("event-attend", args=[self.event.pk])

    def test_last_seat_and_repeated_requests(self):
        first, second = self.clients
        for client in (first, first, second):
            client.post(self.url, {"action": "join"})
        self.assertContains(first.get(self.event.get_absolute_url()), "Скасувати участь")
        self.assertContains(second.get(self.event.get_absolute_url()), "Вільних місць немає.")
        for _ in range(2):
            first.post(self.url, {"action": "cancel"})
        self.assertContains(second.get(self.event.get_absolute_url()), "Вільних місць: 1 із 1")
        response = second.post(self.url, {"action": "join"}, follow=True)
        self.assertContains(response, "Ви у списку учасників.")

    def test_concurrent_join(self):
        barrier = Barrier(2)

        def join(client):
            try:
                barrier.wait(timeout=5)
                return client.post(self.url, {"action": "join"}).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(join, self.clients)), [302, 302])
        self.assertEqual(self.event.attendances.count(), 1)

    def test_private_and_closed_event(self):
        self.event.visibility = "private"
        self.event.save()
        private_url = reverse("invite-attend", args=[self.event.token])
        user = self.clients[0]
        self.assertEqual(user.post(self.url, {"action": "join"}).status_code, 404)
        self.assertEqual(Client().post(private_url, {"action": "join"}).status_code, 302)
        self.assertEqual(user.get(private_url).status_code, 405)
        self.assertEqual(self.event.attendances.count(), 0)
        user.post(private_url, {"action": "join"})
        self.assertEqual(self.event.attendances.count(), 1)
        user.post(private_url, {"action": "cancel"})
        self.event.starts_at = timezone.now() - timedelta(minutes=1)
        self.event.save()
        user.post(private_url, {"action": "join"})
        self.assertEqual(self.event.attendances.count(), 0)
