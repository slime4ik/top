from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.text import slugify
from unidecode import unidecode
from django.urls import reverse
from timezone_field import TimeZoneField  # Нужно установить пакет django-timezone-field

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]
    
    # Основные поля
    email = models.EmailField(unique=True, blank=False)
    nickname = models.CharField(max_length=35, blank=False)
    slug = models.SlugField(max_length=50, blank=True, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    # Изображения
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/%d',
        default='avatars/default.jpg'
    )
    background_image = models.ImageField(
        upload_to='backgrounds/%Y/%m/%d',
        blank=True,
        null=True,
        help_text="Recommended size: 1200x400px"
    )
    
    # Описание
    bio = models.TextField(blank=True, max_length=500, default='')
    
    # Навыки (многие-ко-многим для гибкости)
    skills = models.ManyToManyField(
        'Skill',
        blank=True,
        related_name='users'
    )
    
    # Временная зона
    time_zone = TimeZoneField(
        blank=True,
        default='UTC',
        choices_display="WITH_GMT_OFFSET"
    )
    
    # Соцсети
    github = models.URLField(blank=True, max_length=255)
    vk = models.URLField(blank=True, max_length=255)
    telegram = models.CharField(blank=True, max_length=32)  # Для username без @
    
    # Статистика
    last_activity = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nickname']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)

    def generate_unique_slug(self):
        slug = slugify(unidecode(self.nickname))
        unique_slug = slug
        num = 1
        while User.objects.filter(slug=unique_slug).exists():
            unique_slug = f'{slug}-{num}'
            num += 1
        return unique_slug

    def get_absolute_url(self):
        return reverse("accounts:user_detail", args=[self.id, self.slug])
    
    def get_background_image_url(self):
        if self.background_image:
            return self.background_image.url
        return '/static/images/default-background.jpg'  # Путь к дефолтному фону

    def __str__(self):
        return f'{self.nickname} ({self.email})'


class Skill(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="fas fa-code",  # Иконка по умолчанию
        help_text="Font Awesome class name (e.g. 'fa-python')"
    )
    
    def __str__(self):
        return self.name