from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import EventForm
from .models import Event


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
        event.save()
        return redirect(event)
    return render(request, "events/create.html", {"form": form})


def visible_event(pk=None, token=None):
    if token is not None:
        return get_object_or_404(Event, visibility="private", token=token)
    return get_object_or_404(Event, visibility="public", pk=pk)


def detail(request, **lookup):
    event = visible_event(**lookup)
    return render(request, "events/detail.html", {
        "event": event, "invite_url": request.build_absolute_uri(event.get_absolute_url())
        if event.visibility == "private" and request.user.pk == event.author_id else "",
    })


def cover(request, **lookup):
    event = visible_event(**lookup)
    if not event.cover:
        raise Http404
    return HttpResponse(event.cover, content_type="image/jpeg")
