from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Skill, Notification, FriendRequest



admin.site.register(User)
admin.site.register(Skill)
admin.site.register(Notification)
admin.site.register(FriendRequest)