import pandas as pd

from data_adapter import collection, preprocessing, settings
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from django_energysystem_viewer import network_graph as ng


class NetworkView(TemplateView):
    template_name = "django_energysystem_viewer/network.html"


def network_graph(request):
    sectors = request.GET.getlist("sectors")
    mapping = request.GET["mapping"]
    return HttpResponse(ng.generate_Graph(sectors, mapping).to_html())


def get_abbreviation_input():
    abbreviations = pd.read_excel(settings.MEDIA_ROOT + "/" + settings.MODEL_STRUCTURE_FILE, "Abbreviations")
    return abbreviations


def abbreviations(request):
    abbreviations = get_abbreviation_input()
    abbreviation_list = abbreviations["abbreviations"].unique()
    return render(request, "django_energysystem_viewer/abbreviation.html", {"abbreviation_list": abbreviation_list})


def abbreviation_meaning(request):
    abb = request.GET.get("abbreviation")
    abbreviations = get_abbreviation_input()
    if abb:
        meaning = abbreviations[abbreviations["abbreviations"] == abb]["meaning"].values
        if len(meaning) > 0:
            return HttpResponse(meaning)
        else:
            return HttpResponse(["Abbreviation not found"])
    else:
        return HttpResponse("")
    

class AggregationView(TemplateView):
    template_name = "django_energysystem_viewer/aggregation.html"


def aggregation_graph(request):
    return "oi"


class CollectionsView(TemplateView):
    template_name = "django_energysystem_viewer/collections.html"

    def get_context_data(self, **kwargs):
        return {"collections": [file.name for file in settings.COLLECTIONS_DIR.iterdir() if file.is_dir()]}


class ProcessDetailMixin:
    def get_context_data(self, **kwargs):
        process_name = kwargs.get("process_name", self.request.GET.get("process"))
        if not process_name:
            return {}

        collection_name = kwargs["collection_name"]
        process = preprocessing.get_process(collection_name, process_name)
        artifacts = collection.get_artifacts_from_collection(collection_name, process_name)
        return {
            "collection_name": collection_name,
            "artifacts": artifacts,
            "scalars": process.scalars.to_html(),
            "timeseries": process.timeseries.to_html(),
        }


class ProcessesView(ProcessDetailMixin, TemplateView):
    template_name = "django_energysystem_viewer/processes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        collection_name = kwargs["collection_name"]
        processes = collection.get_processes_from_collection(collection_name)
        context["processes"] = processes
        return context


class ProcessDetailView(ProcessDetailMixin, TemplateView):
    template_name = "django_energysystem_viewer/process_detail.html"


class ArtifactsView(TemplateView):
    template_name = "django_energysystem_viewer/artifacts.html"

    def get_context_data(self, **kwargs):
        collection_name = kwargs["collection_name"]
        artifacts = collection.get_artifacts_from_collection(collection_name)
        context = {"collection_name": collection_name, "artifacts": artifacts}

        # If specific artifact is queried
        artifact_name = self.request.GET.get("artifact")
        group_name = self.request.GET.get("group")
        version = self.request.GET.get("version")
        if artifact_name and group_name:
            artifact = collection.get_artifact_from_collection(collection_name, group_name, artifact_name, version)
            context["processes"] = collection.get_collection_meta(collection_name)["artifacts"][group_name][
                artifact_name
            ]["names"]
            context["data"] = artifact.data.to_html()
            metadataWidget = JsonWidget(artifact.metadata)
            context["metadata"] = metadataWidget.render()
        return context


class ArtifactDetailView(TemplateView):
    template_name = "django_energysystem_viewer/artifact_detail.html"

    def get_context_data(self, **kwargs):
        collection_name = kwargs["collection_name"]
        group_name = kwargs["group_name"]
        artifact_name = kwargs["artifact_name"]
        version = kwargs.get("version")
        artifact = collection.get_artifact_from_collection(collection_name, group_name, artifact_name, version)
        metadataWidget = JsonWidget(artifact.metadata)
        return {
            "collection_name": collection_name,
            "processes": collection.get_collection_meta(collection_name)["artifacts"][group_name][artifact_name][
                "names"
            ],
            "data": artifact.data.to_html(),
            "metadata": metadataWidget.render(),
        }
    
class JsonWidget:
    """
    render JSON data into HTML with indention depending on the level of nesting

    Methods
    ----------
    __init(json: dict)
         Initializes the JsonWidget object with the provided JSON data (dict).
    __convert_to_html(data, level=0)
        Converts the JSON data to HTML format, with indention depending on the level, starting at 0.
    render()
        Necessary for rendering the html structure in the django template.
    """
    def __init__(self, json: dict):
        self.json = json

    def __convert_to_html(self, data, level=0):
        html = ""
        if isinstance(data, dict):
            html += (
                f'<div style="margin-left: {level*2}rem;'
                f"margin-bottom: 0.75rem;"
                f"padding-left: 0.5rem;"
                f'border-left: 1px dotted #002E4F;">'
                if level > 0
                else "<div>"
            )
            for key, value in data.items():
                html += f"<b>{key}:</b> {self.__convert_to_html(value, level+1)}"
            html += "</div>"
        elif isinstance(data, list):
            html += f'<div style="margin-left: {level*2}rem;">'
            for item in data:
                html += f"{self.__convert_to_html(item, level+1)}"
            html += "</div>"
        else:
            html += f"{data}<br>"
        return html

    def render(self):
        header = ""
        if self.json["title"] != "":
            header += f'<p class="lead">{self.json["title"]}</p>'
        if self.json["description"] != "":
            header += f'<p>{self.json["description"]}</p>'
        return header + self.__convert_to_html(data=self.json)
