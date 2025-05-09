from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from .models import Group
from .forms import GroupCreateForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import JoinGroupForm
from django.db.models import Q
from django.conf import settings
from accounts.models import User
from actions.models import Action
from django.urls import reverse
from django.core.paginator import Paginator
from tasks.forms import CommentForm
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChatMessage
from .serializers import ChatMessageSerializer
from django.utils import timezone

@login_required
def groups_view(request):
    user = request.user
    groups = Group.objects.filter(
        Q(creator=user) | Q(admins=user) | Q(members=user)
    ).distinct()
    context = {
        'groups': groups
    }
    return render(request, 'groups.html', context)

@login_required
def join_group(request):
    if request.method == 'POST':
        form = JoinGroupForm(request.POST)
        if form.is_valid():
            group = form.cleaned_data['group']
            user = request.user
            if user in group.members.all() or user in group.admins.all() or user == group.creator:
                messages.info(request, f'You are already a member of “{group.name}”.')
            else:
                group.members.add(user)
                messages.success(request, f'You have joined the group “{group.name}”!')
                action = Action.objects.create(
                    user=user,
                    group=group,
                    verb=f'{user.nickname} joined the group welcome!',
                )

            return redirect('groups:group_detail', id=group.id, slug=group.slug)
    else:
        form = JoinGroupForm()

    return render(request, 'join_group.html', {'form': form})

@login_required
def create(request):
    if request.method == 'POST':
        form = GroupCreateForm(request.POST, request.FILES)
        if form.is_valid():
            new_group = form.save(commit=False)
            new_group.creator = request.user
            new_group.save()
            form.save_m2m()
            messages.success(request,
                             'Group created successfully ^_^')
            return redirect('groups:manage')
    else:
        form = GroupCreateForm()

    return render(request,
                  'create.html',
                  {'form': form})
@login_required
def edit(request, id):
    group = get_object_or_404(Group, id=id)

    # Проверка, является ли пользователь администратором или создателем группы
    if request.user not in group.admins.all() and request.user != group.creator:
        return HttpResponseForbidden("You do not have permission to edit this group.")

    # Если запрос POST, обработка формы
    if request.method == 'POST':
        group_form = GroupCreateForm(request.POST, request.FILES, instance=group)
        if group_form.is_valid():
            group_form.save()
            return redirect('groups:groups')  # или redirect('groups:group_detail', id=group.id)
    else:
        # Если GET запрос, отображаем форму с данными группы
        group_form = GroupCreateForm(instance=group)

    # Контекст для шаблона
    context = {
        'group_form': group_form,
        'group': group,
    }

    return render(request, 'edit.html', context)

@login_required
def my_groups(request):
    current_user = request.user
    my_groups = Group.objects.filter(creator=current_user)
    total = my_groups.count()
    context = {'groups': my_groups,
               'total': total}
    return render(request,
                  'my_groups.html',
                  context)


@login_required
def group_detail(request, id, slug):
    group = (
        Group.objects
        .prefetch_related('members', 'admins')  # избежим N+1 на проверку доступа
        .select_related('creator')              # избежим лишнего запроса к создателю
        .get(id=id, slug=slug)
    )

    ru = request.user
    is_member = ru in group.members.all()
    is_admin = ru in group.admins.all()

    if not (is_member or is_admin or ru == group.creator) and group.status == 'C':
        return HttpResponseForbidden("U cant interact with this group")
    elif not (is_member or is_admin or ru == group.creator):
        return render(request, 'group_preview.html', {'group': group})

    # Оптимизируем подгрузку задач
    tasks_list = (
        group.tasks
        .select_related('creator', 'group')
        .prefetch_related(
            'user',                # M2M пользователей
            'files',              # файлы задачи
            'subtasks__user',     # пользователи подзадач
            'subtasks__files',    # файлы подзадач
            'comments__user',     # комментарии + авторы
        )
        .all()
    )

    paginator = Paginator(tasks_list, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Последние действия (оптимизация зависит от Action модели)
    actions = (
        Action.objects
        .filter(group=group)
        .select_related('user', 'group')  # если есть ForeignKey к user
        [:7]
    )

    comment_form = CommentForm()

    context = {
        'now': timezone.now(),
        'comment_form': comment_form,
        'group': group,
        'actions': actions,
        'page_obj': page_obj,
    }

    return render(request, 'detail.html', context)
@login_required
def users_list(request, id, slug):
    group = get_object_or_404(Group, id=id, slug=slug)
    creator = group.creator  # если OneToOneField или ForeignKey
    admins = group.admins.all()
    members = group.members.all()

    context = {
        'group': group,
        'creator': creator,
        'admins': admins,
        'members': members,
    }
    return render(request, 'users_list.html', context)

@login_required
def open_groups(request):
    groups = Group.objects.filter(status='O')
    paginator = Paginator(groups, 12)  # по 12 групп на страницу
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'open_groups.html', {
        'page_obj': page_obj,
    })

