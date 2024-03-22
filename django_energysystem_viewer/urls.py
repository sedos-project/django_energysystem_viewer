from django.urls import path

from django_energysystem_viewer import views

app_name = "django_energysystem_viewer"


urlpatterns = [
    path("energysystem/selection/", views.SelectionView.as_view(), name="selection"),
    path("energysystem/network/", views.network, name="networks"),
    path("energysystem/network_graph/", views.network_graph),
    path("energysystem/abbreviation/", views.abbreviations, name="abbreviations"),
    path("energysystem/abbreviation_meaning/", views.abbreviation_meaning),
    path("energysystem/aggregation/", views.AggregationView.as_view(), name="aggregations"),
    path("collection/processes/", views.ProcessesView.as_view(), name="processes"),
    path(
        "collection/<str:collection_name>/process/<str:process_name>/data/",
        views.ProcessDetailView.as_view(),
    ),
    path("collection/artifacts/", views.ArtifactsView.as_view(), name="artifacts"),
    path(
        "collection/<str:collection_name>/artifact/<str:group_name>/<str:artifact_name>/data/",
        views.ArtifactDetailView.as_view(),
    ),
    path(
        "collection/<str:collection_name>/artifact/<str:group_name>/<str:artifact_name>/<str:version>/data/",
        views.ArtifactDetailView.as_view(),
    ),
]
