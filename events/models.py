import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Event(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField("Назва", max_length=160)
    search_title = models.TextField(editable=False)
    description = models.TextField("Опис", max_length=5000)
    starts_at = models.DateTimeField("Дата й час", db_index=True)
    capacity = models.PositiveIntegerField("Кількість місць", validators=[MinValueValidator(1)])
    visibility = models.CharField("Тип події", max_length=7, choices=[
        ("public", "Публічна"), ("private", "Приватна"),
    ], default="public")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    cover = models.BinaryField(blank=True, default=bytes)

    def save(self, *args, **kwargs):
        self.search_title = self.title.casefold()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.visibility == "private":
            return reverse("invite", args=[self.token])
        return reverse("event", args=[self.pk])
