from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection, transaction
from django.http import HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import EventForm
from .models import Attendance, Event


def catalog(request):
    query = request.GET.get("q", "").strip()
    events = Event.objects.filter(visibility="public", starts_at__gt=timezone.now())
    if query:
        events = events.filter(search_title__contains=query.casefold())
    return render(request, "home.html", {
        "events": events.defer("cover").order_by("starts_at", "pk"), "query": query,
    })


@login_required
def create(request):
    form = EventForm(request.POST, request.FILES) if request.method == "POST" else EventForm()
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.author = request.user
        event.cover = form.cleaned_data["image"]
        with transaction.atomic():
            event.save()
            Attendance.objects.create(event=event, user=request.user)
        return redirect(event)
    return render(request, "events/create.html", {"form": form})


@login_required
def edit(request, pk):
    event = get_object_or_404(Event, pk=pk, author=request.user)
    form = EventForm(instance=event)
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            fields = ["title", "search_title", "description", "starts_at", "capacity", "visibility"]
            if form.cleaned_data["image"]:
                event.cover = form.cleaned_data["image"]
                fields.append("cover")
            # Acquire SQLite's write lock before counting seats so a concurrent
            # reservation cannot slip between the check and the capacity change.
            with transaction.atomic():
                event.save(update_fields=fields)
                if event.capacity < event.attendances.count():
                    transaction.set_rollback(True)
                    form.add_error("capacity", "Кількість місць менша за кількість учасників.")
                else:
                    return redirect(event)
    return render(request, "events/create.html", {"form": form, "editing": True})


def visible_event(pk=None, token=None):
    if token is not None:
        return get_object_or_404(Event, visibility="private", token=token)
    return get_object_or_404(Event, visibility="public", pk=pk)


def detail(request, **lookup):
    event = visible_event(**lookup)
    return render(request, "events/detail.html", {
        "remaining": event.capacity - event.attendances.count(),
        "joined": request.user.is_authenticated and event.attendances.filter(user=request.user).exists(),
        "closed": event.starts_at <= timezone.now(),
        "event": event, "invite_url": request.build_absolute_uri(event.get_absolute_url())
        if event.visibility == "private" and request.user.pk == event.author_id else "",
    })


@require_POST
@login_required
def attend(request, **lookup):
    event = visible_event(**lookup)
    action = request.POST.get("action")
    if action not in ("join", "cancel"):
        return HttpResponseBadRequest("Невідома дія.")
    if event.starts_at <= timezone.now():
        messages.info(request, "Подія вже почалася. Запис закрито.")
    elif action == "cancel":
        event.attendances.filter(user=request.user).delete()
    else:
        # One SQLite write statement serializes competing reservations for the last place.
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO events_attendance (event_id, user_id)
                SELECT id, %s FROM events_event
                WHERE id = %s AND visibility = %s AND starts_at > %s AND capacity > (
                    SELECT COUNT(*) FROM events_attendance WHERE event_id = %s
                )
                ON CONFLICT (event_id, user_id) DO NOTHING
            """, [request.user.pk, event.pk, event.visibility,
                  connection.ops.adapt_datetimefield_value(timezone.now()), event.pk])
            inserted = cursor.rowcount
        if not inserted and not Attendance.objects.filter(event=event, user=request.user).exists():
            messages.info(request, "Запис недоступний. Перевірте час події й кількість місць.")
    return redirect(event)


def cover(request, **lookup):
    event = visible_event(**lookup)
    if not event.cover:
        raise Http404
    return HttpResponse(event.cover, content_type="image/jpeg")
