from django.urls import path, include
from .views import login_view, home, profile_detail,\
                    profile_check, notification_list_view,\
                    accept_friend_request, reject_friend_request,\
                    friend_list, remove_friend
from django.contrib.auth import views as auth_views

app_name = 'accounts'

urlpatterns = [
    path('come/', login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', home, name='home'),
    path('me/', profile_detail, name='profile_edit'),
    path('<int:user_id>/<slug:user_slug>/', profile_check, name='profile_check'),
    path('notifications/', notification_list_view, name='notifications'),
    path('friend-request/accept/<int:request_id>/', accept_friend_request, name='accept_friend_request'),
    path('friend-request/reject/<int:request_id>/', reject_friend_request, name='reject_friend_request'),
    path('friends/', friend_list, name='friend_list'),
    path('friends/remove/<int:friend_id>/', remove_friend, name='remove_friend'),
]
