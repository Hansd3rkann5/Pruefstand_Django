from django.contrib import admin
from django.urls import path
from komp_pruefstand.views import *
from . import views

urlpatterns = [
    path("", views.komp_pruefstand),
    path("download", views.download_file, name="download" ),
]
