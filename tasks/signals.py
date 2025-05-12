from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import SubTask
from .services import update_task_status_from_subtasks

User = get_user_model()

@receiver(m2m_changed, sender=SubTask.user.through)
def on_subtask_user_changed(sender, instance, action, pk_set, **kwargs):
    instance.update_status_from_users()
    update_task_status_from_subtasks(instance.task)

    task = instance.task
    if action == 'post_add':
        for user_id in pk_set:
            if not task.user.filter(pk=user_id).exists():
                task.user.add(user_id)
    elif action == 'post_remove':
        for user_id in pk_set:
            user_subtasks = SubTask.objects.filter(task=task, user__id=user_id)
            if not user_subtasks.exists():
                task.user.remove(user_id)
