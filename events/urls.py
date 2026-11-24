from django.urls import path
from . import views

urlpatterns = [
    path("", views.catalog, name="home"),
    path("events/new/", views.create, name="event-create"),
    path("events/<int:pk>/", views.detail, name="event"),
    path("events/<int:pk>/cover/", views.cover, name="event-cover"),
    path("invite/<uuid:token>/", views.detail, name="invite"),
    path("invite/<uuid:token>/cover/", views.cover, name="invite-cover"),
]
