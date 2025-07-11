from django.shortcuts import render, redirect
from .forms import TaskForm, SubTaskForm, CommentForm
from .models import Task, TaskFile, SubTask, SubTaskFile
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from groups.models import Group  # Импортируй свою модель групп
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from groups.models import Group  # Импортируй свою модель групп
from django.urls import reverse
from django.db.models import Prefetch
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import PermissionDenied

@login_required
def create_task_view(request):
    # Проверяем, есть ли группы, где пользователь админ или создатель
    user_groups = Group.objects.filter(admins=request.user) | Group.objects.filter(creator=request.user)
    if not user_groups.exists():
        return HttpResponseForbidden(
            'U have no access to create tasks. Only admins and creators can do it. '\
            'Return to <a href="/">home</a>.'
        )

    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.creator = request.user
            task.save()
            form.save_m2m()
            # Сохраняем файл, если он есть
            if 'files' in request.FILES:
                TaskFile.objects.create(task=task, file=request.FILES['files'])

            return redirect('accounts:home')
    else:
        form = TaskForm(user=request.user)

    return render(request, 'create_task.html', {'form': form})

@login_required
def create_subtask(request, id, slug):
    task = get_object_or_404(Task, id=id, group__slug=slug)
    if request.method == 'POST' and (
        request.user == task.group.creator or 
        request.user in task.group.admins.all()
    ):

        sub_form = SubTaskForm(request.POST, request.FILES)
        if sub_form.is_valid():
            subtask = sub_form.save(commit=False)
            subtask.creator = request.user
            subtask.task = task
            subtask.save()
            sub_form.save_m2m()

            uploaded_file = request.FILES.get('files')
            if uploaded_file:
                SubTaskFile.objects.create(subtask=subtask, file=uploaded_file)

            return redirect(reverse('groups:group_detail', kwargs={
                'id': task.group.id,
                'slug': task.group.slug,
            }))
    else:
        sub_form = SubTaskForm()

    return render(request, 'task_detail.html', {
        'task': task,
        'sub_form': sub_form,
    })

@login_required
def change_task_status(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['waiting', 'in_progress', 'done']:
            task.status = new_status
            task.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def add_comment(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task       # <-- привязали к задаче
            comment.user = request.user
            comment.save()
    # после сохранения — вернёмся на страницу, откуда пришли
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def join_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.user not in task.user.all():
        task.user.add(request.user)
        task.update_status_from_users()
        messages.success(request, "You've joined the task!")
    return redirect('groups:group_detail', id=task.group.id, slug=task.group.slug)

@login_required
def leave_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.user in task.user.all():
        task.user.remove(request.user)
        if task.user.count() == 0:
            task.status = task.STATUS_WAITING
            task.save(update_fields=['status'])
        messages.success(request, "You've left the task.")
    return redirect('groups:group_detail', id=task.group.id, slug=task.group.slug)

@login_required
def change_task_status(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    
    if (request.user not in task.user.all() and 
        request.user != task.creator and 
        request.user not in task.group.admins.all()):
        raise PermissionDenied
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Task.STATUS_CHOICES).keys():
            task.status = new_status
            task.save()
            messages.success(request, "Task status updated!")
    
    return redirect('groups:group_detail', id=task.group.id, slug=task.group.slug)

@login_required
def join_subtask(request, subtask_id):
    subtask = get_object_or_404(SubTask, id=subtask_id)
    if request.user not in subtask.user.all():
        subtask.user.add(request.user)
        messages.success(request, "You've joined the subtask!")
    return redirect('groups:group_detail', id=subtask.task.group.id, slug=subtask.task.group.slug)

@login_required
def leave_subtask(request, subtask_id):
    subtask = get_object_or_404(SubTask, id=subtask_id)
    if request.user in subtask.user.all():
        subtask.user.remove(request.user)
        messages.success(request, "You've left the subtask.")
    return redirect('groups:group_detail', id=subtask.task.group.id, slug=subtask.task.group.slug)

@login_required
def change_subtask_status(request, subtask_id):
    subtask = get_object_or_404(SubTask, id=subtask_id)
    
    if (request.user not in subtask.user.all() and 
        request.user != subtask.creator and 
        request.user not in subtask.task.group.admins.all()):
        raise PermissionDenied
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(SubTask.STATUS_CHOICES).keys():
            subtask.status = new_status
            subtask.save()
            messages.success(request, "Subtask status updated!")
    
    return redirect('groups:group_detail', id=subtask.task.group.id, slug=subtask.task.group.slug)

@require_POST
@login_required
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if (
        request.user != task.creator and
        request.user not in task.group.admin.all() and
        request.user != task.group.creator
    ):
        return HttpResponseForbidden('U cant delete this task!')
    
    task.delete()
    return redirect('groups:groups')


@login_required
def delete_subtask(request, subtask_id):
    ru = request.user
    subtask = get_object_or_404(SubTask, id=subtask_id)
    task = subtask.task
    if ru == task.group.creator or ru in task.group.admins.all() or ru == subtask.creator:
        subtask.delete()
        return redirect('groups:groups')
    else:
        return HttpResponseForbidden("You do not have permission to delete this subtask.")


@login_required
def user_tasks(request):
    user = request.user

    user_tasks = (
        Task.objects
        .filter(user=user)
        .select_related('creator', 'group')
        .prefetch_related(
            'user',
            'subtasks__user',
            'subtasks__files',
            'files',
            'comments__user',
        )
        .order_by('dead_line')
    )

    context = {
        'user_tasks': user_tasks,
    }
    return render(request, 'user_tasks.html', context)
