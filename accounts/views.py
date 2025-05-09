from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login
from django.core.cache import cache
from .forms import EmailForm, CodeForm, NicknameForm, UserUpdateForm
from .models import User, Notification, FriendRequest, Friendship
from django.contrib import messages
from django.db.models import Q
from config.utils.auth import (
    generate_code, save_code_to_redis, check_code_in_redis,
    send_login_code_task, code_already_exists
)

MAX_ATTEMPTS = 3
BAN_DURATION = 600  # 10 минут


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


@login_required
def home(request):
    user = request.user
    context = {
        'user': user
    }
    return render(request, 'about.html', context)


def login_view(request):
    step = request.session.get('step', 'email')
    email = request.session.get('login_email')

    email_form = EmailForm()
    code_form = CodeForm()
    nickname_form = NicknameForm()
    ip = get_client_ip(request)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        # === Шаг 1: Email ===
        if form_type == 'email_form':
            email_form = EmailForm(request.POST)
            if email_form.is_valid():
                email = email_form.cleaned_data['email']
                request.session['login_email'] = email

                # Блокировки по IP и email
                cache.set(f'cooldown:ip:{ip}', True, timeout=60)
                cache.set(f'cooldown:email:{email}', True, timeout=60)

                # Создаём и отправляем код только если его ещё нет
                if not code_already_exists(email):
                    code = generate_code()
                    print(code)
                    save_code_to_redis(email, code)
                    send_login_code_task.delay(email, code)

                # Переходим к проверке кода или никнейму
                exists = User.objects.filter(email=email).exists()
                request.session['step'] = 'code_only' if exists else 'code_and_nickname'
                return redirect('accounts:login')

        # === Шаг 2: Проверка кода ===
        elif form_type == 'code_form':
            code_form = CodeForm(request.POST)
            if code_form.is_valid():
                code = code_form.cleaned_data['code']
                attempts_key = f'code_attempts:{ip}'
                ban_key = f'code_ban:{ip}'

                # Если в бане — говорим сколько осталось
                if cache.get(ban_key):
                    ttl = cache.ttl(ban_key)
                    m, s = divmod(ttl or 0, 60)
                    code_form.add_error(None, f'Слишком много попыток. Повторите через {m}м {s}с.')
                # Если код верный — логиним
                elif check_code_in_redis(email, code):
                    cache.delete(attempts_key)
                    cache.delete(ban_key)

                    if request.session['step'] == 'code_only':
                        user = User.objects.get(email=email)
                        auth_login(request, user)
                        # очищаем временные ключи, но НЕ сбрасываем сессию
                        request.session.pop('login_email', None)
                        request.session.pop('step', None)
                        return redirect('accounts:home')
                    else:
                        request.session['step'] = 'nickname'
                        return redirect('accounts:login')
                # Если код неверный — считаем попытки
                else:
                    attempts = cache.get(attempts_key, 0) + 1
                    cache.set(attempts_key, attempts, timeout=BAN_DURATION)
                    if attempts >= MAX_ATTEMPTS:
                        cache.set(ban_key, True, timeout=BAN_DURATION)
                        code_form.add_error(None, 'Превышено количество попыток. Блокировка на 10 минут.')
                    else:
                        code_form.add_error(None, 'Неверный код')

        # === Шаг 3: Никнейм ===
        elif form_type == 'nickname_form':
            nickname_form = NicknameForm(request.POST)
            if nickname_form.is_valid():
                nickname = nickname_form.cleaned_data['nickname']
                user, _ = User.objects.get_or_create(email=email)
                user.nickname = nickname
                user.save()

                auth_login(request, user)
                request.session.pop('login_email', None)
                request.session.pop('step', None)
                return redirect('accounts:home')

    return render(request, 'login.html', {
        'step': step,
        'email_form': email_form,
        'code_form': code_form,
        'nickname_form': nickname_form,
    })
@login_required
def friend_list(request):
    friends = request.user.get_friends()
    context = {
        'friends': friends
    }
    return render(request, 'friend_list.html', context)

@require_POST
@login_required
def remove_friend(request, friend_id):
    friend = get_object_or_404(User, id=friend_id)
    
    # Remove friendship both ways
    Friendship.objects.filter(
        (Q(user1=request.user) & Q(user2=friend)) |
        (Q(user1=friend) & Q(user2=request.user))
    ).delete()
    
    messages.success(request, f'You have removed {friend.nickname} from your friends')
    return redirect('accounts:friend_list')

@login_required
def notification_list_view(request):
    friend_requests = FriendRequest.objects.select_related('user_from', 'user_to') \
                                           .filter(user_to=request.user, status='pending')

    notifications = Notification.objects.select_related('user') \
                                        .filter(user=request.user) \
                                        .order_by('-id')
    # Помечаем все уведы прочитаными
    notifications.filter(read=False).update(read=True)
    context = {
        'friend_requests': friend_requests,
        'notifications': notifications,
    }
    return render(request, 'notifications.html', context)

@require_POST
@login_required
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, user_to=request.user)
    friend_request.accept()
    return redirect('accounts:notifications')

@require_POST
@login_required
def reject_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, user_to=request.user)
    friend_request.reject()
    return redirect('accounts:notifications')

@login_required
def profile_detail(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request,
                             'Profile updated')
            return redirect('accounts:home')  # или куда ты хочешь
        else:
            messages.warning(request,
                             'U did smth wrong')
    else:
        form = UserUpdateForm(instance=request.user)

    context = {
        'form': form
    }
    return render(request, 'profile_detail.html', context)


@login_required
def profile_check(request, user_id, user_slug):
    profile_user = get_object_or_404(User, id=user_id, slug=user_slug)

    if request.method == 'POST':
        try:
            request.user.send_friend_request(profile_user)
            messages.success(request, 'Заявка в друзья отправлена.')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('accounts:profile_check', user_id=profile_user.id, user_slug=profile_user.slug)

    is_friend = request.user.is_authenticated and request.user in profile_user.get_friends()
    
    context = {
        'profile_user': profile_user,
        'is_friend': is_friend,
    }
    return render(request, 'profile_check.html', context)

