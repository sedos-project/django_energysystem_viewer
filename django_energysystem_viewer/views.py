from django.http import HttpResponse
from django.views.generic import TemplateView
from django.conf import settings
from django.shortcuts import render

from django_energysystem_viewer import network_graph as ng

from django_energysystem_viewer import aggregation_graph as ag


class NetworkView(TemplateView):
    template_name = "django_energysystem_viewer/network.html"


def network_graph(request):
    sectors = request.GET.getlist("sectors")
    mapping = request.GET["mapping"]
    return HttpResponse(ng.generate_Graph(sectors, mapping).to_html())


def aggregation_graph(request):
    file = settings.MEDIA_ROOT + "/" + settings.MODEL_STRUCTURE_FILE
    level_of_detail = 1
    nodes, edges = ag.generate_elements(file, level_of_detail)
    return render(request, "django_energysystem_viewer/aggregation.html", {"nodes": nodes, "edges": edges})
