from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    @classmethod
    def normalize_email(cls, email):
        return (email or "").strip().lower()

    def get_by_natural_key(self, email):
        return self.get(email=self.normalize_email(email))

    def create_user(self, email, password=None, **fields):
        if not email:
            raise ValueError("Email required")
        user = self.model(email=self.normalize_email(email), **fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **fields):
        for flag in ("is_staff", "is_superuser"):
            if fields.setdefault(flag, True) is not True:
                raise ValueError(f"{flag} must be True")
        return self.create_user(email, password, **fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("Електронна пошта", unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()
