import json2table
from data_adapter import collection, preprocessing, settings
from django.http import HttpResponse
from django.views.generic import TemplateView

from django_energysystem_viewer import network_graph as ng


class NetworkView(TemplateView):
    template_name = "django_energysystem_viewer/network.html"


def network_graph(request):
    sectors = request.GET.getlist("sectors")
    mapping = request.GET["mapping"]
    return HttpResponse(ng.generate_Graph(sectors, mapping).to_html())


class CollectionsView(TemplateView):
    template_name = "django_energysystem_viewer/collections.html"

    def get_context_data(self, **kwargs):
        return {"collections": [file.name for file in settings.COLLECTIONS_DIR.iterdir() if file.is_dir()]}


class ProcessesView(TemplateView):
    template_name = "django_energysystem_viewer/processes.html"

    def get_context_data(self, **kwargs):
        collection_name = kwargs["collection_name"]
        processes = collection.get_processes_from_collection(collection_name)
        context = {"collection_name": collection_name, "processes": processes}
        process_name = self.request.GET.get("process")
        if process_name:
            process = preprocessing.get_process(collection_name, process_name)
            context["scalars"] = process.scalars.to_html()
            context["timeseries"] = process.timeseries.to_html()
        return context


class ProcessDataView(TemplateView):
    template_name = "django_energysystem_viewer/process_data.html"

    def get_context_data(self, **kwargs):
        collection_name = kwargs["collection_name"]
        process_name = kwargs["process_name"]
        process = preprocessing.get_process(collection_name, process_name)
        return {"scalars": process.scalars.to_html(), "timeseries": process.timeseries.to_html()}


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
            context["data"] = artifact.data.to_html()
            context["metadata"] = json2table.convert(artifact.metadata)
        return context


class ArtifactDataView(TemplateView):
    template_name = "django_energysystem_viewer/artifact_data.html"

    def get_context_data(self, **kwargs):
        collection_name = kwargs["collection_name"]
        group_name = kwargs["group_name"]
        artifact_name = kwargs["artifact_name"]
        version = kwargs.get("version")
        artifact = collection.get_artifact_from_collection(collection_name, group_name, artifact_name, version)
        return {"data": artifact.data.to_html(), "metadata": json2table.convert(artifact.metadata)}
