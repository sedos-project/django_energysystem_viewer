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
