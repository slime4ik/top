from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Skill



admin.site.register(User)
admin.site.register(Skill)
