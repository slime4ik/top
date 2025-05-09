from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import User, Skill
import re
import pytz

MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_BACKGROUND_SIZE = 10 * 1024 * 1024  # 10 MB

class UserUpdateForm(forms.ModelForm):
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Skills')
    )
    
    telegram = forms.CharField(
        required=False,
        label='Telegram',
        help_text='Your Telegram username without @',
        widget=forms.TextInput(attrs={'placeholder': 'username'})
    )
    class Meta:
        model = User
        fields = [
            'nickname',
            'gender',
            'bio',
            'avatar',
            'background_image',
            'time_zone',
            'skills',
            'privacy',
            'github',
            'vk',
            'telegram'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'time_zone': forms.Select(),  # Здесь просто Select, choices будут добавляться в __init__
        }
        labels = {
            'background_image': _('Profile Background'),
            'time_zone': _('Time Zone'),
        }
        help_texts = {
            'github': _('Your GitHub profile URL'),
            'vk': _('Your VK profile URL'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Установка начальных умений (если объект существует)
        if self.instance.pk:
            self.fields['skills'].initial = self.instance.skills.all()

        # Установка списка временных зон
        self.fields['time_zone'].choices = [
            (tz, tz) for tz in pytz.all_timezones
        ]

    def clean_nickname(self):
        nick = self.cleaned_data.get('nickname', '').strip()
        if not nick:
            raise ValidationError(_('Nickname cannot be empty.'))
        if len(nick) < 3:
            raise ValidationError(_('Nickname must be at least 3 characters.'))
        if len(nick) > 35:
            raise ValidationError(_('Nickname must be at most 35 characters.'))
        qs = User.objects.filter(nickname__iexact=nick)
        if self.instance.pk:  # Если это редактирование, а не создание
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError(_('This nickname is already taken.'))
        return nick
    
    def clean_bio(self):
        bio = self.cleaned_data.get('bio', '').strip()
        if len(bio) > 500:
            raise ValidationError(_('Bio must be at most 500 characters.'))
        return bio

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and avatar != self.instance.avatar:
            if avatar.size > MAX_AVATAR_SIZE:
                raise ValidationError(_(f'Avatar file too large (max {MAX_AVATAR_SIZE // 1024 // 1024} MB).'))
            # Можно добавить проверку формата
            # if not avatar.name.lower().endswith(('.jpg', '.jpeg', '.png')):
            #     raise ValidationError('Only JPG/PNG images are allowed.')
        return avatar

    def clean_background_image(self):
        bg_image = self.cleaned_data.get('background_image')
        if bg_image and bg_image != self.instance.background_image:
            if bg_image.size > MAX_BACKGROUND_SIZE:
                raise ValidationError(_(f'Background image too large (max {MAX_BACKGROUND_SIZE // 1024 // 1024} MB).'))
        return bg_image

    def clean_github(self):
        github = self.cleaned_data.get('github', '').strip()
        if github:
            if not github.startswith(('https://github.com/', 'http://github.com/')):
                raise ValidationError(_('Please enter a valid GitHub profile URL.'))
        return github

    def clean_vk(self):
        vk = self.cleaned_data.get('vk', '').strip()
        if vk:
            if not re.match(r'^https?://(?:www\.)?vk\.com/', vk):
                raise ValidationError(_('Please enter a valid VK profile URL.'))
        return vk

    def clean_telegram(self):
        telegram = self.cleaned_data.get('telegram', '').strip()
        if telegram:
            if not re.match(r'^[a-zA-Z0-9_]{5,32}$', telegram):
                raise ValidationError(_('Telegram username must be 5-32 characters, alphanumeric and underscores.'))
        return telegram

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            self.save_m2m()  # Для сохранения навыков (ManyToMany)
        return user
    
class EmailForm(forms.Form):
    email = forms.EmailField(
        label='Enter your email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
            'autofocus': 'autofocus'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Здесь не проверяем на существование, только проверка валидности
        if not email:
            raise forms.ValidationError("Please enter a valid email.")
        return email


class CodeForm(forms.Form):
    code = forms.CharField(
        label='Enter code from your email',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Verification Code'
        })
    )

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if len(code) != 6:  # Предположим, код состоит из 6 символов
            raise forms.ValidationError("The code must be 6 digits long.")
        return code


class NicknameForm(forms.Form):
    nickname = forms.CharField(
        max_length=35,
        label='Enter your nickname',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a nickname'
        })
    )

    def clean_nickname(self):
        nickname = self.cleaned_data.get('nickname')
        if len(nickname) < 3:
            raise forms.ValidationError("Nickname must be at least 3 characters.")
        if User.objects.filter(nickname__iexact=nickname).exists():
            raise ValidationError(_('This nickname is already taken.'))
        return nickname