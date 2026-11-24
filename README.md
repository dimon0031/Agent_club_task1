# Тусовка

Каркас на Django із серверними HTML-шаблонами, реєстрацією за email і SQLite.

## Локальний запуск у Linux / WSL

З кореня репозиторію з Python 3.14 та venv:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export DJANGO_DEBUG=1
python manage.py migrate
python manage.py runserver
```

Відкрийте [головну сторінку](http://127.0.0.1:8000/). У локальному режимі діє ключ для розробки. Поза локальним режимом задайте випадковий секрет у `DJANGO_SECRET_KEY` та дозволені хости через кому в `DJANGO_ALLOWED_HOSTS`.

Тести в налаштованому середовищі запускаються командою `python manage.py test`.

## Події

Після входу оберіть «Створити подію». Каталог показує майбутні публічні події. Для приватної події скопіюйте запрошення з її сторінки. Обкладинка необов’язкова.

Тести подій із кореня проєкту у WSL:

```sh
DJANGO_DEBUG=1 .venv/bin/python manage.py test events.test_events
```
