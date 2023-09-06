from ninja import NinjaAPI

from django_energysystem_viewer import network_graph

api = NinjaAPI()


@api.get("/network")
def hello(request):
    return network_graph.generate_Graph(["mob"], "umap").to_html()
