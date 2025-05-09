import random
import string
from django.core.cache import cache
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from celery import shared_task


def generate_code(length=6):
    return ''.join(random.choices(string.digits, k=length))


def code_already_exists(email):
    return cache.get(f'email_login_code:{email}') is not None


def save_code_to_redis(email, code):
    # Только если кода ещё нет
    if not code_already_exists(email):
        cache.set(f'email_login_code:{email}', code, timeout=600)


def check_code_in_redis(email, code):
    stored_code = cache.get(f'email_login_code:{email}')
    if stored_code and stored_code == code:
        cache.delete(f'email_login_code:{email}')
        return True
    return False


def send_login_code(email, code):
    subject = 'Ваш код для входа'
    from_email = 'noreply@example.com'
    to = [email]

    text_content = f'Ваш код для входа: {code}'
    html_content = render_to_string('emails/login_code.html', {'code': code})
    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@shared_task
def send_login_code_task(email, code):
    subject = 'Ваш код для входа'
    from_email = 'noreply@example.com'
    to = [email]
    text_content = f'Ваш код для входа: {code}'
    html_content = render_to_string('emails/login_code.html', {'code': code})

    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
