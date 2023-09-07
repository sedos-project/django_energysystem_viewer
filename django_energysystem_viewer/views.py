from django.views.generic import TemplateView


class NetworkView(TemplateView):
    template_name = "django_energysystem_viewer/network.html"
