from django.db import models
from django.conf import settings
from django.utils import timezone

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ProgressMixin(models.Model):
    STATUS_WAITING = 'waiting'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'

    STATUS_CHOICES = [
        (STATUS_WAITING, 'Waiting'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_DONE, 'Done'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_WAITING,
        db_index=True  # индекс на статус для быстрого фильтра
    )

    class Meta:
        abstract = True

    def is_done(self):
        return self.status == self.STATUS_DONE


class Task(TimeStampedModel, ProgressMixin):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tasks'
    )
    title = models.CharField(max_length=100)
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    user = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assigned_tasks',
        blank=True
    )
    description = models.TextField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    dead_line = models.DateTimeField(editable=True, blank=True, null=True)
    class Meta:
        ordering = ['dead_line']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['group']),
        ]
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'

    @property
    def has_subtasks(self):
        return self.subtasks.count() < 1

    def can_be_deleted_by(self, user):
        return (
            user == self.group.creator or
            user in self.group.admins.all()
        )
    # def is_past_deadline(self):
    #     return self.dead_line < timezone.now()
    
    def update_status_from_users(self):
        if self.user.exists():
            self.status = self.STATUS_IN_PROGRESS
        else:
            self.status = self.STATUS_WAITING
        self.save(update_fields=['status'])

    def update_status_from_subtasks(self):
        subtasks = self.subtasks.only('status')

        if not subtasks.exists():
            return

        if all(s.status == self.STATUS_DONE for s in subtasks):
            new_status = self.STATUS_DONE
        elif any(s.status == self.STATUS_IN_PROGRESS for s in subtasks):
            new_status = self.STATUS_IN_PROGRESS
        else:
            new_status = self.STATUS_WAITING

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])
        def save(self, *args, **kwargs):
            if self.is_past_deadline():
                raise ValueError("Невозможно изменить задачу после дедлайна!")
            super().save(*args, **kwargs)

class TaskFile(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='task_files/')

    def __str__(self):
        return self.file.name


class SubTask(TimeStampedModel, ProgressMixin):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='creator'
    )
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='subtasks')
    user = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                  blank=True,
                                  related_name='subtasks')
    title = models.CharField(max_length=355)
    
    def sub_can_be_deleted_by(self, user):
        return (
            user == self.task.group.creator or
            user in self.task.group.admins.all()
        )

    def update_status_from_users(self):
        if self.user.exists():
            new_status = self.STATUS_IN_PROGRESS
        else:
            new_status = self.STATUS_WAITING

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.task.user.exists():
            self.task.user.add()
        self.task.update_status_from_subtasks()


class SubTaskFile(models.Model):
    subtask = models.ForeignKey(SubTask, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='subtask_files/')

    def __str__(self):
        return self.file.name


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(max_length=1000)
    image = models.ImageField(upload_to='comment_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.nickname}: {self.text[:30]}"
