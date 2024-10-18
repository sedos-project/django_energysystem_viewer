import io

import pandas as pd
from data_adapter import collection, preprocessing
from data_adapter import settings as adapter_settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from django_energysystem_viewer import aggregation_graph as ag
from django_energysystem_viewer import network_graph as ng


class SelectionView(TemplateView):
    template_name = "django_energysystem_viewer/selection.html"

    def get_context_data(self, **kwargs):
        return {
            "structure_list": [
                file.stem
                for file in adapter_settings.STRUCTURES_DIR.iterdir()
                if not file.name.startswith(".") and file.name.endswith((".xls", ".xlsx"))
            ],
            "collection_list": [file.name for file in adapter_settings.COLLECTIONS_DIR.iterdir() if file.is_dir()],
        }


def get_excel_data(file: str, mode: str):
    excel_filename = f"{file}.xlsx"
    path = str(adapter_settings.STRUCTURES_DIR / excel_filename)
    sheets = ["Process_Set", "Helper_Set", "Aggregation_Mapping", "Abbreviations"]
    if mode == "network":
        # Read the data from process_set and helper_set sheets
        process_set = pd.read_excel(path, sheet_name=sheets[0])
        helper_set = pd.read_excel(path, sheet_name=sheets[1])
        # Select the relevant columns
        process_set = process_set[["input", "process", "output"]]
        helper_set = helper_set[["input", "process", "output"]]
        # Concatenate the data from both sheets
        complete_set = pd.concat([process_set, helper_set], ignore_index=True)
        # Filter processes which should not appear in any graph feature
        process_filter = ["x2x_import", "x2x_delivery", "helper_sink", "helper_pow_flow", "helper_co2"]
        complete_set = complete_set[~complete_set["process"].str.contains("|".join(process_filter))]
        return complete_set
    if mode == "aggregation":
        process_set = pd.read_excel(path, sheet_name=sheets[0])
        aggregation_mapping = pd.read_excel(path, sheet_name=sheets[2])
        return process_set, aggregation_mapping
    if mode == "abbreviations":
        return pd.read_excel(path, sheet_name=sheets[3])


def write_excel_data(data: pd.DataFrame, dir: str):
    data.to_excel(dir)


def network(request):
    structure_name = request.GET.get("structure")
    abbreviations = get_excel_data("SEDOS-structure-all", "abbreviations")
    abbreviation_list = abbreviations["abbreviations"].unique()
    process_set = get_excel_data(structure_name, mode="network")
    unique_processes = process_set["process"].unique()

    # get the inputs and outputs of the filtered process set
    sector_commodities = process_set["input"].tolist() + process_set["output"].tolist()

    # clean the list of commodities from "[", "]", "nan" and " ", as well as split at ","
    sector_commodities = [
        str(item).replace("[", "").replace("]", "").replace(" ", "").replace("nan", "") for item in sector_commodities
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
    return render(
        request,
        "django_energysystem_viewer/network.html",
        {
            "network_graph": ng.generate_Graph(
                process_set, ["pow", "x2x"], "fr", "agg", None, None, nomenclature_level=None
            ).to_html(),
            "unique_processes": unique_processes,
            "unique_commodities": unique_commodities,
            "structure_name": structure_name,
            "abbreviation_list": abbreviation_list,
        },
    )


def network_graph(request):
    # # load the process set, change the path if necessary
    structure_name = request.GET.get("structure")
    updated_process_set = get_excel_data(structure_name, mode="network")
    sectors = request.GET.getlist("sectors")
    mapping = request.GET["mapping"]
    process = request.GET.get("process")
    commodity = request.GET.get("commodity")
    nomenclature_level = int(request.GET.get("nomenclature_level"))
    # sep_agg = request.GET.get("seperate_join")
    return HttpResponse(
        ng.generate_Graph(
            updated_process_set, sectors, mapping, "agg", process, commodity, nomenclature_level
        ).to_html()
    )


class AggregationView(TemplateView):
    template_name = "django_energysystem_viewer/aggregation.html"

    def get_context_data(self, **kwargs):
        structure_name = "SEDOS-structure-all"
        abbreviations = get_excel_data(structure_name, "abbreviations")
        return {"structure_name": structure_name, "abbreviation_list": abbreviations["abbreviations"].unique()}


def aggregation_graph(request):
    sectors = request.GET["sectors"]
    lod = int(request.GET["lod"])
    df_process_set, df_aggregation_mapping = get_excel_data("SEDOS-structure-all", mode="aggregation")
    process_list = list(df_process_set["process"].unique())
    elements = ag.generate_aggregation_graph(df_aggregation_mapping, sectors, lod, process_list)
    return JsonResponse({"elements": elements}, safe=False)


def write_lod_list(request):
    lod = int(request.GET["lod"])
    df_process_set, df_aggregation_mapping = get_excel_data("SEDOS-structure-all", mode="aggregation")
    process_list = list(df_process_set["process"].unique())
    df_lod = ag.generate_df_lod(df_aggregation_mapping, lod, process_list)

    # Use an in-memory BytesIO stream instead of saving to disk
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="openpyxl")
    df_lod.to_excel(writer, index=False)
    writer.close()
    output.seek(0)

    # Create a file response
    filename = f"aggregations_lod_{lod}.xlsx"
    response = FileResponse(output, as_attachment=True, filename=filename)
    return response


