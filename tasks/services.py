from .models import Task, SubTask

def update_task_status_from_subtasks(task: Task):
    """
    Обновляет статус задачи на основе её подзадач.
    """
    subtasks = task.subtasks.only('status')

    if not subtasks.exists():
        return

    if all(s.status == SubTask.STATUS_DONE for s in subtasks):
        task.status = Task.STATUS_DONE
    elif any(s.status == SubTask.STATUS_IN_PROGRESS for s in subtasks):
        task.status = Task.STATUS_IN_PROGRESS
    else:
        task.status = Task.STATUS_WAITING

    task.save(update_fields=['status'])
