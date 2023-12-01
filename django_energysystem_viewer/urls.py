from django.urls import path

from django_energysystem_viewer import views

app_name = "django_energysystem_viewer"


urlpatterns = [
    path("energysystem/network/", views.NetworkView.as_view()),
    path("energysystem/network_graph/", views.network_graph),
    path("collection/<str:collection_name>/artifacts/", views.ArtifactsView.as_view()),
    path(
        "collection/<str:collection_name>/artifact/<str:group_name>/<str:artifact_name>/data/",
        views.ArtifactDataView.as_view(),
    ),
    path(
        "collection/<str:collection_name>/artifact/<str:group_name>/<str:artifact_name>/<str:version>/data/",
        views.ArtifactDataView.as_view(),
    ),
]
