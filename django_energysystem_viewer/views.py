import json2table
from data_adapter import collection
from django.http import HttpResponse
from django.views.generic import TemplateView

from django_energysystem_viewer import network_graph as ng


class NetworkView(TemplateView):
    template_name = "django_energysystem_viewer/network.html"


def network_graph(request):
    sectors = request.GET.getlist("sectors")
    mapping = request.GET["mapping"]
    return HttpResponse(ng.generate_Graph(sectors, mapping).to_html())


class ArtifactsView(TemplateView):
    template_name = "django_energysystem_viewer/artifacts.html"

    def get_context_data(self, **kwargs):
        collection_name = kwargs["collection_name"]
        artifacts = collection.get_artifacts_from_collection(collection_name)
        return {"collection_name": collection_name, "artifacts": artifacts}


class ArtifactDataView(TemplateView):
    template_name = "django_energysystem_viewer/artifact_data.html"

    def get_context_data(self, **kwargs):
        collection_name = kwargs["collection_name"]
        group_name = kwargs["group_name"]
        artifact_name = kwargs["artifact_name"]
        version = kwargs.get("version")
        artifact = collection.get_artifact_from_collection(collection_name, group_name, artifact_name, version)
        return {"data": artifact.data.to_html(), "metadata": json2table.convert(artifact.metadata)}
