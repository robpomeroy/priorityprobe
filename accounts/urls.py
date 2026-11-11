from django.urls import path
from django.contrib.auth import views as auth_views
from accounts import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("settings/", views.settings_view, name="settings"),
    path("delete-account/", views.delete_account_view, name="delete_account"),
]
