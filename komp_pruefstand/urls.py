from django.contrib import admin
from django.urls import path
from komp_pruefstand.views import *
from . import views

urlpatterns = [
    path("", views.komp_pruefstand),
    path("konfig/", views.konfig),
    path("manu/", views.manu),
    path("konfig/drop_konfig/", views.drop_konfig),
    path("manu/drop_konfig/", views.drop_konfig),
]
