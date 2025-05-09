from django.urls import path, include, re_path
from .views import create, my_groups, group_detail,\
                    join_group, groups_view, promote_user,\
                    demote_user, kick_user, edit, users_list,\
                    open_groups, chat_message_history, join_group,\
                    leave_group, open_join_group

app_name = 'groups'

urlpatterns = [
    path('create/', create, name='create'),
    path('manage/', my_groups, name='manage'),
    re_path(r'^group/(?P<id>[0-9]+)/(?P<slug>[\w\-]+)/$', group_detail, name='group_detail'),
    path('join/', join_group, name='join_group'),
    path('groups/', groups_view, name='groups'),
    path('group/<int:group_id>/promote/<int:user_id>/', promote_user, name='promote_user'),
    path('group/<int:group_id>/demote/<int:user_id>/', demote_user, name='demote_user'),
    path('group/<int:group_id>/kick/<int:user_id>/', kick_user, name='kick_user'),
    path('edit/<int:id>/', edit, name='group_edit'),
    path('groups/<int:id>/<slug:slug>/users/', users_list, name='users_list'),
    path('opengroups/', open_groups, name='open_groups'),
    path('api/chat/<int:group_id>/messages/', chat_message_history, name='chat_message_history'),
    path('group/<int:group_id>/<slug:group_slug>/join/', open_join_group, name='open_join_group'),
    path('<int:group_id>/<slug:group_slug>/leave/', leave_group, name='leave_group'),
]
