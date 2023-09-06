from django.urls import path

from .api import api

app_name = "django_energysystem_viewer"


urlpatterns = [
    path("energysystem/", api.urls),
]
