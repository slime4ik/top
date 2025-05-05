from django.urls import path
from tasks import views

app_name = 'tasks'

urlpatterns = [
    path('create/', views.create_task_view, name='create_task'),
    path('<int:id>/<slug:slug>/', views.create_subtask, name='task_detail'),
    path(
        'change_status/<int:task_id>/',
        views.change_task_status,
        name='change_task_status'
    ),
    path(
        'change_subtask_status/<int:subtask_id>/',
        views.change_subtask_status,
        name='change_subtask_status'
    ),
    path(
        'add_comment/<int:task_id>/',
        views.add_comment,
        name='add_comment'
    ),
    path('join_task/<int:task_id>/', views.join_task, name='join_task'),
    path('leave_task/<int:task_id>/', views.leave_task, name='leave_task'),
    path('join_subtask/<int:subtask_id>/', views.join_subtask, name='join_subtask'),
    path('leave_subtask/<int:subtask_id>/', views.leave_subtask, name='leave_subtask'),
    path('mytasks/', views.user_tasks, name = 'user_tasks')
]
