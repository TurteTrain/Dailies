from django.contrib import admin
from django.urls import path
from dailies import views

from dailies import api, views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/csrf", api.csrf),
    path("api/register", api.register),
    path("api/login", api.login_view),
    path("api/logout", api.logout_view),
    path("api/me", api.me),
    path("api/listens", api.my_listens),
    path("api/admin/users", api.admin_users),
    path("spotify/login", views.login),     # "Connect Spotify" button
    path("callback", views.callback),       # unchanged path, so your redirect URI stays valid
]
