from django.urls import path

from django_energysystem_viewer import views

app_name = "django_energysystem_viewer"


urlpatterns = [
    path("energysystem/network/", views.NetworkView.as_view()),
    path("energysystem/network_graph/", views.network_graph),
    path("energysystem/abbreviation/", views.AbbreviationView.as_view()),
    path("energysystem/aggregation/", views.AggregationView.as_view()),
    path("energysystem/aggregation_graph/", views.aggregation_graph()),
    path("collections/", views.CollectionsView.as_view(), name="collections"),
    path("collection/<str:collection_name>/processes/", views.ProcessesView.as_view(), name="processes"),
    path(
        "collection/<str:collection_name>/process/<str:process_name>/data/",
        views.ProcessDetailView.as_view(),
    ),
    path("collection/<str:collection_name>/artifacts/", views.ArtifactsView.as_view(), name="artifacts"),
    path(
        "collection/<str:collection_name>/artifact/<str:group_name>/<str:artifact_name>/data/",
        views.ArtifactDetailView.as_view(),
    ),
    path(
        "collection/<str:collection_name>/artifact/<str:group_name>/<str:artifact_name>/<str:version>/data/",
        views.ArtifactDetailView.as_view(),
    ),
]
