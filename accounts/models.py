from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.text import slugify
from unidecode import unidecode
from django.urls import reverse
from timezone_field import TimeZoneField
from django.db.models import Q
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
    ]
    PRIVACY_CHOICES =[
        ('O', 'Opened'),
        ('C', 'Closed')
    ]
    # Основные поля
    email = models.EmailField(unique=True,
                              blank=False)
    nickname = models.CharField(max_length=35,
                                blank=False,
                                unique=True)
    display_nickname = models.CharField(max_length=35,
                                        blank=True)
    privacy = models.CharField(max_length=1,
                               choices=PRIVACY_CHOICES,
                               default='O',
                               blank=False)
    slug = models.SlugField(max_length=50, blank=True, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    gender = models.CharField(max_length=1,
                              choices=GENDER_CHOICES,
                              blank=True)
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
    bio = models.TextField(blank=True,
                           max_length=500,
                           default='')
    
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
    telegram = models.CharField(blank=True, max_length=32)
    
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
        
    def get_friends(self):
        """Получить всех друзей пользователя как QuerySet."""
        friend_ids = Friendship.objects.filter(
            Q(user1=self) | Q(user2=self)
        ).values_list('user1', 'user2')

        # Получаем только id друзей, исключая себя
        ids = set()
        for u1, u2 in friend_ids:
            if u1 == self.id:
                ids.add(u2)
            else:
                ids.add(u1)

        return User.objects.filter(id__in=ids).distinct()

    def send_friend_request(self, other_user):
        """Отправить запрос на дружбу."""
        if self == other_user:
            raise ValueError("Нельзя отправить запрос самому себе.")
        
        if FriendRequest.objects.filter(user_from=self, user_to=other_user, status='pending').exists():
            raise ValueError("Заявка уже отправлена.")
        
        FriendRequest.objects.create(user_from=self, user_to=other_user)

    def cancel_friend_request(self, other_user):
        """Отменить запрос на дружбу."""
        friend_request = FriendRequest.objects.filter(user_from=self, user_to=other_user, status='pending').first()
        if friend_request:
            friend_request.cancel()

    def get_background_image_url(self):
        if self.background_image:
            return self.background_image.url
        return '/static/images/default-background.jpg'  # Путь к дефолтному фону

    def __str__(self):
        return f'{self.nickname} ({self.email})'
class Friendship(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendship_set1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendship_set2')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')

    def __str__(self):
        return f'{self.user1.nickname} is friends with {self.user2.nickname}'

class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    user_from = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests')
    user_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user_from', 'user_to')

    def __str__(self):
        return f'{self.user_from.nickname} -> {self.user_to.nickname} ({self.status})'

    def accept(self):
        self.status = 'accepted'
        self.save()

        Friendship.objects.create(user1=self.user_from, user2=self.user_to)
        Friendship.objects.create(user1=self.user_to, user2=self.user_from)  # Обе записи для двусторонней дружбы
    def reject(self):
        self.status = 'rejected'
        self.save()

    def cancel(self):
        self.status = 'cancelled'
        self.save()

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    verb = models.CharField(max_length=200)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

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