from django.contrib import admin
from .models import Group, ChatMessage

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created_at', 'code')
    search_fields = ('name', 'creator__username', 'code')
    filter_horizontal = ('admins', 'members')
    readonly_fields = ('code', 'created_at')

admin.site.register(ChatMessage)