def abbreviation_meaning(request):
    abb = request.GET.get("abbreviation")
    structure_name = "SEDOS-structure-all"
    abbreviations = get_excel_data(structure_name, "abbreviations")
    if abb:
        meaning = abbreviations[abbreviations["abbreviations"] == abb]["meaning"].values
        if len(meaning) > 0:
            return HttpResponse("Meaning: " + meaning)
        else:
            return HttpResponse(["Abbreviation not found"])
    else:
        return HttpResponse("")


class ProcessDetailMixin:
    def get_context_data(self, **kwargs):
        collection_name = self.request.GET["collection"]
        collection_url = collection.get_collection_meta(collection_name)["name"]
        process_name = kwargs.get("process_name", self.request.GET.get("process"))
        if not process_name:
            return {
                "collection_name": collection_name,
                "collection_url": collection_url,
            }

        process = preprocessing.get_process(collection_name, process_name)
        artifacts = collection.get_artifacts_from_collection(collection_name, process_name)
        return {
            "collection_name": collection_name,
            "artifacts": artifacts,
            "scalars": process.scalars.to_html() if not process.scalars.empty else "No data available",
            "timeseries": process.timeseries.to_html() if not process.timeseries.empty else "No data available",
        }


class ProcessesView(ProcessDetailMixin, TemplateView):
    template_name = "django_energysystem_viewer/processes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        collection_name = self.request.GET.get("collection")
        processes = collection.get_processes_from_collection(collection_name)
        context["collection_name"] = collection_name
        context["processes"] = processes
        context["banner_data"] = collection_name
        structure_name = self.request.GET.get("structure")
        context["structure_name"] = structure_name
        abbreviations = get_excel_data("SEDOS-structure-all", "abbreviations")
        context["abbreviation_list"] = abbreviations["abbreviations"].unique()
        return context


class ProcessDetailView(ProcessDetailMixin, TemplateView):
    template_name = "django_energysystem_viewer/process_detail.html"


class ArtifactsView(TemplateView):
    template_name = "django_energysystem_viewer/artifacts.html"

    def get_context_data(self, **kwargs):
        collection_name = self.request.GET.get("collection")
        collection_url = collection.get_collection_meta(collection_name)["name"]
        artifacts = collection.get_artifacts_from_collection(collection_name)
        context = {
            "collection_name": collection_name,
            "collection_url": collection_url,
            "artifacts": artifacts,
        }

        structure_name = self.request.GET.get("structure")
        context["structure_name"] = structure_name
        abbreviations = get_excel_data("SEDOS-structure-all", "abbreviations")
        context["abbreviation_list"] = abbreviations["abbreviations"].unique()

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
        collection_name = self.request.GET["collection"]
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
            "data": artifact.data.to_html() if not artifact.data.empty else "No data available",
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
