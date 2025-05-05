from django.contrib import admin
from .models import Task, SubTask, TaskFile, SubTaskFile, Comment

class TaskFileInline(admin.TabularInline):
    model = TaskFile
    extra = 1

class SubTaskFileInline(admin.TabularInline):
    model = SubTaskFile
    extra = 1

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'group', 'status', 'created_at', 'updated_at', 'dead_line')
    list_filter = ('status', 'group', 'dead_line')
    search_fields = ('title', 'creator__username', 'description', 'dead_line')
    inlines = [TaskFileInline, CommentInline]

@admin.register(SubTask)
class SubTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'task', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'task')
    search_fields = ('title', 'task__title')
    inlines = [SubTaskFileInline]

@admin.register(TaskFile)
class TaskFileAdmin(admin.ModelAdmin):
    list_display = ('task', 'file')
    search_fields = ('task__title',)

@admin.register(SubTaskFile)
class SubTaskFileAdmin(admin.ModelAdmin):
    list_display = ('subtask', 'file')
    search_fields = ('subtask__title',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'created_at', 'text')
    search_fields = ('user__username', 'task__title', 'text')
