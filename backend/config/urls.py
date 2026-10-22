from django.contrib import admin
from django.urls import path
from dailies import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login", views.login),
    path("callback", views.callback),
]
