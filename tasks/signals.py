from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from .models import SubTask
from .services import update_task_status_from_subtasks

@receiver(post_save, sender=SubTask)
def on_subtask_saved(sender, instance, **kwargs):
    update_task_status_from_subtasks(instance.task)

@receiver(m2m_changed, sender=SubTask.user.through)
def on_subtask_user_changed(sender, instance, **kwargs):
    instance.update_status_from_users()
    update_task_status_from_subtasks(instance.task)