#ВСЕ ЧТО НИЖЕ ЭТО УПРАВЛЕНИЕ УЧАСТНИКАМИ ГРУППЫ
@login_required
def promote_user(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id)
    user = get_object_or_404(User, id=user_id)

    # Проверка прав
    if request.user != group.creator and request.user not in group.admins.all():
        messages.error(request, "You do not have permission to promote users.")
        return redirect(group.get_absolute_url())

    # Нельзя изменить роль создателя
    if user == group.creator:
        messages.warning(request, "You cannot change the role of the group creator.")
        return redirect(group.get_absolute_url())

    # Перемещаем пользователя из members в admins
    if user in group.members.all():
        group.members.remove(user)
        group.admins.add(user)
        messages.success(request, f"{user.nickname} has been promoted to admin.")
        action = Action.objects.create(
                    user=request.user,
                    group=group,
                    verb=f'{user.nickname} was promoted to admin by {request.user.nickname}'
                )
    elif user in group.admins.all():
        messages.info(request, f"{user.nickname} is already an admin.")
    else:
        messages.warning(request, f"{user.nickname} is not a member of the group.")

    return redirect(reverse('groups:users_list', kwargs={'id': group.id, 'slug': group.slug}))


@login_required
def demote_user(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id)
    user = get_object_or_404(User, id=user_id)

    if request.user != group.creator and request.user not in group.admins.all():
        messages.error(request, "You do not have permission to demote users.")
        return redirect(group.get_absolute_url())

    if user == group.creator:
        messages.warning(request, "You cannot change the role of the group creator.")
        return redirect(group.get_absolute_url())

    # Перемещаем пользователя из admins в members
    if user in group.admins.all():
        group.admins.remove(user)
        group.members.add(user)
        messages.success(request, f"{user.nickname} has been demoted to member.")
        action = Action.objects.create(
                    user=request.user,
                    group=group,
                    verb=f'{user.nickname} was demoted to member by {request.user.nickname}'
                )
    elif user in group.members.all():
        messages.info(request, f"{user.nickname} is already a member.")
    else:
        messages.warning(request, f"{user.nickname} is not in the group.")

    return redirect(reverse('groups:users_list', kwargs={'id': group.id, 'slug': group.slug}))


@login_required
def kick_user(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id)
    user = get_object_or_404(User, id=user_id)

    if request.user != group.creator and request.user not in group.admins.all():
        messages.error(request, "You do not have permission to kick users.")
        return redirect(group.get_absolute_url())

    if user == group.creator:
        messages.warning(request, "You cannot kick the group creator.")
        return redirect(group.get_absolute_url())

    # Удаляем из всех ролей
    was_member = False
    if user in group.members.all():
        group.members.remove(user)
        was_member = True
    if user in group.admins.all():
        group.admins.remove(user)
        was_member = True

    if was_member:
        messages.success(request, f"{user.nickname} has been kicked from the group.")
        action = Action.objects.create(
                    user=request.user,
                    group=group,
                    verb=f'{user.nickname} was kicked by {request.user.nickname}'
                )
    else:
        messages.info(request, f"{user.nickname} is not a member of the group.")

    return redirect(reverse('groups:users_list', kwargs={'id': group.id, 'slug': group.slug}))

@login_required
def open_join_group(request, group_id, group_slug):
    group = get_object_or_404(Group, id=group_id, slug=group_slug)

    # Проверка, является ли пользователь уже участником группы
    if request.user in group.members.all():
        messages.info(request, "You are already a member of this group.")
        return redirect('groups:group_detail', id=group.id, slug=group.slug)

    # Добавление пользователя в группу как участника
    group.members.add(request.user)
    messages.success(request, f"You have successfully joined the group {group.name}!")
    action = Action.objects.create(
                    user=request.user,
                    group=group,
                    verb=f'{request.user.nickname} joined our group, wellcome!'
                )
    # Перенаправление на страницу группы 
    return redirect('groups:group_detail', id=group.id, slug=group.slug)

@login_required
def leave_group(request, group_id, group_slug):
    group = get_object_or_404(Group, id=group_id, slug=group_slug)

    # Creator не может выйти из группы
    if request.user == group.creator:
        messages.warning(request, "The group creator cannot leave the group.")
        return redirect('groups:group_detail', id=group.id, slug=group.slug)

    # Если пользователь не состоит в группе
    if request.user not in group.members.all() and request.user not in group.admins.all():
        messages.warning(request, "You are not a member of this group.")
        return redirect('groups:group_detail', id=group.id, slug=group.slug)

    # Удаляем пользователя из админов, если он там
    if request.user in group.admins.all():
        group.admins.remove(request.user)
        action = Action.objects.create(
                    user=request.user,
                    group=group,
                    verb=f'{request.user.nickname} left our group, bye:`('
                )
    # Удаляем пользователя из участников, если он там
    if request.user in group.members.all():
        group.members.remove(request.user)
        action = Action.objects.create(
                    user=request.user,
                    group=group,
                    verb=f'{request.user.nickname} left our group, bye:`('
                )

    messages.success(request, f"You have successfully left the group {group.name}.")
    return redirect('groups:group_detail', id=group.id, slug=group.slug)


#API

@api_view(['GET'])
def chat_message_history(request, group_id):
    # Проверяем, что пользователь состоит в группе
    group = get_object_or_404(Group, id=group_id)
    user = request.user
    
    if not (user == group.creator or user in group.admins.all() or user in group.members.all()):
        return Response({'error': 'Access denied'}, status=403)
    
    limit = int(request.GET.get('limit', 100))
    messages = ChatMessage.objects.filter(group=group).order_by('-created_at')[:limit]
    serializer = ChatMessageSerializer(messages, many=True)
    return Response(serializer.data[::-1])  # Переворачиваем, чтобы новые были внизу

