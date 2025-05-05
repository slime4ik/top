from django.urls import path, include
from .views import login_view, home, profile_detail,\
                    profile_check
from django.contrib.auth import views as auth_views

app_name = 'accounts'

urlpatterns = [
    path('come/', login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', home, name='home'),
    path('me/', profile_detail, name='profile_edit'),
    path('<int:user_id>/<slug:user_slug>/', profile_check, name='profile_check'),
]
