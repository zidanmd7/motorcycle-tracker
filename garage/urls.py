from django.urls import path
from . import views

# Connect each page address to the function that handles it.
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("<str:kind>/new/", views.edit, name="add"),
    path("<str:kind>/<int:pk>/edit/", views.edit, name="edit"),
    path("<str:kind>/<int:pk>/delete/", views.delete, name="delete"),
]
