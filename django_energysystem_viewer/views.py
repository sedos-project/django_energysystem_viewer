import pandas as pd

from data_adapter import collection, preprocessing, settings as da_settings
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from django_energysystem_viewer import network_graph as ng


class SelectionView(TemplateView):
    template_name = "django_energysystem_viewer/selection.html"

    def get_context_data(self, **kwargs):
        return {"structure_list": [file.name for file in da_settings.STRUCTURES_DIR.iterdir() 
                                   if not file.name.startswith('.') or file.name.endswith(('.xls', '.xlsx'))],
                "collection_list": [file.name for file in da_settings.COLLECTIONS_DIR.iterdir() if file.is_dir()]}
    

def get_excel_data(file: str, sheet: str):
    data = pd.read_excel(str(da_settings.STRUCTURES_DIR / file), sheet)
    return data


def network(request):
    file_name = request.GET.get("structures")
    process_set = get_excel_data(file_name, "Process_Set")
    unique_processes = process_set["process"].unique()

    # get the inputs and outputs of the filtered process set
    sector_commodities = (
        process_set["input"].tolist()
        + process_set["output"].tolist()
    )

    # clean the list of commodities from "[", "]", "nan" and " ", as well as split at ","
    sector_commodities = [
        str(item)
        .replace("[", "")
        .replace("]", "")
        .replace(" ", "")
        .replace("nan", "")
        for item in sector_commodities
    ]
    sector_commodities = [item.split(",") for item in sector_commodities]

    # get rid of duplicates
    unique_commodities = []
    for commodity in sector_commodities:
        for item in commodity:
            if item not in unique_commodities:
                unique_commodities.append(item)

    # remove empty strings
    unique_commodities = [item for item in unique_commodities if item]

    # sort unique commodities alphabetically
    unique_commodities.sort()
    return render(request, "django_energysystem_viewer/network.html", {"unique_processes": unique_processes, "unique_commodities": unique_commodities, "data": file_name})


def network_graph(request):
    sectors = request.GET.getlist("sectors")
    mapping = request.GET["mapping"]
    sep_agg = request.GET.get("seperate_join")
    process = request.GET.get("process")
    commodity = request.GET.get("commodity")
    return HttpResponse(ng.generate_Graph(sectors, mapping, sep_agg, process, commodity).to_html())


def abbreviations(request):
    file_name = request.GET.get("structures")
    abbreviations = get_excel_data(file_name, "Abbreviations")
    abbreviation_list = abbreviations["abbreviations"].unique()
    return render(request, "django_energysystem_viewer/abbreviation.html", {"abbreviation_list": abbreviation_list, 
                                                                            "data": file_name})


def abbreviation_meaning(request):
    abb = request.GET.get("abbreviation")
    file_name = request.GET.get("structure")
    abbreviations = get_excel_data(file_name, "Abbreviations")
    if abb:
        meaning = abbreviations[abbreviations["abbreviations"] == abb]["meaning"].values
        if len(meaning) > 0:
            return HttpResponse("Meaning: " + meaning)
        else:
            return HttpResponse(["Abbreviation not found"])
    else:
        return HttpResponse("")
    

class AggregationView(TemplateView):
    template_name = "django_energysystem_viewer/aggregation.html"

    def get_context_data(self, **kwargs):
        file_name = self.request.GET.get("structures")
        return {"data": file_name}


def aggregation_graph(request):
    return "oi"


class CollectionsView(TemplateView):
    template_name = "django_energysystem_viewer/collections.html"

    def get_context_data(self, **kwargs):
        return {"collections": [file.name for file in da_settings.COLLECTIONS_DIR.iterdir() if file.is_dir()]}


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
