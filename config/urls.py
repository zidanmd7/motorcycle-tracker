from django.contrib import admin
from django.urls import path, include

# Send garage pages to the app and keep the admin page separate.
urlpatterns = [path("admin/", admin.site.urls), path("", include("garage.urls"))]
