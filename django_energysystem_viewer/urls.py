from django.urls import path

from django_energysystem_viewer import views
from django_energysystem_viewer.api import api

app_name = "django_energysystem_viewer"


urlpatterns = [
    path("energysystem/", api.urls),
    path("energysystem/network/", views.NetworkView.as_view()),
]
