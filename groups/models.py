import string
import random
from django.db import models
from taggit.managers import TaggableManager
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from unidecode import unidecode


def generate_unique_code():
    length = 8
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))


class Group(models.Model):
    STATUS_CHOICES = [
        ('O', 'Oppened'),
        ('C', 'Closed'),
    ]

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_creator'
    )
    admins = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='group_admins'
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='group_members'
    )
    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES,
        default='C'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=30)
    about = models.CharField(max_length=300, null=True, blank=True)
    slug = models.SlugField(max_length=200, blank=True)
    code = models.CharField(
        max_length=8,
        unique=True,
        editable=False,
        blank=True,
        db_index=True
    )
    tags = TaggableManager(blank=True)
    logo = models.ImageField(upload_to='group_logos/', blank=True)

    def get_absolute_url(self):
        return reverse("groups:group_detail", args=[self.id, self.slug])

    def save(self, *args, **kwargs):
        # Обновляем slug только если имя изменилось или это новая запись
        if not self.slug or not self.pk or (
            self.pk and self.name != self.__class__.objects.get(pk=self.pk).name
        ):
            self.slug = slugify(unidecode(self.name))

        # Генерируем уникальный код, если он ещё не установлен
        if not self.code:
            while True:
                code = generate_unique_code()
                if not Group.objects.filter(code=code).exists():
                    self.code = code
                    break

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ChatMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="chat_messages"
    )
    text = models.TextField()
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)

    reply_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.nickname}: {self.text[:30]}'
