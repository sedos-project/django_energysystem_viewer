from django.http import HttpResponse
from ninja import NinjaAPI

from django_energysystem_viewer import network_graph as ng

api = NinjaAPI(urls_namespace="energysystem_viewer")


@api.get("/network_graph")
def network_graph(request):
    return HttpResponse(ng.generate_Graph(["mob"], "umap").to_html())
