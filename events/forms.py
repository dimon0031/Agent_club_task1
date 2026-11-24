from io import BytesIO

from django import forms
from django.utils import timezone
from PIL import Image, ImageOps

from .models import Event


class EventForm(forms.ModelForm):
    image = forms.FileField(label="Обкладинка", required=False,
                            help_text="JPEG, PNG або WebP, до 5 МіБ.",
                            widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}))

    class Meta:
        model = Event
        fields = ["title", "description", "starts_at", "capacity", "visibility", "image"]
        widgets = {"starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"},
                                                    format="%Y-%m-%dT%H:%M")}
        help_texts = {"starts_at": "За київським часом."}

    def clean_starts_at(self):
        value = self.cleaned_data["starts_at"]
        if self.instance.pk and self.instance.starts_at.replace(second=0, microsecond=0) == value:
            return self.instance.starts_at
        if value <= timezone.now():
            raise forms.ValidationError("Виберіть дату в майбутньому.")
        return value

    def clean_image(self):
        upload = self.cleaned_data.get("image")
        if not upload:
            return b""
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Максимальний розмір — 5 МіБ.")
        try:
            with Image.open(upload, formats=("JPEG", "PNG", "WEBP")) as image:
                if image.width * image.height > 12_000_000:
                    raise forms.ValidationError("Максимальна площа — 12 мегапікселів.")
                image.thumbnail((1400, 1000))
                output = BytesIO()
                ImageOps.exif_transpose(image).convert("RGB").save(output, format="JPEG", quality=85)
                return output.getvalue()
        except (OSError, ValueError, Image.DecompressionBombError, SyntaxError):
            raise forms.ValidationError("Виберіть справне зображення JPEG, PNG або WebP.")
